# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import collections
import logging
from collections import defaultdict
from datetime import date
from http import HTTPStatus
from pprint import pformat
from urllib.parse import urlencode

import psycopg2.errors
from dateutil.relativedelta import relativedelta
from lxml import etree
import werkzeug.wrappers
from werkzeug.exceptions import (
    HTTPException,
    BadRequest,
    NotFound,
    NotImplemented,
)

from odoo import http
from odoo.exceptions import AccessError, AccessDenied, ValidationError, UserError
from odoo.http import request
from odoo.models import check_object_name
from odoo.osv import expression
from odoo.tools import frozendict, OrderedSet
from odoo.tools.safe_eval import safe_eval

from .utils import get_action_triples

_logger = logging.getLogger(__name__)

# The mimetype of JSON:API requests and responses, although we also
# allow application/json
JSONAPI_MIMETYPE = 'application/vnd.api+json'

# The default limit and offset when ?page[limit]=...&page[offset]=...
# are missing.
DEFAULT_PAGE = frozendict(limit=80, offset=0)

# The keys that can appear a JSON;API the query string
JSONAPI_QUERY_KEYS = frozenset(('fields', 'filter', 'include', 'page', 'sort'))


def make_jsonapi_resource_object(record, field_names, *, check_fields=True):
    if check_fields and (unknown_fields := set(field_names).difference(record._fields)):
        e = f"unknown fields for model {record._name}: {sorted(unknown_fields)}"
        raise BadRequest(e)

    resource_object = {
        'type': record._name,
        'id': record.id,
    #   'attributes': {
    #       field_name: value,
    #   },
    #   'relationships': {
    #     when many2one:
    #       field_name: {
    #           data: {} or None,
    #           links: {
    #               self: the link via the primary record,
    #               related: the canonical link to the comodel,
    #           },
    #       },
    #     when x2many:
    #       field_name: {
    #           data: [],  # when length <= 80
    #           links: {self, related},
    #           meta: {length},
    #       },
    #   },
        'links': {
            'related': f'/json/2/{record._name}/{record.id}',
        },
    }
    attributes = {}
    relationships = {}
    for field_name in field_names:
        field_spec = record._fields[field_name]
        if not field_spec.relational:
            attributes[field_name] = record[field_name]
        elif field_spec.name == 'many2one':
            if record[field_name]:
                relationships[field_name] = {
                    'data': {
                        'type': field_spec.comodel_name,
                        'id': record[field_name].id,
                    },
                    'links': {
                        'self': f'/json/2/{record._name}/{record.id}/{field_name}',
                        'related': f'/json/2/{field_spec.comodel_name}/{record[field_name].id}',
                    },
                }
            else:
                relationships[field_name] = {
                    'data': None,
                    'links': {
                        'self': f'/json/2/{record._name}/{record.id}/{field_name}',
                    },
                }
        else:
            relationships[field_name] = {
                'data': ...,
                'links': {
                    'self': f'/json/2/{record._name}/{record.id}/{field_name}',
                },
                'meta': {
                    'length': len(record[field_name]),
                },
            }
            if len(record[field_name].ids) > DEFAULT_PAGE['limit']:
                del relationships['data']
            else:
                relationships[field_name]['data'] = [
                    {
                        'type': field_spec.comodel_name,
                        'id': id_,
                    }
                    for id_ in record[field_name].ids
                ]
    if attributes:
        resource_object['attributes'] = resource_object
    if relationships:
        resource_object['relationships'] = relationships
    return resource_object


def make_jsonapi_pager(path: str, params: dict, offset: int, limit: int, length: int | None) -> dict:
    assert 'page[limit]' not in params, params
    assert 'page[offset]' not in params, params
    def page_at_offset(offset_, /):
        return urlencode({'page[limit]': limit, 'page[offset]': offset_})

    path_ = f'{path}?{urlencode(params)}&' if params else f'{path}?'
    pager = {
        'first': path_ + page_at_offset(0),
    }
    if length is not None:
        pager['last']: path_ + page_at_offset(length // limit * limit)
    if offset:
        pager['prev']: path_ + page_at_offset(max(0, offset - limit))
    if length is None or offset - limit < length:
        pager['next']: path_ + page_at_offset(offset + limit)
    return pager


def jsonapi_rename(filter_, page, sort):
    return (
        __builtins__['filter'],
        filter_,
        page['offset'],
        page['limit'],
        jsonapi_sort_to_order(sort),
    )


def jsonapi_sort_to_order(sort: str) -> str:
    return ', '.join(
        f'{field_name[1:]} DESC' if field_name.startswith('-') else field_name
        for field_name in sort.split(',')
    )


class JsonAPIDispatcher(http.Dispatcher):
    routing_type = 'jsonapi'

    @classmethod
    def is_compatible_with(cls, request):
        return request.httprequest.mimetype in (JSONAPI_MIMETYPE, 'application/json')

    def _parse_query(self, args):
        multidict = args.copy()

        # {'fields[res.partner]': 'id,name'} => {'fields': {'res.partner': 'id,name'}}
        for key in args:
            if key == 'fields':
                raise BadRequest(f"missing model name with {key!r} in query")
            elif key == 'page':
                raise BadRequest(f"missing offset or limit with {key!r} in query")
            elif key.startswith(('fields[', 'page[')):
                mainkey, _, subkey = key.removesuffix(']').partition('[')
                value = multidict.pop(key)
                if mainkey not in multidict:
                    multidict[mainkey] = {subkey: value}
                elif subkey in multidict[mainkey]:
                    raise BadRequest(f"multiple {key!r} found in query")
                else:
                    multidict[mainkey][subkey] = value

        if unknown_keys := set(multidict) - JSONAPI_QUERY_KEYS:
            raise BadRequest(f"unknown query keys: {unknown_keys}")

        # {"filter": "[['name', '=', 'john']]"} => {"filter": [["name", "=", "john"]]}
        if filter_str := multidict.get('filter'):
            try:
                multidict['filter'] = ast.literal_eval(filter_str)
            except ValueError:
                raise BadRequest(f"bad filter query, invalid domain: {filter_str}")

        # {"include": "user_id.groups_id,parent_id"} => {"include": ["user_id.groups_id", "parent_id"]}
        if include_csv := multidict.get('include'):
            multidict['include'] = include_csv.split(',')

        # {"fields": {"res.partner": "name,phone"}} => {"fields": {"res.partner": ["name", "phone"]}}
        if fields := multidict.pop('fields', None):
            multidict['fields'] = {}
            for model_name, fields_csv in fields.items():
                multidict['fields'][model_name] = fields_csv.split(',')

        if page := multidict.pop('page', None):
            try:
                multidict['page'] = {
                    'limit': int(page.get('limit', DEFAULT_PAGE['limit'])),
                    'offset': int(page.get('offset', DEFAULT_PAGE['offset'])),
                }
                if multidict['page']['limit'] < 0:
                    raise BadRequest("bad page[limit] query: must be a positive integer")
                if multidict['page']['offset'] < 0:
                    raise BadRequest("bad page[offset] query: must be a positive integer")
            except ValueError as exc:
                e = f"bad page[limit] or page[offset] query: {exc.args[0]}"
                raise BadRequest(e) from exc

        return multidict

    def dispatch(self, endpoint, args):
        self.request.params = self._parse_query(self.request.httprequest.args) | args
        _logger.debug("jsonapi extracted parameters:\n%s", pformat(self.request.params))
        if self.request.db:
            result = self.request.registry['ir.http']._dispatch(endpoint)
        else:
            result = endpoint(**self.request.params)

        if isinstance(result, werkzeug.wrappers.Response):
            return result

        assert isinstance(result, collections.abc.Mapping), result
        return self.request.make_json_response(
            result,
            status=int(result['errors'][0]['status']) if 'errors' in result else 200,
            headers=[
                # reuse the same mimetype (json or vnd.api+json) as the
                # request, as most tools use json and are able to pretty
                # print a json response, but not a vnd.api+json one.
                ('Content-Type', f'{self.request.httprequest.mimetype}; charset=utf-8')
            ]
        )

    def handle_error(self, exc):
        if isinstance(exc, HTTPException):
            error = {
                'status': str(exc.code),
                'title': HTTPStatus(exc.code).phrase,
                'detail': exc.description,
            }
        elif isinstance(exc, (AccessDenied, AccessError)):
            error = {
                'status': '403',
                'title': "Access Error",
                'detail': exc.args[0],
            }
        elif isinstance(exc, ValidationError):
            error = {
                'status': '422',
                'title': "Validation Error",
                'detail': exc.args[0],
            }
        elif isinstance(exc, UserError):
            error = {
                'status': '422',
                'title': "User Error",
                'detail': exc.args[0],
            }
        else:
            meta = http.serialize_exception(exc)
            error = {
                'status': '500',
                'title': HTTPStatus(500).phrase,
                'detail': f"{meta['name']}: {meta['message']}",
                'meta': meta,
            }
        return self.request.make_json_response(
            {'errors': [error]},
            status=int(error['status']),
            headers=[
                # reuse the same content-type (json or vnd.api+json) as
                # the request, so we can pretty print it in the browser
                ('Content-Type', f'{self.request.httprequest.mimetype}; charset=utf-8'),
            ],
        )



class WebJsonController(http.Controller):

    # for /json, the route should work in a browser, therefore type=http
    @http.route('/json/<path:subpath>', auth='user', type='http', readonly=True)
    def web_json(self, subpath, **kwargs):
        self._check_json_route_active()
        return request.redirect(
            f'/json/2/{subpath}?{urlencode(kwargs)}',
            HTTPStatus.TEMPORARY_REDIRECT
        )

    # =====================================================
    # /json/2: REST-like API, RPC and dynamic documentation
    # =====================================================

    @http.route('/json/2/<model_name>', methods=['GET'], auth='bearer', type='jsonapi', readonly=True, save_session=False)
    def web_json_2_search(self, model_name, filter=(), fields=frozendict(), include=(), sort='id', page=DEFAULT_PAGE):
        filter, domain, offset, limit, order = jsonapi_rename(filter, page, sort)

        breakpoint()

        try:
            Model = self.env[model_name]
        except KeyError as exc:
            e = f"model {model_name!r} does not exist"
            raise NotFound(e) from exc
        records = Model.search(domain, offset, limit, order)

        data_list, included = self._web_json_2_read(records, fields, include)

        length = (offset + len(records)) if len(records) < limit else Model.search_count(domain)
        path_canonical = f'/json/2/{model_name}'
        params = {
            'filter': domain,
            **{
                f'fields[{model_name}]': ','.join(field_names)
                for model_name, field_names
                in fields.items()
            },
            'include': ','.join(include),
            'sort': sort,
        }

        res = {
            'data': data_list,
            **({'included': included} if included else {}),
            'links': make_jsonapi_pager(path_canonical, params, offset, limit, length),
            'meta': {
                'length': length,
            },
        }
        return res

    @http.route('/json/2/<model_name>/<int:id>', methods=['GET'], auth='bearer', type='jsonapi', readonly=True, save_session=False)
    def web_json_2_read(self, model_name, id, fields, include):
        try:
            model = self.env[model_name]
        except KeyError as exc:
            raise NotFound(f"no model with name {model_name!r}") from exc
        record = model.browse(int(id)).exists()
        if not record:
            raise NotFound(f"no record for model {model_name} with id {id}")

        data_list, included = self._web_json_2_read(record, fields, include)
        params = {
            **{
                f'fields[{model_name}]': ','.join(field_names)
                for model_name, field_names
                in fields.items()
            },
            'include': ','.join(include),
        }

        res = {
            'data': data_list[0] if data_list else None,
            **({'included': included} if included else {}),
            'links': {
                'self': f'/json/2/{model_name}/{id}?{urlencode(params)}',
            }
        }
        return res

    @http.route(['/json/2/<model_name>/<int:id>/<rel_field_name>'])
    def web_json_2_read_relation(self, model_name, id, rel_field_name, filter=(), fields=frozendict(), include=(), sort='id', page=DEFAULT_PAGE):
        filter, domain, offset, limit, order = jsonapi_rename(filter, page, sort)

        try:
            Model = self.env[model_name]
        except KeyError as exc:
            raise NotFound(f"no model with name {model_name!r}") from exc
        record = Model.browse(int(id)).exists()
        if not record:
            raise NotFound(f"no record for model {model_name} with id {id}")
        try:
            field_spec = record._fields[rel_field_name]
            if not field_spec.relational:
                raise KeyError(rel_field_name)
        except KeyError as exc:
            e =(f"no relational field for model {model_name} with name "
                f"{rel_field_name!r}")
            raise BadRequest(e) from exc


        if field_spec.type == 'many2one':
            corecord = record[rel_field_name]
            data_list, included = self._web_json_2_read(corecord, fields, include)
            return ...

        # there must be a better way!
        if not sort.isalnul():
            raise BadRequest("can only sort by a single field")
        corecords = record[rel_field_name].filtered_domain(domain)
        length = len(corecords)
        corecords = corecords.sorted(sort)[offset:offset+limit]

        data_list, included = self._web_json_2_read(corecord, fields, include)
        path_canonical = f'/json/2/{model_name}/{id}/{rel_field_name}'
        params = {
            'filter': filter,
            **{
                f'fields[{model_name}]': ','.join(field_names)
                for model_name, field_names
                in fields.items()
            },
            'include': ','.join(include),
            'sort': sort,
        }

        return {
            'data': data_list,
            **({'included': included} if included else {}),
            'links': make_jsonapi_pager(path_canonical, params, offset, limit, length),
            'meta': {
                'length': length
            }
        }

    def _web_json_2_read(self, records, fields=frozendict(), include=()):
        field_names = fields.get(records._name) or records._fields.keys()
        data_list = [make_jsonapi_resource_object(record, field_names) for record in records]

        included_records = defaultdict(OrderedSet)
        def get_included_ressources(records, include):
            include_field_names = [
                field_name
                for field_name in (fields.get(records._name) or records._fields.keys())
                if records._fields[field_name].relational
                if any(field_path.partition('.')[0] == field_name for field_path in include)
            ]
            for field_name in include_field_names:
                sub_records = records[field_name]
                included_records[sub_records._name].update(sub_records.ids)
                get_included_ressources(sub_records, include=[
                    field_path.removeprefix(f'{field_name}.')
                    for field_path in include
                    if field_path.startswith(f'{field_name}.')
                ])
        get_included_ressources(records, include)

        included = []
        for model_name, ids in included_records.items():
            field_names = fields.get(model_name) or self.env[model_name]._fields.keys()
            for record in self.env[model_name].browse(ids):
                included.append(make_jsonapi_resource_object(record, field_names))

        return data_list, included

    @http.route('/json/2/<model>', methods=['POST'], auth='bearer', type='jsonapi', csrf=False, save_session=False)
    def web_json_2_create(self, model):
        raise NotImplemented()  # noqa: F901

    @http.route('/json/2/<model>/<int:id>', methods=['PATCH'], auth='bearer', type='jsonapi', csrf=False, save_session=False)
    def web_json_2_write(self, model, id):
        raise NotImplemented()  # noqa: F901

    @http.route('/json/2/<model>/<int:id>', methods=['DELETE'], auth='bearer', type='jsonapi', csrf=False, save_session=False)
    def web_json_2_unlink(self, model, id):
        record = self.env[model].browse(id)
        if not record.exists():
            raise NotFound()
        record.unlink()
        return self.request.make_response(HTTPStatus.NO_CONTENT)

    @http.route('/json/2/<model>/rpc/<method>', methods=['POST'], auth='bearer', type='jsonapi', csrf=False, save_session=False)
    def web_json_2_rpc(self, model, method):
        raise NotImplemented()  # noqa: F901

    @http.route('/json/2/<model>/doc', methods=['GET'], auth='bearer', type='http', readonly=True, save_session=False)
    def web_json_2_doc(self, model):
        fields = self.env[model].fields_get()
        head = '<head><style>td,th {vertical-align: top; text-align: left;}</style></head>'
        table_head = '<tr><th>name</th><th>type</th><th>readonly</th><th>required</th><th>searchable</th><th>string</th></tr>'
        content = [
            f'<tr><td>{field_name}</td><td>{info["type"]}</td><td>{info["readonly"]}</td><td>{info["required"]}</td><td>{info["searchable"]}</td><td>{info["string"]}</td></tr>'
            for field_name, info in fields.items()
        ]
        return f'<html>{head}<body><h1>GET ... &fields[{model}]</h1><table>{table_head}{"".join(content)}</table></body></html>'

    # =====================================================
    # /json/1: download the data of webclient views as json
    # =====================================================

    @http.route('/json/1/<path:subpath>', auth='bearer', type='http', readonly=True)
    def web_json_1(self, subpath, **kwargs):
        """Simple JSON representation of the views.

        Get the JSON representation of the action/view as it would be shown
        in the web client for the same /odoo `subpath`.

        Behaviour:
        - When, the action resolves to a pair (Action, id), `form` view_type.
          Otherwise when it resolves to (Action, None), use the given view_type
          or the preferred one.
        - View form uses `web_read`.
        - If a groupby is given, use a read group.
          Views pivot, graph redirect to a canonical URL with a groupby.
        - Otherwise use a search read.
        - If any parameter is missing, redirect to the canonical URL (one where
          all parameters are set).

        :param subpath: Path to the (window) action to execute
        :param view_type: View type from which we generate the parameters
        :param domain: The domain for searches
        :param offset: Offset for search
        :param limit: Limit for search
        :param groupby: Comma-separated string; when set, executes a `web_read_group`
                        and groups by the given fields
        :param fields: Comma-separates aggregates for the "group by" query
        :param start_date: When applicable, minimum date (inclusive bound)
        :param end_date: When applicable, maximum date (exclusive bound)
        """
        self._check_json_route_active()
        if not request.env.user.has_group('base.group_allow_export'):
            raise AccessError(request.env._("You need export permissions to use the /json route"))

        # redirect when the computed kwargs and the kwargs from the URL are different
        param_list = set(kwargs)

        def check_redirect():
            # when parameters were added, redirect
            if set(param_list) == set(kwargs):
                return None
            # for domains, make chars as safe
            encoded_kwargs = urlencode(kwargs, safe="()[], '\"")
            return request.redirect(
                f'/json/1/{subpath}?{encoded_kwargs}',
                HTTPStatus.TEMPORARY_REDIRECT
            )

        # Get the action
        env = request.env
        action, context, eval_context, record_id = self._get_action(subpath)
        model = env[action.res_model].with_context(context)

        # Get the view
        view_type = kwargs.get('view_type')
        if not view_type and record_id:
            view_type = 'form'
        view_id, view_type = get_view_id_and_type(action, view_type)
        view = model.get_view(view_id, view_type)
        spec = model._get_fields_spec(view)

        # Simple case: form view with record
        if view_type == 'form' or record_id:
            if redirect := check_redirect():
                return redirect
            if not record_id:
                raise BadRequest(env._("Missing record id"))
            res = model.browse(int(record_id)).web_read(spec)[0]
            return request.make_json_response(res)

        # Find domain and limits
        domains = [safe_eval(action.domain or '[]', eval_context)]
        if 'domain' in kwargs:
            # for the user-given domain, use only literal-eval instead of safe_eval
            user_domain = ast.literal_eval(kwargs.get('domain') or '[]')
            domains.append(user_domain)
        else:
            default_domain = get_default_domain(model, action, context, eval_context)
            if default_domain and default_domain != expression.TRUE_DOMAIN:
                kwargs['domain'] = repr(default_domain)
            domains.append(default_domain)
        try:
            limit = int(kwargs.get('limit', 0)) or action.limit
            offset = int(kwargs.get('offset', 0))
        except ValueError as exc:
            raise BadRequest(exc.args[0]) from exc
        if 'offset' not in kwargs:
            kwargs['offset'] = offset
        if 'limit' not in kwargs:
            kwargs['limit'] = limit

        # Additional info from the view
        view_tree = etree.fromstring(view['arch'])

        # Add date domain for some view types
        if view_type in ('calendar', 'gantt', 'cohort'):
            try:
                start_date = date.fromisoformat(kwargs['start_date'])
                end_date = date.fromisoformat(kwargs['end_date'])
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc
            except KeyError:
                start_date = end_date = None
            date_domain = get_date_domain(start_date, end_date, view_tree)
            domains.append(date_domain)
            if 'start_date' not in kwargs or end_date not in kwargs:
                kwargs.update({
                    'start_date': date_domain[0][2].isoformat(),
                    'end_date': date_domain[1][2].isoformat(),
                })

        # Add explicitly activity fields for an activity view
        if view_type == 'activity':
            domains.append([('activity_ids', '!=', False)])
            # add activity fields
            for field_name, field in model._fields.items():
                if field_name.startswith('activity_') and field_name not in spec and model._has_field_access(field, 'read'):
                    spec[field_name] = {}

        # Group by
        groupby, fields = get_groupby(view_tree, kwargs.get('groupby'), kwargs.get('fields'))
        if groupby is not None and not kwargs.get('groupby'):
            # add arguments to kwargs
            kwargs['groupby'] = ','.join(groupby)
            if 'fields' not in kwargs and fields:
                kwargs['fields'] = ','.join(fields)
        if groupby is None and fields:
            # add fields to the spec
            for field in fields:
                spec.setdefault(field, {})

        # Last checks before the query
        if redirect := check_redirect():
            return redirect
        domain = expression.AND(domains)
        # Reading a group or a list
        if groupby:
            res = model.web_read_group(
                domain,
                fields=fields or ['__count'],
                groupby=groupby,
                limit=limit,
                lazy=False,
            )
            # pop '__domain' key
            for value in res['groups']:
                del value['__domain']
        else:
            res = model.web_search_read(
                domain,
                spec,
                limit=limit,
                offset=offset,
            )
        return request.make_json_response(res)

    def _check_json_route_active(self):
        # experimental route, only enabled in demo mode or when explicitly set
        if not (request.env.ref('base.module_base').demo
                or request.env['ir.config_parameter'].sudo().get_param('web.json.enabled')):
            raise NotFound()

    def _get_action(self, subpath):
        def get_action_triples_():
            try:
                yield from get_action_triples(request.env, subpath, start_pos=1)
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc

        context = dict(request.env.context)
        active_id, action, record_id = list(get_action_triples_())[-1]
        action = action.sudo()
        if action.usage == 'ir_actions_server' and action.path:
            # force read-only evaluation of action_data
            try:
                with action.pool.cursor(readonly=True) as ro_cr:
                    if not ro_cr.readonly:
                        ro_cr.connection.set_session(readonly=True)
                    assert ro_cr.readonly
                    action_data = action.with_env(action.env(cr=ro_cr, su=False)).run()
            except psycopg2.errors.ReadOnlySqlTransaction as e:
                # never retry on RO connection, just leave
                raise AccessError(action.env._("Unsupported server action")) from e
            except ValueError as e:
                # safe_eval wraps the error into a ValueError (as str)
                if "ReadOnlySqlTransaction" not in e.args[0]:
                    raise
                raise AccessError(action.env._("Unsupported server action")) from e
            # transform data into a new record
            action = action.env[action_data['type']]
            action = action.new(action_data, origin=action.browse(action_data.pop('id')))
        if action._name != 'ir.actions.act_window':
            e = f"{action._name} are not supported server-side"
            raise BadRequest(e)
        eval_context = dict(
            action._get_eval_context(action),
            active_id=active_id,
            context=context,
        )
        # update the context and return
        context.update(safe_eval(action.context, eval_context))
        return action, context, eval_context, record_id


def get_view_id_and_type(action, view_type: str | None) -> tuple[int | None, str]:
    """Extract the view id from the action"""
    assert action._name == 'ir.actions.act_window'
    view_modes = action.view_mode.split(',')
    if not view_type:
        view_type = view_modes[0]

    try:
        view_id = next(view_id for view_id, action_view_type in action.views if view_type == action_view_type)
    except StopIteration:
        if view_type not in view_modes:
            raise BadRequest(request.env._(
                "Invalid view type '%(view_type)s' for action id=%(action)s",
                view_type=view_type,
                action=action.id,
            )) from None
        view_id = False
    return view_id, view_type


def get_default_domain(model, action, context, eval_context):
    for ir_filter in model.env['ir.filters'].get_filters(model._name, action._origin.id):
        if ir_filter['is_default']:
            # user filters, static parsing only
            default_domain = ast.literal_eval(ir_filter['domain'])
            break
    else:
        def filters_from_context():
            view_tree = None
            for key, value in context.items():
                if key.startswith('search_default_') and value:
                    filter_name = key[15:]
                    if not check_object_name(filter_name):
                        raise ValueError(model.env._("Invalid default search filter name for %s", key))
                    if view_tree is None:
                        view = model.get_view(action.search_view_id.id, 'search')
                        view_tree = etree.fromstring(view['arch'])
                    if (element := view_tree.find(Rf'.//filter[@name="{filter_name}"]')) is not None:
                        # parse the domain
                        if domain := element.attrib.get('domain'):
                            yield domain
                        # not parsing context['group_by']

        default_domain = expression.AND(
            safe_eval(domain, eval_context)
            for domain in filters_from_context()
        )
    return default_domain


def get_date_domain(start_date, end_date, view_tree):
    if not start_date or not end_date:
        start_date = date.today() + relativedelta(day=1)
        end_date = start_date + relativedelta(months=1)
    date_field = view_tree.attrib.get('date_start')
    if not date_field:
        raise ValueError("Could not find the date field in the view")
    return [(date_field, '>=', start_date), (date_field, '<', end_date)]


def get_groupby(view_tree, groupby=None, fields=None):
    """Parse the given groupby and fields and fallback to the view if not provided.

    Return the groupby as a list when given.
    Otherwise find groupby and fields from the view.

    :param view_tree: The xml tree of the view
    :param groupby: string or None
    :param fields: string or None
    """
    if groupby:
        groupby = groupby.split(',')
    if fields:
        fields = fields.split(',')
    else:
        fields = None
    if groupby is not None:
        return groupby, fields

    if view_tree.tag in ('pivot', 'graph'):
        # extract groupby from the view if we don't have any
        field_by_type = defaultdict(list)
        for element in view_tree.findall(r'./field'):
            field_name = element.attrib.get('name')
            if element.attrib.get('invisible', '') in ('1', 'true'):
                field_by_type['invisible'].append(field_name)
            else:
                field_by_type[element.attrib.get('type', 'normal')].append(field_name)
            # not reading interval from the attribute
        groupby = [
            *field_by_type.get('row', ()),
            *field_by_type.get('col', ()),
            *field_by_type.get('normal', ()),
        ]
        if fields is None:
            fields = field_by_type.get('measure', [])
        return groupby, fields
    if view_tree.attrib.get('default_group_by'):
        # in case the kanban view (or other) defines a default grouping
        # return the field name so it is added to the spec
        field = view_tree.attrib.get('default_group_by')
        return (None, [field] if field else [])
    return None, None

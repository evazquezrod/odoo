import difflib

from werkzeug.exceptions import NotFound

from odoo import http, models
from odoo import release
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service.model import get_public_method


def is_public_method(model, name):
    try:
        meth = get_public_method(model, name)
        return meth
    except (AttributeError, AccessError):
        return None


class DocController(http.Controller):
    @http.route('/doc', type='http', auth='public', readonly=True)
    def doc_home(self, model=None):
        return (
            "<p>Page under construction<p>"
            "<p>Please go to <a href={0!r}>{0}</a></p>"
        ).format(f'/doc/3/{model or "base"}.json')

    @http.route('/doc/3/schema.json', type='http', auth='public', readonly=True)
    def doc_schema(self, limit=10):
        base_methods = {
            attr
            for attr in dir(models.BaseModel)
            if (meth := is_public_method(request.env['base'], attr))
        }

        schemas = {}
        for model in request.env.values():
            if model._abstract:
                continue
            fields = model.fields_get()
            schemas[model._name] = {
                'fields': fields,
                'methods': {
                    attr: meth
                    for attr in dir(model)
                    if attr not in fields
                    if attr not in base_methods
                    if (meth := is_public_method(model, attr))
                },
            }

        openapi = {
            "openapi": "3.0.2",
            "info": {
                "title": "Odoo Live Models Documentation",
                "version": release.version,
            },
            "tags": [
                {
                    "name": model._name,
                    "description": model._description
                }
                for model in list(request.env.values())[:limit]
            ],
            "paths": {
                f"/json/2/{{model}}/{method_name}": {"post": {
                    "tags": list(schemas)[:limit],
                    "parameters": [
                      {
                        "name": "model",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                      }
                    ],
                }}
                for method_name in sorted(base_methods)
            } | {
                f"/json/2/{model}/{method_name}": {"post": {"tags": [model]}}
                for model in list(schemas)[:limit]
                for method_name, method in schemas[model]['methods'].items()
            },
            "components": {
                "schemas": {
                    model: {
                        "type": "object",
                        "properties": {field: {} for field in schemas[model]['fields']}
                    }
                    for model in list(schemas)[:limit]
                }
            }
        }

        return request.make_json_response(openapi)

    @http.route('/doc/3/<model_name>.json', type='http', auth='public', readonly=True)
    def doc_model(self, model_name):
        model = request.env.get(model_name)
        if model:
            m = f"Model {model_name!r} not found."
            if closest5 := difflib.get_close_matches(model_name, request.env, 5):
                m += f"\n\nClose matches include:\n- {f'{chr(10)}- '.join(closest5)}"
            raise NotFound(m)

        base_methods = {
            attr
            for attr in dir(models.BaseModel)
            if (meth := is_public_method(request.env['base'], attr))
        }
        fields = model.fields_get()
        methods = {
            attr: meth
            for attr in sorted(dir(model), lambda attr: attr not in base_methods)
            if attr not in fields
            if attr not in base_methods
            if (meth := is_public_method(model, attr))
        }

        def make_fields(fields):
            data = {
                'type': 'object',
                'properties': ...,
                'required': [],
            }

            for field_name, field_spec in fields.items():
                field = {
                    'type': field_spec.openapi_type,
                }
                if field_spec.openapi_type == 'array':
                    field['items'] = {'type': }
                if field_spec.openapi_format:
                    field['format'] = field_spec.openapi_format
                if field_spec.required:
                    data['required'].append(field_name)
                else:
                    field['nullable'] = True
                if field_spec.readonly:
                    field['readOnly'] = True
                data[field_name] = field

            if not data['required']:
                del data['required']


        openapi = {
            "openapi": "3.0.2",
            "info": {
                "title": "Odoo Live Models Documentation",
                "version": release.version,
            },
            "tags": [model],
            "paths": {
                f"/json/2/{model_name}/{method_name}": {"post": {"tags": [model]}}
                for method_name, method in methods.items()
            },
            "components": {
                "schemas": {
                    model_name: {
                        "type": "object",
                        "properties": {
                            field_name: {
                                "type": field_spec.openapi_type,
                                "format": field_spec.openapi_format,
                            }
                            for field_name, field_spec
                            in model._fields.items()
                        }
                    }
                }
            }
        }

        return request.make_json_response(openapi)

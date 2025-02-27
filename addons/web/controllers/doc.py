import difflib
import inspect

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service.model import get_public_method


def is_public_method(model, name):
    try:
        get_public_method(model, name)
    except (AttributeError, AccessError):
        return False
    else:
        return True


class DocController(http.Controller):
    @http.route('/doc', type='http', auth='public', readonly=True)
    def doc_home(self, model=None):
        return (
            "<p>Page under construction<p>"
            "<p>Please go to <a href={0!r}>{0}</a></p>"
        ).format(f'/doc/{model or 'base'}.json')

    @http.route('/doc/schema.json', type='http', auth='public', readonly=True)
    def doc_schema(self):
        schema = {}
        for model in request.env:
            fields = model.fields_get()
            schema[model] = {
                'fields': list(fields),
                'methods': [
                    attr
                    for attr in dir(model)
                    if attr not in fields
                    if is_public_method(attr)
                ],
            }

        return request.make_json_response(schema)

    @http.route('/doc/<model>.json', type='http', auth='public', readonly=True)
    def doc_model(self, model):
        if model not in request.env:
            m = f"Model {model!r} not found."
            if closest5 := difflib.get_close_matches(model, request.env, 5):
                m += f"\n\nClose matches include:\n- {f'{chr(10)}- '.join(closest5)}"
            raise NotFound(m)

        Model = request.env[model]
        fields = Model.fields_get()

        public_methods = {
            attr: str(inspect.signature(meth))
            for attr in dir(Model)
            if not attr.startswith('_')
            if attr not in fields
            if callable(meth := getattr(Model, attr))
            if not getattr(meth, '_api_private', False)
        }

        # TODO: OpenAPI
        return request.make_json_response({
            'fields': fields,
            'methods': public_methods
        })

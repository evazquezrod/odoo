import difflib
import inspect

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class DocController(http.Controller):
    @http.route([
        '/doc',
        '/doc/<model>',
        '/doc/<model>.html',
        '/doc/<model>.json'
    ], type='http', auth='public', readonly=True)
    def doc(self, model=None):
        if not model:
            return request.redirect('/doc/res.partner.json')
        if not request.httprequest.path.endswith(('.html', '.json')):
            request.redirect(request.httprequest.path + '.html')

        if model not in request.env:
            m = f"Model {model!r} not found."
            if closest5 := difflib.get_close_matches(model, request.env, 5):
                m += f"\n\nClose matches include:\n- {f'{chr(10)}- '.join(closest5)}"
            raise NotFound(m)

        # TODO: use the registry sequence as ETag, for caching

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

        if request.httprequest.path.endswith('.json'):
            return request.make_json_response({
                'fields': fields,
                'methods': public_methods
            })

        # we should render a template
        return (
            "<p>Page under construction<p>"
            "<p>Please go to <a href={0!r}>{0}</a></p>"
        ).format(request.httprequest.path + '.json')

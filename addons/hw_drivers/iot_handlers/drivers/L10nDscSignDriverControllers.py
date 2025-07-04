# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request, Response


class SignUsbDscIotController(http.Controller):

    @http.route("/hw_sign_dsc_token/sign", type='http', auth='none', cors='*', csrf=False, save_session=False, methods=['GET', 'POST', 'OPTIONS'])
    def sign_pdf_with_dsc_usb_token(self, **kw):
        return "secret_signed_pdf!"
        # return Response(
        #     "secret_signed_pdf!",
        #     content_type='application/pdf',
        #     headers={
        #         'Access-Control-Allow-Origin': 'localhost:8069',
        #         'Access-Control-Allow-Methods': ['GET', 'POST', 'OPTIONS'],
        #         'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        #     }
        # )

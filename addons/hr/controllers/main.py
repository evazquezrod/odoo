from odoo import http
from odoo.http import request


class HrEmployee(http.Controller):
    @http.route('/hr/is_fresh_db', type="jsonrpc", auth="user")
    def is_fresh_db(self):
        employees = request.env['hr.employee'].sudo().search(['|', ('active', '=', True), ('active', '=', False)])
        # if not request.env['ir.config_parameter'].get_param('hr.onboarding_done'):
        #     request.env['ir.config_parameter'].set_param('hr.onboarding_done', True)
        return len(employees) == 1 and employees.user_id.login == 'admin'

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

async function actionSignWithUsbDrive(env, action) {
    let route = "http://localhost:8069/hw_sign_dsc_token/sign";
    const { orm, http, dialog, action: actionService } = env.services;

    let result;
    try {
        console.log("actionSignWithUsbDrive", action);
        result = await http.post(route, action?.params);
        console.log("result", result);
    } catch (error) {
        console.log(error);
        return;
    }
}

registry.category("actions").add("action_sign_invoices_with_dsc_token", actionSignWithUsbDrive);

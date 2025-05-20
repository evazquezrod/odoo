import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class HrActionOnboarding extends Component {
    static template = "hr.EmployeeActionOnboarding";
    static props = {};

    setup() {
        this.actionService = useService("action");
    }

    loadEmployeeScenario = async () => {
        await this.actionService.doAction("hr.action_load_employee_demo_data");
    }

    actionCreateEmployee = async () => {
        await this.actionService.doAction({
            name: _t("Employees"),
            res_model: "hr.employee",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}

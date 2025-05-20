import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { HrActionHelper } from "@hr/views/hr_action_helper";
import { HrActionOnboarding } from "./hr_action_onboarding";

export class HrPivotController extends PivotController {
    static template = "hr.PivotView";
    static components = { ...PivotController.components, HrActionHelper, HrActionOnboarding };

    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            this.isHrOnboardingDone = await this.orm.call('ir.config_parameter', 'get_param', ['hr.hr_employee_onboarding_done']);
        });
    }
}
export const HrPivotView = {
    ...pivotView,
    Controller: HrPivotController,
};

registry.category("views").add("hr_pivot_view", HrPivotView);

import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { graphView } from "@web/views/graph/graph_view";
import { GraphController } from "@web/views/graph/graph_controller";

import { HrActionHelper } from "@hr/views/hr_action_helper";
import { HrActionOnboarding } from "@hr/views/hr_action_onboarding";

export class HrGraphController extends GraphController {
    static template = "hr.GraphView";
    static components = { ...GraphController.components, HrActionHelper, HrActionOnboarding };

    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            this.isHrOnboardingDone = await this.orm.call('ir.config_parameter', 'get_param', ['hr.hr_employee_onboarding_done']);
        });
    }
}
export const HrGraphView = {
    ...graphView,
    Controller: HrGraphController,
};

registry.category("views").add("hr_graph_view", HrGraphView);

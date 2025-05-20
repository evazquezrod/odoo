import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { HrEmployeeHierarchyRenderer } from "./hr_employee_hierarchy_renderer";
import { HierarchyController } from "@web_hierarchy/hierarchy_controller";
import { HrActionHelper } from "@hr/views/hr_action_helper";
import { HrActionOnboarding } from "@hr/views/hr_action_onboarding";

export class HrEmployeeHierarchyController extends HierarchyController {
    static template = "hr_org_chart.HierarchyView";
    static components = { ...HierarchyController.components, HrActionHelper, HrActionOnboarding };

    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            this.isHrOnboardingDone = await this.orm.call('ir.config_parameter', 'get_param', ['hr.hr_employee_onboarding_done']);
        });
    }
}

export const hrEmployeeHierarchyView = {
    ...hierarchyView,
    Controller: HrEmployeeHierarchyController,
    Renderer: HrEmployeeHierarchyRenderer,
};

registry.category("views").add("hr_employee_hierarchy", hrEmployeeHierarchyView);

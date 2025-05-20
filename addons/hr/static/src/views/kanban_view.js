import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

import { useArchiveEmployee } from "@hr/views/archive_employee_hook";
import { HrActionHelper } from "@hr/views/hr_action_helper";
import { HrActionOnboarding } from '@hr/views/hr_action_onboarding';

export class EmployeeKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const selectedRecords = this.model.root.selection;

        menuItems.archive.callback = this.archiveEmployee.bind(
            this,
            selectedRecords.map(({ resId }) => resId)
        );
        return menuItems;
    }
}

export class EmployeeKanbanRender extends KanbanRenderer {
    static template = "hr.KanbanRenderer";
    static components = { ...KanbanRenderer.components, HrActionOnboarding, HrActionHelper };

    setup() {
        super.setup();

        onWillStart(async () => {
            this.isFreshDB = await rpc("/hr/is_fresh_db");
        });
    }

    get showOnboarding() {
        return this.isFreshDB && !this.showNoContentHelper;
    }

    getGroupsOrRecords() {
        const result = super.getGroupsOrRecords();
        if (this.isFreshDB) {
            return [];
        }
        return result;
    }
}

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Controller: EmployeeKanbanController,
    Renderer: EmployeeKanbanRender,
});

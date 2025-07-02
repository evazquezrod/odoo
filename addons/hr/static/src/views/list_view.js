import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';

import { useArchiveEmployee } from '@hr/views/archive_employee_hook';

export class EmployeeListController extends ListController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const selectedRecords = this.model.root.selection;

        menuItems.archive.callback = this.archiveEmployee.bind(
            this,
            selectedRecords.map(({resId}) => resId),
        )
        return menuItems;
    }

    async createRecord() {
        await this.props.createRecord();
    }
}

class HrVersionListController extends ListController {
    async openRecord(event) {
        const versionId = event?.resId;
        const employeeId = event?.evalContext?.employee_id;

        if (employeeId) {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "hr.employee",
                res_id: employeeId,
                views: [[false, "form"]],
                target: "current",
                context: {
                    version_id: versionId,
                },
            });
        } else {
            this.notification.add("No employee linked to this version.", {
                type: "warning",
            });
        }
    }
}

registry.category('views').add('hr_employee_list', {
    ...listView,
    Controller: EmployeeListController,
});

registry.category("views").add("hr_version_list", {
    ...listView,
    Controller: HrVersionListController,
});

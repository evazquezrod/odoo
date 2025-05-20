import { onWillStart } from "@odoo/owl";
import { registry } from '@web/core/registry';
import { rpc } from "@web/core/network/rpc";

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';
import { ListRenderer } from "@web/views/list/list_renderer";

import { useArchiveEmployee } from '@hr/views/archive_employee_hook';
import { HrActionHelper } from "@hr/views/hr_action_helper";
import { HrActionOnboarding } from '@hr/views/hr_action_onboarding';

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

export class EmployeeListRender extends ListRenderer {
    static template = "hr.ListRenderer";
    static components = { ...ListRenderer.components, HrActionHelper, HrActionOnboarding };

    setup() {
        super.setup();

        onWillStart(async () => {
            this.isFreshDB = await rpc("/hr/is_fresh_db");
        });
    }

    get showOnboarding() {
        return this.isFreshDB && !this.showNoContentHelper;
    }
}

const ListModel = listView.Model;
export class EmployeeListModel extends ListModel {
    setup() {
        super.setup(...arguments);
    }
    async load() {
        const result = await super.load();

        // if (this.isFreshDB === true) {
        //     console.log("Fresh DB condition met. Overriding result.");
        //     return {
        //         ...result,
        //         count: 0,
        //         data: [],
        //     };
        // }

        return result;
    }
}


registry.category('views').add('hr_employee_list', {
    ...listView,
    Controller: EmployeeListController,
    Renderer: EmployeeListRender,
    // Model: EmployeeListModel,
});

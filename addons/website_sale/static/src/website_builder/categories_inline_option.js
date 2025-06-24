import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class CategoriesInlineOption extends BaseOptionComponent {
    static template = "website_sale.CategoriesInlineOption";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.website = useService('website');
        this.categories = [];

        onWillStart(async () => {
            this.categories = await this.orm.call(
                'product.public.category',
                'get_snippet_categories',
                [this.website.currentWebsiteId],
            );
        });
    }
}

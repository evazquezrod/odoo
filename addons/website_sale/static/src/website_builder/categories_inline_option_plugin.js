import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { CategoriesInlineOption } from "./categories_inline_option";

class CategoriesInlineOptionPlugin extends Plugin {
    static id = "categoriesInlineOption";
    resources = {
        builder_options: [
            {
                OptionComponent: CategoriesInlineOption,
                template: "website_sale.CategoriesInlineOption",
                selector: ".s_categories_inline",
            },
        ],

        so_content_addition_selector: [".s_categories_inline"],
    };

}
registry.category("website-plugins").add(CategoriesInlineOptionPlugin.id, CategoriesInlineOptionPlugin);

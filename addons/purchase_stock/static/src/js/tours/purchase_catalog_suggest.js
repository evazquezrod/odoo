import { registry } from "@web/core/registry";

// TODO : Test Search
registry.category("web_tour.tours").add("purchase_catalog_suggest", {
    steps: () => [
        { trigger: ".o_purchase_order" },
        {
            content: "Create a New PO",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            trigger: ".o_purchase_order",
        },
        {
            content: "Fill Vendor Field on PO",
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("Julia Agrolait", input || this.anchor);
            },
        },
        {
            content: "Select Julia as vendor",
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Julia Agrolait')",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        {
            content: "Go to product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        {
            content: "Toggle the Suggest feature in search panel",
            trigger: 'i[name="toggle_suggest_catalog"]',
            run: "click",
        },
        { trigger: "i[name='toggle_suggest_catalog'].fa-toggle-off" },
        {
            content: "Check suggest fields hidden when suggest is off",
            trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view",
            run() {
                const selectors = [
                    ".o_TimePeriodSelectionField",
                    "input.o_PurchaseSuggestInput",
                    ".o_purchase_suggest_footer",
                ];
                const stillVisible = selectors.some((sel) => {
                    const el = document.querySelector(sel);
                    return el && el.offsetParent !== null;
                });
                if (stillVisible) {
                    throw new Error("Toggle did not hide elements");
                }
            },
        },
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        {
            content: "And back again to catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: "i[name='toggle_suggest_catalog'].fa-toggle-off" }, // Should still be off
        {
            content: "Toggle suggest ON",
            trigger: 'i[name="toggle_suggest_catalog"]',
            run: "click",
        },
        { trigger: "i[name='toggle_suggest_catalog'].fa-toggle-on" },
        {
            content: "Set reference period to Last 3 months",
            trigger: ".o_TimePeriodSelectionField select",
            run: "select three_months",
        },
        {
            content: "Changing number of days",
            trigger: "input.o_PurchaseSuggestInput:first-of-type",
            run: "edit 50",
        },
        {
            trigger: "span[name='suggest_total']",
            async run() {
                await new Promise((r) => setTimeout(r, 2000));
                const total = parseFloat(this.anchor.textContent);
                if (total !== 1000) {
                    throw new Error(`Expected suggest_total = 1000, got ${total}`);
                }
            },
        },
    ],
});

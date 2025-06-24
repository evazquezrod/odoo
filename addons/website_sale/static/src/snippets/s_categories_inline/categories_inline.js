import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
// import { listenSizeChange, utils as uiUtils } from '@web/core/ui/ui_service';
import { renderToFragment } from '@web/core/utils/render';
import { Interaction } from '@web/public/interaction';


export class CategoriesInline extends Interaction {
    static selector = ".s_categories_inline";
    dynamicContent = {
        ".s_categories_inline_wrapper": {
            "t-att-class": () => ({
                "nav": this.el.dataset.layout === "nav",
                "list-unstyled": this.el.dataset.layout === "list",
                "list-group": this.el.dataset.layout === "listgroup",
                "o_categories_inline_thumbnails list-unstyled d-flex flex-column gap-2": this.el.dataset.layout === "thumbnails",
            }),
        },
    };

    async willStart() {
        const categoryId = this.el.dataset.categoryId;
        this.data = categoryId != ''
            ? await this.waitFor(rpc('/shop/get_categories', { category_id: parseInt(categoryId) }))
            : await this.waitFor(rpc('/shop/get_categories'));
    }

    start() {
        this.render();
    }

    render() {
        const snippetItemsEl = this.el.querySelectorAll(".s_categories_inline_item");
        const layout = this.el.dataset.layout;
        let snippetWrapperEl = this.el.querySelector(".s_categories_inline_wrapper");
        let newWrapperEl = layout === "listgroup" ? document.createElement("div") : document.createElement("ul");

        snippetItemsEl.forEach(el => {el.remove()});
        // Adapt the tag of wrapper el to div or ul depending on the selected layout.
        if(layout === "listgroup" || this.el.tagName.toLowerCase() === "div") {
            const oldWrapperEl = snippetWrapperEl;
            // Copy attributes
            for (const attr of oldWrapperEl.attributes) {
                newWrapperEl.setAttribute(attr.name, attr.value);
            }
            // Replace the old element with the new one in the DOM
            oldWrapperEl.parentNode.replaceChild(newWrapperEl, oldWrapperEl);
            snippetWrapperEl = newWrapperEl;
        }
        snippetWrapperEl.replaceChildren(
            renderToFragment("website_sale.s_categories_inline_template_" + layout, {
                data: this.data,
            }
        ));
    }
}

registry
    .category("public.interactions")
    .add("website_sale.categories_inline", CategoriesInline);

registry
    .category("public.interactions.edit")
    .add("website_sale.categories_inline", {Interaction: CategoriesInline});

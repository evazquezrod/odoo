
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.WebsiteSaleProduct.include({

    /**
     * @override
     *
     * Prevent displaying stock values when click and collect is activated.
     *
     */
    // FIXME VFE doesn't work currently
    // _showStockInformation: (combination_info) => {
    //     const result = this._super.apply(this, arguments);
    //     // Only show stock availability message if the product exists (not dynamic) and its
    //     // inventory is tracked
    //     return this._super.apply(this, arguments) && !combination_info.show_click_and_collect_availability;
    // },
})
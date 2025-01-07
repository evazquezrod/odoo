
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.WebsiteSaleProduct.include({

    /**
     * @override
     *
     * This will prevent the user from selecting a quantity that is not available in the
     * stock for that product.
     *
     * It will also display various info/warning messages regarding the select product's stock.
     */
    _onChangeCombination: function (ev, $parent, combination) {
        this._super.apply(this, arguments);
        if (this.el.querySelector('.o_add_wishlist_dyn')) {
            const messageEl = this.el.querySelector('div.availability_messages');
            if (messageEl && !this.el.querySelector('#stock_wishlist_message')) {
                messageEl.append(
                    renderToElement('website_sale_stock_wishlist.product_availability', combination) || ''
                );
            }
        }
    },
})

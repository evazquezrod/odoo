import { EventBus } from '@odoo/owl';
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductComparisonButton } from '@website_sale_comparison/js/product_comparison_button/product_comparison_button';

export class ProductComparison extends Interaction {
    static selector = '.js_sale';
    dynamicContent = {
        '.o_add_compare, .o_add_compare_dyn': { 't-on-click': this.addProduct },
        '.o_comparelist_remove': { 't-on-click': this.removeProduct },
        '.o_add_cart_form_compare': { 't-on-submit.prevent': this.addToCart },
    };

    setup() {
        this.bus = new EventBus();
        this.mountComponent(this.el, ProductComparisonButton, { bus: this.bus });
    }

    /**
     * Add a product to the comparison.
     *
     * @param {Event} ev
     */
    async addProduct(ev) {
        if (!this._checkMaxComparisonProducts()) return;

        const el = ev.currentTarget;
        let productId = el.dataset.productProductId;
        if (el.classList.contains('o_add_compare_dyn')) {
            productId = el.parentElement.querySelector('.product_id')?.value;
        }

        const form = el.closest('form');
        if (!productId) {
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id:
                    parseInt(form.querySelector('.product_template_id').value),
                product_template_attribute_value_ids:
                    wSaleUtils.getSelectedAttributeValues(form),
            }));
        }
        productId = parseInt(productId) || parseInt(el.dataset.productProductId);
        if (!productId) return;

        comparisonUtils.addComparisonProduct(productId);
        this.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));
        await wSaleUtils.animateClone(
            $('button[name="product_comparison_button"]'),
            $(this.el.querySelector('#product_detail_main') ?? form),
            -50,
            10,
        );
    }

    /**
     * Remove a product from the comparison.
     *
     * @param {Event} ev
     */
    removeProduct(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productProductId);
        comparisonUtils.removeComparisonProduct(productId);
        this.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));

        const productIds = comparisonUtils.getComparisonProductIds();
        const comparisonUrl = `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
        window.location.href = productIds.length ? comparisonUrl : '/shop';
    }

    /**
     * Add a product to the cart from the comparison page.
     *
     * @param {Event} ev
     */
    addToCart(ev) {
        const form = ev.currentTarget;
        const productTemplateId = parseInt(
            form.querySelector('input[type="hidden"][name="product_template_id"]').value
        );
        const productId = parseInt(
            form.querySelector('input[type="hidden"][name="product_id"]').value
        );
        const showQuantity = Boolean(form.dataset.showQuantity);

         this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: productId,
        }, {
            showQuantity: showQuantity,
        });
    }

    _checkMaxComparisonProducts() {
        if (
            comparisonUtils.getComparisonProductIds().length
            >= comparisonUtils.MAX_COMPARISON_PRODUCTS
        ) {
            this.services.notification.add(
                _t("You can compare up to 4 products at a time."),
                {
                    type: 'warning',
                    sticky: false,
                    title: _t("Too many products to compare"),
                },
            );
            return false;
        }
        return true;
    }
}

registry
    .category('public.interactions')
    .add('website_sale_comparison.product_comparison', ProductComparison);

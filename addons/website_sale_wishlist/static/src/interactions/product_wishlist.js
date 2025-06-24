import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc, RPCError } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class ProductWishlist extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        '.o_add_wishlist, .o_add_wishlist_dyn': { 't-on-click': this.addProduct },
        'input.product_id': { 't-on-change': this.onChangeVariant },
        '.wishlist-section .o_wish_rm': { 't-on-click': this.removeProduct },
        '.wishlist-section .o_wish_add': { 't-on-click': this.addToCart },
    };

    setup() {
        this.wishlistProductIds = wishlistUtils.getWishlistProductIds();
    }

    /**
     * Get the products in the wishlist.
     */
    async willStart() {
        const wishCount = parseInt(
            document.querySelector('header#top .my_wish_quantity')?.textContent
        );
        if (this.wishlistProductIds.length !== wishCount) {
            this.wishlistProductIds = await this.waitFor(rpc('/shop/wishlist/get_product_ids'));
            wishlistUtils.setWishlistProductIds(this.wishlistProductIds);
        }
    }

    /**
     * Update the wishlist view (navbar) and the wishlist button (product page).
     */
    start() {
        this._updateWishlistView();
        this.el.querySelector('input.product_id')?.dispatchEvent(
            new Event('change', { bubbles: true })
        );
    }

    /**
     * Add a product to the wishlist.
     *
     * @param {Event} ev
     */
    async addProduct(ev) {
        const el = ev.currentTarget;
        let productId = this._getProductId(el);
        const form = el.closest('form');
        let templateId = form.querySelector('.product_template_id')?.value;
        // In case the product is added from the shop page instead of the product page.
        if (!templateId) {
            templateId = el.dataset.productTemplateId;
        }
        this._updateDisabled(el, true);

        try {
            if (!productId) {
                productId = await this.waitFor(rpc('/sale/create_product_variant', {
                    product_template_id: parseInt(templateId),
                    product_template_attribute_value_ids:
                        wSaleUtils.getSelectedAttributeValues(form),
                }));
            }
        } catch (e) {
            this._updateDisabled(el, false);
            if (!(e instanceof RPCError)) throw e;
            return;
        }

        if (productId && !this.wishlistProductIds.includes(productId)) {
            try {
                await this.waitFor(rpc('/shop/wishlist/add', { product_id: productId }));
            } catch (e) {
                this._updateDisabled(el, false);
                if (!(e instanceof RPCError)) throw e;
                return;
            }
            this.wishlistProductIds.push(productId);
            wishlistUtils.setWishlistProductIds(this.wishlistProductIds);
            this._updateWishlistView();
            await wSaleUtils.animateClone(
                $(document.querySelector('header .o_wsale_my_wish')),
                $(this.el.querySelector('#product_detail_main') ?? form),
                25,
                40,
            );
            // If there was a concurrent call of `onChangeVariant`, and `productId` hasn't changed,
            // disable the button again.
            let currentProductId = this._getProductId(el);
            if (productId === currentProductId) {
                this._updateDisabled(el, true);
            }
        }
    }

    onChangeVariant(ev) {
        const input = ev.target;
        const productId = input.value;
        const button = input.closest('.js_product')?.querySelector('[data-action="o_wishlist"]');
        if (button) this._updateWishlistButton(button, productId);
    }

    /**
     * Remove a product from the wishlist.
     *
     * @param {Event} ev
     */
    async removeProduct(ev) {
        await this._removeProduct(ev, false);
    }

    /**
     * Add a product to the cart from the wishlist page.
     *
     * @param {Event} ev
     */
    async addToCart(ev) {
        if (ev.currentTarget.classList.contains('disabled')) {
            ev.preventDefault();
            return;
        }

        const td = ev.currentTarget.parentElement;
        const productId = parseInt(
            td.querySelector('input[type="hidden"][name="product_id"]').value
        );
        const productTemplateId = parseInt(
            td.querySelector('input[type="hidden"][name="product_template_id"]').value
        );
        const isCombo = td.querySelector(
            'input[type="hidden"][name="product_type"]'
        )?.value === 'combo';
        const showQuantity = Boolean(ev.currentTarget.dataset.showQuantity);

        const addToCart = this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: productId,
            isCombo: isCombo,
        }, {
            showQuantity: showQuantity,
        });

        if (!document.getElementById('b2b_wish').checked) {
            await this._removeProduct(ev, addToCart);
        }
    }

    _getProductId(el) {
        let productId = el.dataset.productProductId;
        if (el.classList.contains('o_add_wishlist_dyn')) {
            productId = el.closest('.js_product').querySelector('.product_id:checked')?.value;
        }
        return parseInt(productId);
    }

    _updateDisabled(el, isDisabled) {
        el.disabled = isDisabled;
        el.classList.toggle('disabled', isDisabled);
    }

    _updateWishlistView() {
        const wishButton = document.querySelector('.o_wsale_my_wish');
        if (wishButton.classList.contains('o_wsale_my_wish_hide_empty')) {
            wishButton.classList.toggle('d-none', !this.wishlistProductIds.length);
        }
        wishButton.querySelector('.my_wish_quantity').textContent = this.wishlistProductIds.length;
        const wishlistQuantity = document.querySelector('.my_wish_quantity');
        wishlistQuantity.classList.toggle('d-none', !this.wishlistProductIds.length);
    }

    _updateWishlistButton(button, productId) {
        const isDisabled = this.wishlistProductIds.includes(parseInt(productId));
        this._updateDisabled(button, isDisabled);
        button.dataset.productProductId = productId;
    }

    /**
     * Remove a product from the wishlist.
     *
     * @param {Event} ev
     * @param {Promise} deferredRedirect
     */
    async _removeProduct(ev, deferredRedirect) {
        const tr = ev.currentTarget.closest('tr');
        const wish = tr.dataset.wishId;
        const productId = parseInt(tr.dataset.productId);

        await this.waitFor(rpc(`/shop/wishlist/remove/${wish}`));
        tr.style.display = 'none';

        this.wishlistProductIds = this.wishlistProductIds.filter((id) => id !== productId);
        wishlistUtils.setWishlistProductIds(this.wishlistProductIds);
        if (!this.wishlistProductIds.length) {
            if (deferredRedirect) {
                await this.waitFor(deferredRedirect);
                this._redirectNoWish();
            }
        }
        this._updateWishlistView();
    }

    _redirectNoWish() {
        window.location.href = '/shop/cart';
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.product_wishlist', ProductWishlist);

import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import { redirect } from '@web/core/utils/urls';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class ProductWishlist extends Interaction {
    static selector = '.wishlist-section';
    dynamicContent = {
        '.o_wish_rm': { 't-on-click': this.removeProduct },
        '.o_wish_add': { 't-on-click': this.addToCart },
    };

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
        const button = ev.currentTarget;
        const productId = parseInt(button.dataset.productProductId);
        const productTemplateId = parseInt(button.dataset.productTemplateId);
        const isCombo = button.dataset.productType === 'combo';
        const showQuantity = Boolean(button.dataset.showQuantity);

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

        wishlistUtils.removeWishlistProduct(productId);
        if (!wishlistUtils.getWishlistProductIds().length) {
            if (deferredRedirect) {
                await this.waitFor(deferredRedirect);
                this._redirectNoWish();
            } else {
                this._redirectNoWish('/shop');
            }
        }
        wishlistUtils.updateWishlistNavBar();
    }

    _redirectNoWish(redirect_url='/shop/cart') {
        redirect(redirect_url);
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.product_wishlist', ProductWishlist);

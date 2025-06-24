const WISHLIST_PRODUCT_IDS_SESSION_NAME = 'wishlist_product_ids';

/**
 * Get the IDs of the products in the wishlist from the session.
 *
 * @return {Array<number>} The IDs of the products in the wishlist.
 */
function getWishlistProductIds() {
    return JSON.parse(sessionStorage.getItem(WISHLIST_PRODUCT_IDS_SESSION_NAME) || '[]');
}

/**
 * Set the IDs of the products in the wishlist in the session.
 *
 * @param {ArrayLike<number>} productIds The IDs of the products in the wishlist.
 */
function setWishlistProductIds(productIds) {
    sessionStorage.setItem(
        WISHLIST_PRODUCT_IDS_SESSION_NAME, JSON.stringify(Array.from(productIds))
    );
}

export default {
    getWishlistProductIds: getWishlistProductIds,
    setWishlistProductIds: setWishlistProductIds,
};

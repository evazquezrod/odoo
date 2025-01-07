import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { throttleForAnimation } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { extraMenuUpdateCallbacks } from "@website/js/content/menu";
import "@website/libs/zoomodoo/zoomodoo";
import VariantMixin from "@website_sale/js/variant_mixin";
import { ProductImageViewer } from "@website_sale/js/components/website_sale_image_viewer";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { memoize, uniqueId } from "@web/core/utils/functions";
import { insertThousandsSep } from "@web/core/utils/numbers";


publicWidget.registry.WebsiteSaleProduct = publicWidget.Widget.extend(VariantMixin, {
    selector: '.o_wsale_product_page', // '#shop_product', in the future?
    events: {
        'change form .js_product:first input[name="add_qty"]': '_onChangeAddQuantity',
        'change .css_attribute_color input': '_onChangeColorAttribute',
        'change .js_main_product [data-attribute_exclusions]': 'onChangeVariant',
        'click input.js_product_change': 'onChangeVariant', // list view of variants
        'click .o_variant_pills': '_onChangePillsAttribute',
        'click .o_product_page_reviews_link': '_onClickReviewsLink',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

    },
    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);

        this._applyHash();

        // This has to be triggered to compute the "out of stock" feature and the hash variant changes
        this.triggerVariantChange(this.$el);

        // Triggered when selecting a variant of a product in a carousel element
        window.addEventListener("hashchange", (ev) => {
            this._applyHash();
            this.triggerVariantChange(this.$el);
        });

        this._startZoom();

        return def;
    },
    destroy() {
        this._super.apply(this, arguments);
        this._cleanupZoom();
    },

    /**
     * @private
     */
    _onClickReviewsLink: function () {
        $('#o_product_page_reviews_content').collapse('show');
    },
    /* VARIANT SELECTION & CONFIGURATION */

    _applyHash: function () {
        const params = new URLSearchParams(window.location.hash.substring(1));
        if (params.get("attribute_values")) {
            const attributeValueIds = params.get("attribute_values").split(',');
            const inputs = document.querySelectorAll(
                'input.js_variant_change, select.js_variant_change option'
            );
            inputs.forEach((element) => {
                if (attributeValueIds.includes(element.dataset.attributeValueId)) {
                    if (element.tagName === "INPUT") {
                        element.checked = true;
                    } else if (element.tagName === "OPTION") {
                        element.selected = true;
                    }
                }
            });
            this._changeAttribute(['.css_attribute_color', '.o_variant_pills']);
        }
    },
    /**
     * Set the checked values active.
     *
     * @private
     * @param {Array} valueSelectors Selectors
     */
    _changeAttribute: function (valueSelectors) {
        valueSelectors.forEach((selector) => {
            $(selector).removeClass("active").filter(":has(input:checked)").addClass("active");
        });
    },
    /**
     * Will disable attribute value's inputs based on combination exclusions
     * and will disable the "add" button if the selected combination
     * is not available
     *
     * This will check both the exclusions within the product itself and
     * the exclusions coming from the parent product (meaning that this product
     * is an option of the parent product)
     *
     * It will also check that the selected combination does not exactly
     * match a manually archived product
     *
     * @private
     * @param {$.Element} $parent the parent container to apply exclusions
     * @param {Array} combination the selected combination of product attribute values
     */
    _checkExclusions: function ($parent, combination) {
        var self = this;
        var combinationData = $parent
            .find('ul[data-attribute_exclusions]')
            .data('attribute_exclusions');

        $parent
            .find('option, input, label, .o_variant_pills')
            .removeClass('css_not_available')
            .attr('title', function () { return $(this).data('value_name') || ''; })
            .data('excluded-by', '');

        // exclusion rules: array of ptav
        // for each of them, contains array with the other ptav they exclude
        if (combinationData.exclusions) {
            // browse all the currently selected attributes
            Object.values(combination).forEach((current_ptav) => {
                if (combinationData.exclusions.hasOwnProperty(current_ptav)) {
                    // for each exclusion of the current attribute:
                    Object.values(combinationData.exclusions[current_ptav]).forEach((excluded_ptav) => {
                        // disable the excluded input (even when not already selected)
                        // to give a visual feedback before click
                        self._disableInput(
                            $parent,
                            excluded_ptav,
                            current_ptav,
                            combinationData.mapped_attribute_names
                        );
                    });
                }
            });
        }
        // combination exclusions: array of array of ptav
        // for example a product with 3 variation and one specific variation is disabled (archived)
        //  requires the first 2 to be selected for the third to be disabled
        if (combinationData.archived_combinations) {
            combinationData.archived_combinations.forEach((excludedCombination) => {
                const ptavCommon = excludedCombination.filter((ptav) => combination.includes(ptav));
                if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === combination.length)
                ) {
                    // Selected combination is archived, all attributes must be disabled from each other
                    combination.forEach((ptav) => {
                        combination.forEach((ptavOther) => {
                            if (ptav === ptavOther) {
                                return;
                            }
                            self._disableInput(
                                $parent,
                                ptav,
                                ptavOther,
                                combinationData.mapped_attribute_names,
                            );
                        })
                    })
                } else if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === (combination.length - 1))
                ) {
                    // In this case we only need to disable the remaining ptav
                    const disabledPtav = excludedCombination.find((ptav) => !combination.includes(ptav));
                    excludedCombination.forEach((ptav) => {
                        if (ptav === disabledPtav) {
                            return;
                        }
                        self._disableInput(
                            $parent,
                            disabledPtav,
                            ptav,
                            combinationData.mapped_attribute_names,
                        )
                    });
                }
            });
        }
    },
    /**
     * Will disable the input/option that refers to the passed attributeValueId.
     * This is used for showing the user that some combinations are not available.
     *
     * It will also display a message explaining why the input is not selectable.
     * Based on the "excludedBy" and the "productName" params.
     * e.g: Not available with Color: Black
     *
     * @private
     * @param {$.Element} $parent
     * @param {integer} attributeValueId
     * @param {integer} excludedBy The attribute value that excludes this input
     * @param {Object} attributeNames A dict containing all the names of the attribute values
     *   to show a human readable message explaining why the input is disabled.
     * @param {string} [productName] The parent product. If provided, it will be appended before
     *   the name of the attribute value that excludes this input
     *   e.g: Not available with Customizable Desk (Color: Black)
     */
    _disableInput: function ($parent, attributeValueId, excludedBy, attributeNames, productName) {
        var $input = $parent
            .find('option[value=' + attributeValueId + '], input[value=' + attributeValueId + ']');
        $input.addClass('css_not_available');
        $input.closest('label').addClass('css_not_available');
        $input.closest('.o_variant_pills').addClass('css_not_available');

        if (excludedBy && attributeNames) {
            var $target = $input.is('option') ? $input : $input.closest('label').add($input);
            var excludedByData = [];
            if ($target.data('excluded-by')) {
                excludedByData = JSON.parse($target.data('excluded-by'));
            }

            var excludedByName = attributeNames[excludedBy];
            if (productName) {
                excludedByName = productName + ' (' + excludedByName + ')';
            }
            excludedByData.push(excludedByName);

            $target.attr('title', _t('Not available with %s', excludedByData.join(', ')));
            $target.data('excluded-by', JSON.stringify(excludedByData));
        }
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {Event} ev
     * @returns {Deferred}
     */
    _getCombinationInfo: function (ev) {
        if ($(ev.target).hasClass('variant_custom_value')) {
            return Promise.resolve();
        }

        const $parent = $(ev.target).closest('.js_product');
        if(!$parent.length){
            return Promise.resolve();
        }
        const combination = VariantMixin.getSelectedVariantValues($parent);

        return rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt($parent.find('.product_template_id').val()),
            'product_id': this._getProductId($parent),
            'combination': combination,
            'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
            'context': this.context,
            ...this._getOptionalCombinationInfoParam($parent),
        }).then((combinationData) => {
            if (this._shouldIgnoreRpcResult()) {
                return;
            }
            this._onChangeCombination(ev, $parent, combinationData);
            this._checkExclusions($parent, combination);
        });
    },
    /**
     * Hook to add optional info to the combination info call.
     *
     * @param {$.Element} $product
     */
    _getOptionalCombinationInfoParam($product) {
        return {};
    },
    /**
     * Will add the "custom value" input for this attribute value if
     * the attribute value is configured as "custom" (see product_attribute_value.is_custom)
     *
     * @private
     * @param {MouseEvent} ev
     */
    handleCustomValues: function ($target) {
        var $variantContainer;
        var $customInput = false;
        if ($target.is('input[type=radio]') && $target.is(':checked')) {
            $variantContainer = $target.closest('ul').closest('li');
            $customInput = $target;
        } else if ($target.is('select')) {
            $variantContainer = $target.closest('li');
            $customInput = $target
                .find('option[value="' + $target.val() + '"]');
        }

        if ($variantContainer) {
            if ($customInput && $customInput.data('is_custom') === 'True') {
                var attributeValueId = $customInput.data('value_id');
                var attributeValueName = $customInput.data('value_name');

                if ($variantContainer.find('.variant_custom_value').length === 0
                    || $variantContainer
                        .find('.variant_custom_value')
                        .data('custom_product_template_attribute_value_id') !== parseInt(
                            attributeValueId
                        )
                ) {
                    $variantContainer.find('.variant_custom_value').remove();

                    const previousCustomValue = $customInput.attr("previous_custom_value");
                    var $input = $('<input>', {
                        type: 'text',
                        'data-custom_product_template_attribute_value_id': attributeValueId,
                        class: 'variant_custom_value form-control mt-2'
                    });

                    $input.attr('placeholder', attributeValueName);
                    $input.addClass('custom_value_radio');
                    $variantContainer.append($input);
                    if (previousCustomValue) {
                        $input.val(previousCustomValue);
                    }
                }
            } else {
                $variantContainer.find('.variant_custom_value').remove();
            }
        }
    },

    /**
     * This is overridden to handle the "List View of Variants" of the web shop.
     * That feature allows directly selecting the variant from a list instead of selecting the
     * attribute values.
     *
     * Since the layout is completely different, we need to fetch the product_id directly
     * from the selected variant.
     *
     * @override
     */
    _getProductId: function ($parent) {
        if ($parent.find('input.js_product_change').length !== 0) {
            return parseInt($parent.find('input.js_product_change:checked').val());
        }
        else {
            return parseInt($parent.find('.product_id').val());
        }
    },

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the pricelist, the price might change when quantity exceeds a certain amount.
     *
     * @private
     * @param {MouseEvent} ev
     *
     * @returns {void}
     */
    _onChangeAddQuantity: function (ev) {
        const $parent = $(ev.currentTarget).closest('form');
        if ($parent.length > 0) {
            this.triggerVariantChange($parent);
        }
    },

    /**
     * Highlight selected color
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeColorAttribute: function (ev) {
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.css_attribute_color')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {MouseEvent} ev
     * @param {$.Element} $parent
     * @param {Array} combination
     */
    _onChangeCombination: function (ev, $parent, combination) {
        const isCombinationPossible = !!combination.is_combination_possible;
        const $pricePerUom = $parent.find(".o_base_unit_price:first .oe_currency_value");
        if ($pricePerUom.length) {
            if (isCombinationPossible && combination.base_unit_price != 0) {
                $pricePerUom.parents(".o_base_unit_price_wrapper").removeClass("d-none");
                $pricePerUom.text(this._priceToStr(combination.base_unit_price));
                $parent.find(".oe_custom_base_unit:first").text(combination.base_unit_name);
            } else {
                $pricePerUom.parents(".o_base_unit_price_wrapper").addClass("d-none");
            }
        }

        // Triggers a new JS event with the correct payload, which is then handled
        // by the google analytics tracking code.
        // Indeed, every time another variant is selected, a new view_item event
        // needs to be tracked by google analytics.
        if ('product_tracking_info' in combination) {
            const $product = $('#product_detail');
            $product.data('product-tracking-info', combination['product_tracking_info']);
            $product.trigger('view_item_event', combination['product_tracking_info']);
        }
        const addToCart = $parent.find('#add_to_cart_wrap');
        const contactUsButton = $parent.find('#contact_us_wrapper');
        const productPrice = $parent.find('.product_price');
        const quantity = $parent.find('.css_quantity');
        const product_unavailable = $parent.find('#product_unavailable');
        if (combination.prevent_zero_price_sale) {
            productPrice.removeClass('d-inline-block').addClass('d-none');
            quantity.removeClass('d-inline-flex').addClass('d-none');
            addToCart.removeClass('d-inline-flex').addClass('d-none');
            contactUsButton.removeClass('d-none').addClass('d-flex');
            product_unavailable.removeClass('d-none').addClass('d-flex');
        } else {
            productPrice.removeClass('d-none').addClass('d-inline-block');
            quantity.removeClass('d-none').addClass('d-inline-flex');
            addToCart.removeClass('d-none').addClass('d-inline-flex');
            contactUsButton.removeClass('d-flex').addClass('d-none');
            product_unavailable.removeClass('d-flex').addClass('d-none');
        }

        const self = this;
        const $price = $parent.find(".oe_price:first .oe_currency_value");
        const $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        const $compare_price = $parent.find(".oe_compare_list_price")
        $price.text(self._priceToStr(combination.price));
        $default_price.text(self._priceToStr(combination.list_price));

        this._toggleDisable($parent, isCombinationPossible);

        if (combination.has_discounted_price) {
            $default_price
                .closest('.oe_website_sale')
                .addClass("discount");
            $default_price.parent().removeClass('d-none');
            $compare_price.addClass("d-none");
        } else {
            $default_price
                .closest('.oe_website_sale')
                .removeClass("discount");
            $default_price.parent().addClass('d-none');
            $compare_price.removeClass("d-none");
        }

        // update images & tags only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.no_product_change) {
            const rootComponentSelectors = ['tr.js_product', '.oe_website_sale'];
            self._updateProductImage(
                $parent.closest(rootComponentSelectors.join(', ')),
                combination.carousel,
                isCombinationPossible
            );
            $parent
                .find('.o_product_tags')
                .first()
                .html(combination.product_tags);
        }

        $parent
            .find('.product_id')
            .first()
            .val(combination.product_id || 0)
            .trigger('change');

        this.handleCustomValues($(ev.target));
    },

    _onChangePillsAttribute: function (ev) {
        const radio = ev.target.closest('.o_variant_pills').querySelector("input");
        radio.click();  // Trigger onChangeVariant.
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.o_variant_pills')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
    },
    /**
     * When a variant is changed, this will check:
     * - If the selected combination is available or not
     * - The extra price if applicable
     * - The display name of the product ("Customizable desk (White, Steel)")
     * - The new total price
     * - The need of adding a "custom value" input
     *   If the custom value is the only available value
     *   (defined by its data 'is_single_and_custom'),
     *   the custom value will have it's own input & label
     *
     * 'change' events triggered by the user entered custom values are ignored since they
     * are not relevant
     *
     * @override
     */
    onChangeVariant: function (ev) {
        var $component = $(ev.currentTarget).closest('.js_product');
        /*
        * Write the properties of the form elements in the DOM to prevent the
        * current selection from being lost when activating the web editor.
        */
        $component.find('input').each(function () {
            var $el = $(this);
            $el.attr('checked', $el.is(':checked'));
        });
        $component.find('select option').each(function () {
            var $el = $(this);
            $el.attr('selected', $el.is(':selected'));
        });

        this._setUrlHash($component);

        var $parent = $(ev.target).closest('.js_product');
        if (!$parent.data('uniqueId')) {
            $parent.data('uniqueId', uniqueId());
        }
        this._throttledGetCombinationInfo(this, $parent.data('uniqueId'))(ev);
    },
    /**
     * returns the formatted price
     *
     * @private
     * @param {float} price
     */
    _priceToStr: function (price) {
        var precision = 2;

        if ($('.decimal_precision').length) {
            precision = parseInt($('.decimal_precision').last().data('precision'));
        }
        var formatted = price.toFixed(precision).split(".");
        const { thousandsSep, decimalPoint, grouping } = localization;
        formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
        return formatted.join(decimalPoint);
    },

    /**
     * Sets the url hash from the selected product options.
     *
     * @private
     */
    _setUrlHash: function ($parent) {
        const inputs = document.querySelectorAll(
            'input.js_variant_change:checked, select.js_variant_change option:checked'
        );
        let attributeIds = [];
        inputs.forEach((element) => attributeIds.push(element.dataset.attributeValueId));
        if (attributeIds.length > 0) {
            window.location.hash = `attribute_values=${attributeIds.join(',')}`;
        }
    },
    /**
     * Return true if the current object has been destroyed. Useful to know if
     * the result of a rpc should be handled.
     *
     * @private
     */
    _shouldIgnoreRpcResult() {
        return (typeof this.isDestroyed === "function" && this.isDestroyed());
    },
    /**
     * Returns a throttled `_getCombinationInfo` with a leading and a trailing
     * call, which is memoized per `uniqueId`, and for which previous results
     * are dropped.
     *
     * The uniqueId is needed because on the configurator modal there might be
     * multiple elements triggering the rpc at the same time, and we need each
     * individual product rpc to be executed, but only once per individual
     * product.
     *
     * The leading execution is to keep good reactivity on the first call, for
     * a better user experience. The trailing is because ultimately only the
     * information about the last selected combination is useful. All
     * intermediary rpc can be ignored and are therefore best not done at all.
     *
     * The keepLast is to make sure we only consider the result of the last call, when several
     * (asynchronous) calls are done in parallel.
     *
     * @private
     * @param {string} uniqueId
     * @returns {function}
     */
    _throttledGetCombinationInfo: memoize(function (self, uniqueId) {
        const keepLast = new KeepLast();
        var _getCombinationInfo = throttleForAnimation(self._getCombinationInfo.bind(self));
        return (ev, params) => keepLast.add(_getCombinationInfo(ev, params));
    }),
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable: function ($parent, isCombinationPossible) {
        $parent.toggleClass('css_not_available', !isCombinationPossible);
        $parent.find("#add_to_cart").toggleClass('disabled', !isCombinationPossible);
        $parent.find(".o_we_buy_now").toggleClass('disabled', !isCombinationPossible);
    },
    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {$.Element} $container
     */
    triggerVariantChange: function ($container) {
        const self = this;
        $container.find('ul[data-attribute_exclusions]').trigger('change');
        $container.find('input.js_variant_change:checked, select.js_variant_change').each(function () {
            self.handleCustomValues($(this));
        });
    },

    /* IMAGES */
    /**
     * @private
     */
    _startZoom: function () {
        const salePage = document.querySelector(".o_wsale_product_page");
        if (!salePage || this._getProductImageWidth() === "none") {
            return;
        }
        this._cleanupZoom();
        this.zoomCleanup = [];
        // Zoom on hover (except on mobile)
        if (salePage.dataset.ecomZoomAuto && !uiUtils.isSmall()) {
            const images = salePage.querySelectorAll("img[data-zoom]");
            for (const image of images) {
                const $image = $(image);
                const callback = () => {
                    $image.zoomOdoo({
                        event: "mouseenter",
                        attach: this._getProductImageContainerSelector(),
                        preventClicks: salePage.dataset.ecomZoomClick,
                        attachToTarget: this._getProductImageLayout() === "grid",
                    });
                    image.dataset.zoom = 1;
                };
                image.addEventListener('load', callback);
                this.zoomCleanup.push(() => {
                    image.removeEventListener('load', callback);
                    const zoomOdoo = $image.data("zoomOdoo");
                    if (zoomOdoo) {
                        zoomOdoo.hide();
                        $image.unbind();
                    }
                });
                if (image.complete) {
                    callback();
                }
            }
        }
        // Zoom on click
        if (salePage.dataset.ecomZoomClick) {
            // In this case we want all the images not just the ones that are "zoomables"
            const images = salePage.querySelectorAll(".product_detail_img");
            for (const image of images ) {
                const handler = () => {
                    if (salePage.dataset.ecomZoomAuto) {
                        // Remove any flyout
                        const flyouts = document.querySelectorAll(".zoomodoo-flyout");
                        for (const flyout of flyouts) {
                            flyout.remove();
                        }
                    }
                    this.call("dialog", "add", ProductImageViewer, {
                        selectedImageIdx: [...images].indexOf(image),
                        images,
                    });
                };
                image.addEventListener("click", handler);
                this.zoomCleanup.push(() => {
                    image.removeEventListener("click", handler);
                });
            }
        }
    },
    _cleanupZoom() {
        if (!this.zoomCleanup || !this.zoomCleanup.length) {
            return;
        }
        for (const cleanup of this.zoomCleanup) {
            cleanup();
        }
        this.zoomCleanup = undefined;
    },

    _getProductImageContainerSelector: function () {
        return {
            'carousel': "#o-carousel-product",
            'grid': "#o-grid-product",
        }[this._getProductImageLayout()];
    },
    _getProductImageContainer: function () {
        return document.querySelector(this._getProductImageContainerSelector());
    },
    _getProductImageLayout: function () {
        return document.querySelector("#product_detail_main").dataset.image_layout;
    },
    _getProductImageWidth: function () {
        return document.querySelector("#product_detail_main").dataset.image_width;
    },
    _isEditorEnabled() {
        return document.body.classList.contains("editor_enable");
    },
    /**
     * Updates the product image.
     * This will use the productId if available or will fallback to the productTemplateId.
     *
     * @override
     * @private
     */
    _updateProductImage: function ($productContainer, newImages, isCombinationPossible) {
        let $images = $productContainer.find(this._getProductImageContainerSelector());
        // When using the web editor, don't reload this or the images won't
        // be able to be edited depending on if this is done loading before
        // or after the editor is ready.
        if ($images.length && !this._isEditorEnabled()) {
            const $newImages = $(newImages);
            $images.after($newImages);
            $images.remove();
            $images = $newImages;
            // Update the sharable image (only work for Pinterest).
            const shareImageSrc = $images[0].querySelector('img').src;
            document.querySelector('meta[property="og:image"]')
                .setAttribute('content', shareImageSrc);

            if ($images.attr('id') === 'o-carousel-product') {
                $images.carousel(0);
            }
            this._startZoom();
            // fix issue with carousel height
            this.trigger_up('widgets_start_request', {$target: $images});
        }
        $images.toggleClass('css_not_available', !isCombinationPossible);
    },
});

publicWidget.registry.websiteSaleProductPageReviews = publicWidget.Widget.extend({
    selector: '#o_product_page_reviews',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateChatterComposerPosition();
        extraMenuUpdateCallbacks.push(this._updateChatterComposerPosition.bind(this));
    },
    /**
     * @override
     */
    destroy() {
        this.$el.find('.o_portal_chatter_composer').css('top', '');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateChatterComposerPosition() {
        let size = 20;
        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            size += $(el).outerHeight();
        }
        this.$el.find('.o_portal_chatter_composer').css('top', size);
    },
});

publicWidget.registry.WebsiteSaleAccordionProduct = publicWidget.Widget.extend({
    selector: "#product_accordion",

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateAccordionActiveItem();
    },

    /**
     * Replace the .SCSS styling applied awaiting Js for the default bootstrap classes,
     * opening the first accordion entry and restoring flush behavior.
     *
     * @private
     */
    _updateAccordionActiveItem() {
        const firstAccordionItemEl = this.el.querySelector('.accordion-item');
        if (!firstAccordionItemEl) return;

        const firstAccordionItemButtonEl = firstAccordionItemEl.querySelector('.accordion-button');
        firstAccordionItemButtonEl.classList.remove('collapsed');
        firstAccordionItemButtonEl.setAttribute('aria-expanded', 'true');
        firstAccordionItemEl.querySelector('.accordion-collapse').classList.add('show');
        this.target.classList.remove('o_accordion_not_initialized');
    },
});

publicWidget.registry.websiteSaleCarouselProduct = publicWidget.Widget.extend({
    selector: '#o-carousel-product',
    disabledInEditableMode: false,
    events: {
        'wheel .o_carousel_product_indicators': '_onMouseWheel',
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateCarouselPosition();
        this.throttleOnResize = throttleForAnimation(this._onSlideCarouselProduct.bind(this));
        extraMenuUpdateCallbacks.push(this._updateCarouselPosition.bind(this));
        if (this.$el.find('.carousel-indicators').length > 0) {
            this.$el.on('slide.bs.carousel.carousel_product_slider', this._onSlideCarouselProduct.bind(this));
            $(window).on('resize.carousel_product_slider', this.throttleOnResize);
            this._updateJustifyContent();
        }
    },
    /**
     * @override
     */
    destroy() {
        this.$el.css('top', '');
        this.$el.off('.carousel_product_slider');
        if (this.throttleOnResize) {
            this.throttleOnResize.cancel();
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateCarouselPosition() {
        let size = 5;
        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            size += $(el).outerHeight();
        }
        this.$el.css('top', size);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Center the selected indicator to scroll the indicators list when it
     * overflows.
     *
     * @private
     * @param {Event} ev
     */
    _onSlideCarouselProduct: function (ev) {
        const isReversed = this.$el.css('flex-direction') === "column-reverse";
        const isLeftIndicators = this.$el.hasClass('o_carousel_product_left_indicators');
        const $indicatorsDiv = isLeftIndicators ? this.$el.find('.o_carousel_product_indicators') : this.$el.find('.carousel-indicators');
        let indicatorIndex = $(ev.relatedTarget).index();
        indicatorIndex = indicatorIndex > -1 ? indicatorIndex : this.$el.find('li.active').index();
        const $indicator = $indicatorsDiv.find('[data-bs-slide-to=' + indicatorIndex + ']');
        const indicatorsDivSize = isLeftIndicators && !isReversed ? $indicatorsDiv.outerHeight() : $indicatorsDiv.outerWidth();
        const indicatorSize = isLeftIndicators && !isReversed ? $indicator.outerHeight() : $indicator.outerWidth();
        const indicatorPosition = isLeftIndicators && !isReversed ? $indicator.position().top : $indicator.position().left;
        const scrollSize = isLeftIndicators && !isReversed ? $indicatorsDiv[0].scrollHeight : $indicatorsDiv[0].scrollWidth;
        let indicatorsPositionDiff = (indicatorPosition + (indicatorSize/2)) - (indicatorsDivSize/2);
        indicatorsPositionDiff = Math.min(indicatorsPositionDiff, scrollSize - indicatorsDivSize);
        this._updateJustifyContent();
        const indicatorsPositionX = isLeftIndicators && !isReversed ? '0' : '-' + indicatorsPositionDiff;
        const indicatorsPositionY = isLeftIndicators && !isReversed ? '-' + indicatorsPositionDiff : '0';
        const translate3D = indicatorsPositionDiff > 0 ? "translate3d(" + indicatorsPositionX + "px," + indicatorsPositionY + "px,0)" : '';
        $indicatorsDiv.css("transform", translate3D);
    },
    /**
     * @private
     */
     _updateJustifyContent: function () {
        const $indicatorsDiv = this.$el.find('.carousel-indicators');
        $indicatorsDiv.css('justify-content', 'start');
        if (uiUtils.getSize() <= SIZES.MD) {
            if (($indicatorsDiv.children().last().position().left + this.$el.find('li').outerWidth()) < $indicatorsDiv.outerWidth()) {
                $indicatorsDiv.css('justify-content', 'center');
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseWheel: function (ev) {
        ev.preventDefault();
        if (ev.originalEvent.deltaY > 0) {
            this.$el.carousel('next');
        } else {
            this.$el.carousel('prev');
        }
    },
});

export default {
    WebsiteSaleProduct: publicWidget.registry.WebsiteSaleProduct,
    websiteSaleProductPageReviews: publicWidget.registry.websiteSaleProductPageReviews,
    WebsiteSaleAccordionProduct: publicWidget.registry.WebsiteSaleAccordionProduct,
    WebsiteSaleCarouselProduct: publicWidget.registry.websiteSaleCarouselProduct,
}

import { getValueFromVar, isMobileView } from "@html_builder/utils/utils";
import {
    normalizeColor,
    getCSSVariableValue,
    getBgImageURLFromEl,
} from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { backgroundShapesDefinition } from "./background_shapes_definition";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";
import { getDefaultColors } from "./background_shape_option";
import { withSequence } from "@html_editor/utils/resource";
import { getBgImageURLFromURL } from "@html_editor/utils/image";
import { BuilderAction } from "@html_builder/core/builder_action";
import { rgbToHex } from "@web/core/utils/colors";

export class BackgroundShapeOptionPlugin extends Plugin {
    static id = "backgroundShapeOption";
    static dependencies = ["customizeTab"];
    resources = {
        builder_actions: {
            SetBackgroundShapeAction,
            ToggleBgShapeAction,
            ShowOnMobileAction,
            FlipShapeAction,
            SetBgAnimationSpeedAction,
            BackgroundShapeColorAction,
            handleBgColorChangedAction,
        },
        background_shape_target_providers: withSequence(5, (editingElement) =>
            editingElement.querySelector(":scope > .o_we_bg_filter")
        ),
        on_moved_handlers: ({ movedEl, siblingEl }) => {
            this.handleBgColorChanged(movedEl);
            this.handleBgColorChanged(siblingEl);
        },
        after_remove_handlers: ({ elementToSelect }) => {
            this.handleBgColorChanged(elementToSelect);
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            this.handleBgColorChanged(snippetEl);
        },
        on_cloned_handlers: ({ cloneEl, originalEl }) => {
            this.handleBgColorChanged(cloneEl);
            this.handleBgColorChanged(originalEl);
        },
    };
    static shared = [
        "getShapeStyleUrl",
        "getShapeData",
        "showBackgroundShapes",
        "getBackgroundShapes",
        "getImplicitColors",
        "applyShape",
        "createShapeContainer",
        "handleBgColorChanged",
    ];
    setup() {
        // TODO: update shapeBackgroundImagePerClass if a stylesheet value
        // changes.
        this.shapeBackgroundImagePerClass = {};
        for (const styleSheet of this.document.styleSheets) {
            if (styleSheet.href && new URL(styleSheet.href).host !== location.host) {
                // In some browsers, if a stylesheet is loaded from a different
                // domain accessing cssRules results in a SecurityError.
                continue;
            }
            for (const rule of [...styleSheet.cssRules]) {
                if (rule.selectorText && rule.selectorText.startsWith(".o_we_shape.")) {
                    this.shapeBackgroundImagePerClass[rule.selectorText] =
                        rule.style.backgroundImage;
                }
            }
        }
        // Flip classes should no longer be used but are still present in some
        // theme snippets.
        const flipEls = [...this.editable.querySelectorAll(".o_we_flip_x, .o_we_flip_y")];
        for (const flipEl of flipEls) {
            this.applyShape(flipEl, () => ({ flip: this.getShapeData(flipEl).flip }));
        }
    }
    /**
     * Handles everything related to saving state before preview and restoring
     * it after a preview or locking in the changes when not in preview.
     *
     * @param {HTMLElement} editingElement - The element being edited
     * @param {Function} computeShapeData - Function to compute the new shape
     * data.
     */
    applyShape(editingElement, computeShapeData) {
        const newShapeData = computeShapeData();
        const changedShape = !!newShapeData.shape;
        this.markShape(editingElement, newShapeData);

        // Updates/removes the shape container as needed and gives it the
        // correct background shape
        const json = editingElement.dataset.oeShapeData;
        const {
            shape,
            colors,
            flip = [],
            animated = "false",
            showOnMobile,
            shapeAnimationSpeed,
        } = json ? JSON.parse(json) : {};

        let shapeContainerEl = editingElement.querySelector(":scope > .o_we_shape");

        if (!shape) {
            return this.insertShapeContainer(editingElement, null);
        }

        if (changedShape) {
            // Reset shape container when shape changes (e.g., for transparent
            // color)
            shapeContainerEl = this.createShapeContainer(editingElement, shape);
        }

        // Remove old flip classes (flipping is now done via SVG)
        shapeContainerEl.classList.remove("o_we_flip_x", "o_we_flip_y");

        shapeContainerEl.classList.toggle("o_we_animated", animated === "true");

        const shouldCustomize =
            Boolean(colors) || flip.length > 0 || parseFloat(shapeAnimationSpeed) !== 0;

        if (shouldCustomize) {
            // Apply custom image, flip, speed
            shapeContainerEl.style.setProperty(
                "background-image",
                `url("${this.getShapeSrc(editingElement)}")`
            );
            shapeContainerEl.style.backgroundPosition = "";

            if (flip.length) {
                let [xPos, yPos] = getComputedStyle(shapeContainerEl)
                    .backgroundPosition.split(" ")
                    .map(parseFloat);

                xPos = flip.includes("x") ? -xPos + 100 : xPos;
                yPos = flip.includes("y") ? -yPos + 100 : yPos;

                shapeContainerEl.style.backgroundPosition = `${xPos}% ${yPos}%`;
            }
        } else {
            // Let CSS class define the shape
            shapeContainerEl.style.setProperty("background-image", "");
            shapeContainerEl.style.setProperty("background-position", "");
        }

        shapeContainerEl.classList.toggle("o_shape_show_mobile", Boolean(showOnMobile));
    }

    /**
     * Creates and inserts a container for the shape with the right classes.
     *
     * @param {HTMLElement} editingElement - The element to which the shape is attached.
     * @param {string} shape - The shape name used to generate a class.
     * @returns {HTMLElement} The created shape container element.
     */
    createShapeContainer(editingElement, shape) {
        const shapeContainer = this.insertShapeContainer(
            editingElement,
            document.createElement("div")
        );
        editingElement.style.setProperty("position", "relative");
        shapeContainer.className = `o_we_shape o_${shape.replace(/\//g, "_")}`;
        return shapeContainer;
    }
    /**
     * Returns the implicit colors for the currently selected shape.
     *
     * The implicit colors are use upon shape selection. They are computed as:
     * - the default colors
     * - patched with each set of colors of previous siblings shape
     * - patched with the colors of the previously selected shape
     * - filtered to only keep the colors involved in the current shape
     *
     * @param {HTMLElement} editingElement
     * @param {String} shapeName identifier of the selected shape.
     * @param {Object} previousColors colors of the shape before its
     * replacement.
     */
    getImplicitColors(editingElement, shapeName, previousColors = {}) {
        const selectedBackgroundUrl = this.getShapeStyleUrl(shapeName);
        const defaultColors = this.getShapeDefaultColors(selectedBackgroundUrl);
        let colors = previousColors;
        colors = Object.assign(this.getConnectionsColors(editingElement, shapeName), colors);
        let sibling = editingElement.previousElementSibling;
        while (sibling) {
            colors = Object.assign(this.getShapeData(sibling).colors || {}, colors);
            sibling = sibling.previousElementSibling;
        }
        const defaultKeys = Object.keys(defaultColors);
        colors = Object.assign(defaultColors, colors);
        return pick(colors, ...defaultKeys);
    }
    /**
     * Returns the default colors for the a shape in the selector.
     *
     * @param {String} selectedBackgroundUrl
     */
    getShapeDefaultColors(selectedBackgroundUrl) {
        const shapeSrc = selectedBackgroundUrl && getBgImageURLFromURL(selectedBackgroundUrl);
        const url = new URL(shapeSrc, window.location.origin);
        return Object.fromEntries(url.searchParams.entries().filter(([key]) => key !== "flip"));
    }
    /**
     * Retrieves current shape data from the target's dataset.
     *
     * @param {HTMLElement} editingElement the target on which to read the shape
     * data.
     */
    getShapeData(editingElement) {
        const defaultData = {
            shape: "",
            colors: getDefaultColors(editingElement),
            flip: [],
            showOnMobile: false,
            shapeAnimationSpeed: "0",
        };
        const json = editingElement.dataset.oeShapeData;
        return json ? Object.assign(defaultData, JSON.parse(json.replace(/'/g, '"'))) : defaultData;
    }
    /**
     * Returns the src of the shape corresponding to the current parameters.
     *
     * @param {HTMLElement} editingElement
     */
    getShapeSrc(editingElement) {
        const { shape, colors, flip, shapeAnimationSpeed } = this.getShapeData(editingElement);
        if (!shape) {
            return "";
        }
        const searchParams = Object.entries(colors).map(([colorName, colorValue]) => {
            const encodedCol = encodeURIComponent(colorValue);
            return `${colorName}=${encodedCol}`;
        });
        if (flip.length) {
            searchParams.push(`flip=${encodeURIComponent(flip.sort().join(""))}`);
        }
        if (Number(shapeAnimationSpeed)) {
            searchParams.push(`shapeAnimationSpeed=${encodeURIComponent(shapeAnimationSpeed)}`);
        }
        return `/web_editor/shape/${encodeURIComponent(shape)}.svg?${searchParams.join("&")}`;
    }
    /**
     *
     * @param {String} shapeId
     */
    getShapeStyleUrl(shapeId) {
        const shapeClassName = `o_${shapeId.replace(/\//g, "_")}`;
        // Match current palette
        return this.shapeBackgroundImagePerClass[`.o_we_shape.${shapeClassName}`];
    }
    /**
     * Inserts or removes the given container at the right position in the
     * document.
     *
     * @param {HTMLElement} editingElement
     * @param {HTMLElement} newContainer container to insert, null to remove
     */
    insertShapeContainer(editingElement, newContainer) {
        const shapeContainerEl = editingElement.querySelector(":scope > .o_we_shape");
        if (shapeContainerEl) {
            this.removeShapeEl(shapeContainerEl);
        }
        if (newContainer) {
            let preShapeLayerEl;
            for (const fn of this.getResource("background_shape_target_providers")) {
                preShapeLayerEl = fn(editingElement);
                if (preShapeLayerEl) {
                    break;
                }
            }
            if (preShapeLayerEl) {
                preShapeLayerEl.insertAdjacentElement("afterend", newContainer);
            } else {
                editingElement.prepend(newContainer);
            }
        }
        return newContainer;
    }
    /**
     * Overwrites shape properties with the specified data.
     *
     * @param {HTMLElement} editingElement
     * @param {Object} newData an object with the new data
     */
    markShape(editingElement, newData) {
        const defaultColors = getDefaultColors(editingElement);
        const shapeData = Object.assign(this.getShapeData(editingElement), newData);
        const areColorsDefault = Object.entries(shapeData.colors).every(
            ([colorName, colorValue]) =>
                defaultColors[colorName] &&
                colorValue.toLowerCase() === defaultColors[colorName].toLowerCase()
        );
        if (areColorsDefault) {
            delete shapeData.colors;
        }
        if (!shapeData.shape) {
            delete editingElement.dataset.oeShapeData;
        } else {
            editingElement.dataset.oeShapeData = JSON.stringify(shapeData);
        }
    }
    /**
     *
     * @param {HTMLElement} shapeEl
     */
    removeShapeEl(shapeEl) {
        shapeEl.remove();
    }
    showBackgroundShapes(editingElements) {
        this.dependencies.customizeTab.openCustomizeComponent(ShapeSelector, editingElements, {
            shapeActionId: "setBackgroundShape",
            buttonWrapperClassName: "o-hb-bg-shape-btn",
            selectorTitle: _t("Background Shapes"),
            shapeGroups: this.getBackgroundShapeGroups(),
            imgThroughDiv: true,
            getShapeUrl: this.getShapeStyleUrl.bind(this),
        });
    }
    getBackgroundShapeGroups() {
        return backgroundShapesDefinition;
    }
    getBackgroundShapes() {
        const entries = Object.values(this.getBackgroundShapeGroups())
            .map((x) =>
                Object.values(x.subgroups)
                    .map((x) => Object.entries(x.shapes))
                    .flat()
            )
            .flat();
        return Object.fromEntries(entries);
    }
    handleBgColorChanged(editingElement) {
        //if color is previous implicit color ?
        //if connection shape TODO
        const { shape } = this.getShapeData(editingElement);
        if (shape) {
            this.applyShape(editingElement, () => ({
                colors: this.getImplicitColors(editingElement, shape),
            }));
        }
        const elements = this.getNeighborShape(editingElement);
        for (const element of elements) {
            this.updateShapeForNeighbor(element);
        }
    }
    /**
     * Returns the computed colors for the currently selected Connections shape.
     *
     * The color is computed based on the bgcolor of the next snippet or on the bgcolor
     * of the previous if the shape flip on Y.
     *
     * @private
     * @param {String} shape identifier of the selected shape.
     * @param {Element} target Element for which the color has to be computed.
     */
    getConnectionsColors(editingElement, shapeName) {
        if (!shapeName.includes("web_editor/Connections/")) {
            return {};
        }
        const selectedBackgroundUrl = this.getShapeStyleUrl(shapeName);
        const defaultColors = this.getShapeDefaultColors(selectedBackgroundUrl);
        const defaultKey = Object.keys(defaultColors)[0];
        const targetRect = editingElement.getBoundingClientRect();
        const shapeData = this.getShapeData(editingElement);
        const x = targetRect.left + targetRect.width / 2;
        const effectiveFlipY =
            this.flipYPending !== null ? this.flipYPending : shapeData.flip.includes("y");
        this.flipYPending = null;
        const y = effectiveFlipY ? targetRect.top - 1 : targetRect.bottom + 1;
        const neighborEl = this.getBackgroundElementFromPoint(editingElement, x, y);
        const neighborElHexColor = rgbToHex(getComputedStyle(neighborEl).backgroundColor);

        let curBgColorEl = editingElement;
        while (getComputedStyle(curBgColorEl).backgroundColor.includes("rgba(0, 0, 0, 0)")) {
            curBgColorEl = curBgColorEl.parentElement;
        }
        const curBgHexColor = rgbToHex(getComputedStyle(curBgColorEl).backgroundColor);

        return {
            ...defaultColors,
            [defaultKey]:
                curBgHexColor !== neighborElHexColor
                    ? neighborElHexColor
                    : this.getContrastingColor(neighborElHexColor),
        };
    }
    /**
     * Compute the luminance of a color.
     *
     * @private
     */
    getLuminance(color) {
        const hexColor = rgbToHex(color);
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5), 16);
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    /**
     * Return the color of the current theme with the most contrast compared to
     * the given color.
     *
     * @private
     */
    getContrastingColor(baseColor) {
        const baseLuminance = this.getLuminance(baseColor);

        const colors = ["o-color-1", "o-color-2", "o-color-3", "o-color-4", "o-color-5"];
        const luminances = colors.map((color) => {
            const colorValue = getCSSVariableValue(color);
            return { color, luminance: this.getLuminance(colorValue) };
        });

        let bestContrast;
        let maxDifference = 0;

        for (const { color, luminance } of luminances) {
            const difference = Math.abs(baseLuminance - luminance);
            if (difference > maxDifference) {
                maxDifference = difference;
                bestContrast = color;
            }
        }

        return getCSSVariableValue(bestContrast);
    }
    getElementsFromPoint(editingElement, viewportX, viewportY) {
        const iframeDoc = editingElement.ownerDocument;
        const iframeWin = iframeDoc.defaultView;
        const pageX = iframeWin.scrollX + viewportX;
        const pageY = iframeWin.scrollY + viewportY;
        let elements;
        if (
            viewportX < 0 ||
            viewportY < 0 ||
            viewportX > iframeWin.innerWidth ||
            viewportY > iframeWin.innerHeight
        ) {
            elements = [...iframeDoc.querySelectorAll("*")].filter((el) => {
                const rect = el.getBoundingClientRect();
                return (
                    pageX >= iframeWin.scrollX + rect.left &&
                    pageX <= iframeWin.scrollX + rect.right &&
                    pageY >= iframeWin.scrollY + rect.top &&
                    pageY <= iframeWin.scrollY + rect.bottom
                );
            });
            elements.reverse();
        } else {
            elements = iframeDoc.elementsFromPoint(viewportX, viewportY);
        }
        const header = iframeDoc.querySelector("header");
        if (header) {
            const headerHeight = header.offsetHeight;
            const isHeaderSidebar = header.classList.contains("o_header_sidebar");
            if (pageY < headerHeight && !isHeaderSidebar) {
                elements.unshift(iframeDoc.querySelector("nav"));
            }
        }
        return elements;
    }
    // Get the first element with a bg color on the point.
    getBackgroundElementFromPoint(editingElement, viewportX, viewportY) {
        const iframeDoc = editingElement.ownerDocument;
        const elements = this.getElementsFromPoint(editingElement, viewportX, viewportY);
        const classBlacklist = [".o_handles", ".o_header_is_scrolled"];
        const idBlacklist = ["wrap"];
        const element = elements.find(
            (el) =>
                el.tagName.toLowerCase() !== "html" &&
                !classBlacklist.some((cls) => el.closest(cls)) &&
                !idBlacklist.includes(el.id) &&
                !getComputedStyle(el).backgroundColor.includes("rgba(0, 0, 0, 0)")
        );
        return element || iframeDoc.querySelector("body");
    }
    findElementsWithShape(element) {
        if (!element || element.tagName === "BODY") {
            return [];
        }
        while (element.parentElement?.closest("[data-snippet]")) {
            element = element.parentElement.closest("[data-snippet]");
        }
        const allEl = [element, ...element.querySelectorAll("*")];
        const allShapeEl = allEl.filter((el) => el.querySelector(":scope > .o_we_shape"));
        return allShapeEl;
    }
    isShapeNeighbor(editingElement, shapeTarget) {
        if (!shapeTarget.querySelector(".o_we_shape")) {
            return false;
        }
        const targetRect = shapeTarget.getBoundingClientRect();
        const shapeData = this.getShapeData(shapeTarget);
        const x = targetRect.left + targetRect.width / 2;
        const y = shapeData.flip.includes("y") ? targetRect.top - 1 : targetRect.bottom + 1;
        return this.getElementsFromPoint(shapeTarget, x, y).includes(editingElement);
    }
    getNeighborShape(editingElement, direction) {
        const targetRect = editingElement.getBoundingClientRect();
        const x = targetRect.left + targetRect.width / 2;
        let y;
        switch (direction) {
            case "top":
                y = targetRect.top - 1;
                break;
            case "bottom":
                y = targetRect.bottom + 1;
                break;
            case "inner": {
                const innerElements = this.findElementsWithShape(editingElement);
                return innerElements.filter((el) => this.isShapeNeighbor(editingElement, el));
            }
            default: {
                const topNeighbors = this.getNeighborShape(editingElement, "top");
                const bottomNeighbors = this.getNeighborShape(editingElement, "bottom");
                const innerNeighbors = this.getNeighborShape(editingElement, "inner");
                return [...topNeighbors, ...bottomNeighbors, ...innerNeighbors];
            }
        }
        const elements = this.getElementsFromPoint(editingElement, x, y);
        const element = elements.find((el) => el.querySelector(":scope > .o_we_shape"));
        const ShapeElements = this.findElementsWithShape(element);
        return ShapeElements.filter((el) => this.isShapeNeighbor(editingElement, el));
    }
    updateShapeForNeighbor(snippetEl, newColor) {
        if (!snippetEl) {
            return;
        }
        const shapeEl = snippetEl.querySelector(".o_we_shape");
        if (!shapeEl) {
            return;
        }
        const shapeData = this.getShapeData(snippetEl);
        if (!shapeData.shape.includes("web_editor/Connections")) {
            return;
        }
        const defaultColor = getDefaultColors(snippetEl);
        const defaultKeys = Object.keys(defaultColor);
        newColor = newColor
            ? { [defaultKeys[0]]: rgbToHex(newColor) }
            : this.getConnectionsColors(snippetEl, shapeData.shape);

        if (JSON.stringify(shapeData.colors) === JSON.stringify(newColor)) {
            return;
        }
        let shapeBackgroundImageURL = getBgImageURLFromEl(shapeEl);
        if (shapeBackgroundImageURL) {
            const url = new URL(shapeBackgroundImageURL, window.location.origin);
            Object.entries(newColor).forEach(([key, value]) => {
                url.searchParams.set(key, value);
            });
            shapeBackgroundImageURL = `url("${url.toString()}")`;
            shapeEl.style.backgroundImage = shapeBackgroundImageURL;
        }
        if (JSON.stringify(defaultColor) === JSON.stringify(newColor) && !shapeData.flip.length) {
            shapeEl.style.removeProperty("background-image");
        }
        shapeData.colors = { ...shapeData.colors, ...newColor };
        snippetEl.dataset.oeShapeData = JSON.stringify(shapeData);
    }
}

class BaseAnimationAction extends BuilderAction {
    static id = "baseAnimation";
    static dependencies = ["backgroundShapeOption"];
    setup() {
        this.applyShape = this.dependencies.backgroundShapeOption.applyShape;
        this.getShapeData = this.dependencies.backgroundShapeOption.getShapeData;
        this.getImplicitColors = this.dependencies.backgroundShapeOption.getImplicitColors;
        this.getBackgroundShapes = this.dependencies.backgroundShapeOption.getBackgroundShapes;
        this.createShapeContainer = this.dependencies.backgroundShapeOption.createShapeContainer;
        this.showBackgroundShapes = this.dependencies.backgroundShapeOption.showBackgroundShapes;
        this.handleBgColorChanged = this.dependencies.backgroundShapeOption.handleBgColorChanged;
    }
}
class SetBackgroundShapeAction extends BaseAnimationAction {
    static id = "setBackgroundShape";
    apply({ editingElement, params, value }) {
        params = params || {};
        const shapeData = this.getShapeData(editingElement);
        const applyShapeParams = {
            shape: value,
            colors: this.getImplicitColors(editingElement, value, shapeData.colors),
            flip: shapeData.flip,
            animated: params.animated,
            shapeAnimationSpeed: shapeData.shapeAnimationSpeed,
        };
        this.applyShape(editingElement, () => applyShapeParams);
    }
    isApplied({ editingElement, value }) {
        const currentShapeApplied = this.getShapeData(editingElement).shape;
        return currentShapeApplied === value;
    }
}
class ToggleBgShapeAction extends BaseAnimationAction {
    static id = "toggleBgShape";
    apply({ editingElement }) {
        const previousSibling = editingElement.previousElementSibling;
        let shapeToSelect;
        const allPossiblesShapesUrl = Object.keys(this.getBackgroundShapes());
        if (previousSibling) {
            const previousShape = this.getShapeData(previousSibling).shape;
            shapeToSelect = allPossiblesShapesUrl.find(
                (shape, i) => allPossiblesShapesUrl[i - 1] === previousShape
            );
        }
        // If there is no previous sibling, if the previous sibling
        // had the last shape selected or if the previous shape
        // could not be found in the possible shapes, default to the
        // first shape.
        if (!shapeToSelect) {
            shapeToSelect = allPossiblesShapesUrl[0];
        }
        // Only show on mobile by default if toggled from mobile
        // view.
        const showOnMobile = isMobileView(editingElement);
        this.createShapeContainer(editingElement, shapeToSelect);
        const applyShapeParams = {
            shape: shapeToSelect,
            colors: this.getImplicitColors(editingElement, shapeToSelect),
            showOnMobile,
        };
        this.applyShape(editingElement, () => applyShapeParams);
        this.showBackgroundShapes([editingElement]);
    }
    clean({ editingElement }) {
        this.applyShape(editingElement, () => ({ shape: "" }));
    }
    isApplied({ editingElement }) {
        return !!this.getShapeData(editingElement).shape;
    }
}
class ShowOnMobileAction extends BaseAnimationAction {
    static id = "showOnMobile";
    apply({ editingElement }) {
        this.applyShape(editingElement, () => ({
            showOnMobile: false,
        }));
    }
    clean({ editingElement }) {
        this.applyShape(editingElement, () => ({
            showOnMobile: true,
        }));
    }
    isApplied({ editingElement }) {
        return !this.getShapeData(editingElement).showOnMobile;
    }
}
class FlipShapeAction extends BaseAnimationAction {
    static id = "flipShape";
    apply({ editingElement, params: { mainParam: axis } }) {
        let { shape, flip } = this.getShapeData(editingElement);
        this.applyShape(editingElement, () => {
            flip = new Set(flip);
            flip.add(axis);
            return { flip: [...flip] };
        });
        if (axis === "y") {
            this.applyShape(editingElement, () => ({
                colors: this.getImplicitColors(editingElement, shape),
            }));
        }
    }
    clean({ editingElement, params: { mainParam: axis } }) {
        let { shape, flip } = this.getShapeData(editingElement);
        this.applyShape(editingElement, () => {
            flip = new Set(flip);
            flip.delete(axis);
            return { flip: [...flip] };
        });
        if (axis === "y") {
            this.applyShape(editingElement, () => ({
                colors: this.getImplicitColors(editingElement, shape),
            }));
        }
    }
    isApplied({ editingElement, params: { mainParam: axis } }) {
        // Compat: flip classes are no longer used but may be
        // present in client db.
        const selector = `.o_we_flip_${axis}`;
        const hasFlipClass = !!editingElement.querySelector(`:scope > .o_we_shape${selector}`);
        return hasFlipClass || this.getShapeData(editingElement).flip.includes(axis);
    }
}
class SetBgAnimationSpeedAction extends BaseAnimationAction {
    static id = "setBgAnimationSpeed";
    apply({ editingElement, value }) {
        this.applyShape(editingElement, () => ({
            shapeAnimationSpeed: value,
        }));
    }
    getValue({ editingElement }) {
        return this.getShapeData(editingElement).shapeAnimationSpeed;
    }
}
class BackgroundShapeColorAction extends BaseAnimationAction {
    static id = "backgroundShapeColor";
    getValue({ editingElement, params: { mainParam: colorName } }) {
        // TODO check if it works when the colorpicker is
        // implemented.
        const { shape, colors: customColors } = this.getShapeData(editingElement);
        const colors = Object.assign(getDefaultColors(editingElement), customColors);
        const color = shape && colors[colorName];
        return (color && normalizeColor(color)) || "";
    }
    apply({ editingElement, params: { mainParam: colorName }, value }) {
        this.applyShape(editingElement, () => {
            value = getValueFromVar(value);
            const { colors: previousColors } = this.getShapeData(editingElement);
            const newColor = value || getDefaultColors(editingElement)[colorName];
            const newColors = Object.assign(previousColors, { [colorName]: newColor });
            return { colors: newColors };
        });
    }
}
class handleBgColorChangedAction extends BaseAnimationAction {
    static id = "handleBgColorChanged";
    apply({ editingElement }) {
        this.handleBgColorChanged(editingElement);
    }
}

registry
    .category("website-plugins")
    .add(BackgroundShapeOptionPlugin.id, BackgroundShapeOptionPlugin);

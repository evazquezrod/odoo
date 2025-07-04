/* global Prism */

import { Plugin } from "@html_editor/plugin";
import { loadBundle } from "@web/core/assets";
import { CodeToolbar } from "./code_toolbar";
import { descendants, lastLeaf } from "@html_editor/utils/dom_traversal";

const LANGUAGES = {
    plaintext: "Plain Text",
    markdown: "Markdown",
    javascript: "Javascript",
    typescript: "Typescript",
    jsdoc: "JSDoc",
    java: "Java",
    python: "Python",
    html: "HTML",
    xml: "XML",
    svg: "SVG",
    json: "JSON",
    css: "CSS",
    sass: "SASS",
    scss: "SCSS",
    sql: "SQL",
    diff: "Diff",
};
const DEFAULT_LANGUAGE_ID = "plaintext";

export class SyntaxHighlightingPlugin extends Plugin {
    static id = "syntaxHighlighting";
    static dependencies = ["overlay", "history", "selection", "protectedNode"];
    resources = {
        normalize_handlers: (root) => this.prepareCodeBlocks(root, true),
        post_undo_handlers: () => this.prepareCodeBlocks(this.editable, true),
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.codeToolbar = this.dependencies.overlay.createOverlay(CodeToolbar, {
            positionOptions: {
                position: "top-fit",
                flip: false,
            },
            closeOnPointerdown: false,
        });
        this.addGlobalDomListener("pointermove", this.onMouseMove);
        this.addGlobalDomListener("click", this.onMouseMove);
        this.addDomListener(this.document, "scroll", this.codeToolbar.close, true);
        this.prepareCodeBlocks();
        const pres = this.editable.querySelectorAll("pre");
        if (pres.length) {
            this.loadPrism();
        }
    }

    destroy() {
        for (const codeBlock of this.editable.querySelectorAll("div.o_syntax_highlighting")) {
            this.removeListeners(codeBlock);
        }
    }

    loadPrism() {
        return loadBundle("html_editor.assets_prism");
    }

    prepareCodeBlocks(root = this.editable, activate = false) {
        let activeTextarea =
            this.document.activeElement.nodeName === "TEXTAREA" && this.document.activeElement;
        const textareaSelection = {
            start: activeTextarea?.selectionStart || 0,
            end: activeTextarea?.selectionEnd || 0,
            direction: activeTextarea?.selectionDirection || "forward",
        };
        for (const pre of root.querySelectorAll("pre")) {
            if (!pre.closest("div.o_syntax_highlighting")) {
                const font = getComputedStyle(pre).font.replaceAll('"', "'");
                const div = this.document.createElement("div");
                div.classList.add("o_syntax_highlighting");
                div.dataset.languageId = DEFAULT_LANGUAGE_ID;
                div.style.font = font;
                pre.before(div);
                div.append(pre);
            }
        }
        for (const codeBlock of this.editable.querySelectorAll("div.o_syntax_highlighting")) {
            this.dependencies.protectedNode.setProtectingNode(codeBlock, true);
            const pre = codeBlock.querySelector("pre");
            const preStyle = getComputedStyle(pre);
            let textarea = codeBlock.querySelector("textarea.o_prism_source");
            if (!textarea) {
                textarea = this.document.createElement("textarea");
                textarea.classList.add("o_prism_source");
                textarea.setAttribute("contenteditable", "true");
                textarea.style.padding = preStyle.padding;
                textarea.style.margin = preStyle.margin;
                codeBlock.append(textarea);
                activeTextarea = activate && textarea; // It's the latest inserted one.
            }
            // Trailing br gives \n in innerText but should not be visible.
            const trailingBrs = pre.innerHTML.match(/(<br>)+$/)?.length || 0;
            const preInnerText = pre.innerText.slice(
                0,
                pre.innerText.length - (trailingBrs > 1 ? trailingBrs - 1 : trailingBrs)
            );
            if (textarea.value !== preInnerText) {
                textarea.value = preInnerText;
            }
            this.resetListeners(codeBlock);
        }
        if (activeTextarea) {
            if (activate) {
                this.setActiveCodeBlock(activeTextarea.parentElement);
                activeTextarea.focus();
            }
            setTimeout(
                () =>
                    activeTextarea.setSelectionRange(
                        textareaSelection.start,
                        textareaSelection.end,
                        textareaSelection.direction
                    ),
                10
            );
        }
    }

    removeListeners(codeBlock) {
        const textarea = codeBlock.querySelector("textarea");
        codeBlock.removeEventListener("input", this.boundOnCodeBlockInput);
        codeBlock.removeEventListener("keydown", this.boundOnCodeBlockKeydown);
        textarea.removeEventListener("scroll", this.boundOnTextareaScroll);
    }

    resetListeners(codeBlock) {
        this.boundOnCodeBlockInput ||= this.onCodeBlockInput.bind(this);
        this.boundOnCodeBlockKeydown ||= this.onCodeBlockKeydown.bind(this);
        this.boundOnTextareaScroll ||= this.onTextareaScroll.bind(this);

        this.removeListeners(codeBlock);
        const textarea = codeBlock.querySelector("textarea");
        codeBlock.addEventListener("input", this.boundOnCodeBlockInput);
        codeBlock.addEventListener("keydown", this.boundOnCodeBlockKeydown);
        textarea.addEventListener("scroll", this.boundOnTextareaScroll);
    }

    onCodeBlockInput(ev) {
        this.highlight(ev.currentTarget);
    }

    onCodeBlockKeydown(ev) {
        if (ev.key === "Tab") {
            ev.preventDefault();
            const textarea = ev.currentTarget.querySelector("textarea");
            const tabSize = +getComputedStyle(textarea).tabSize || 4;
            const tab = " ".repeat(tabSize);
            const { selectionStart, selectionEnd } = textarea;
            const collapsed = selectionStart === selectionEnd;
            let start = textarea.value.slice(0, selectionStart).lastIndexOf("\n");
            start = start === -1 ? 0 : start;
            let newValue = "";
            let spacesRemovedAtStart = 0;
            if (ev.shiftKey) {
                // Remove tabs.
                let end = textarea.value.slice(selectionEnd, textarea.value.length).indexOf("\n");
                end = end === -1 ? 0 : end;
                end = selectionEnd + end;
                // From 0 to the last \n before selection start.
                newValue = textarea.value.slice(0, start);
                // From the last \n before selection start to selection end.
                const regex = new RegExp(`(\n|^)( |\u00A0){1,${tabSize}}`, "g");
                newValue += textarea.value.slice(start, selectionEnd).replace(regex, "$1");
                spacesRemovedAtStart = selectionEnd - newValue.length;
                newValue += textarea.value.slice(selectionEnd, end).replace(regex, "$1");
                // From selection end to end.
                newValue += textarea.value.slice(end, textarea.value.length);
            } else {
                // Insert tabs.
                if (collapsed && /\S/.test(textarea.value.slice(start, selectionStart))) {
                    newValue =
                        textarea.value.slice(0, selectionStart) +
                        tab +
                        textarea.value.slice(selectionStart, textarea.value.length);
                } else {
                    // From 0 to the last \n before selection start.
                    newValue = start ? textarea.value.slice(0, start) : tab;
                    // From the last \n before selection start to selection end.
                    newValue += textarea.value
                        .slice(start, selectionEnd)
                        .replaceAll("\n", `\n${tab}`);
                    // From selection end to end.
                    newValue += textarea.value.slice(selectionEnd, textarea.value.length);
                }
            }
            const insertedChars = newValue.length - textarea.value.length;
            textarea.value = newValue;
            const newStart = selectionStart + (ev.shiftKey ? -spacesRemovedAtStart : tabSize);
            const newEnd = collapsed ? newStart : selectionEnd + insertedChars;
            textarea.setSelectionRange(newStart, newEnd, textarea.selectionDirection);
            this.highlight(ev.currentTarget);
        }
    }

    onTextareaScroll(ev) {
        const textarea = ev.currentTarget;
        const pre = textarea.parentElement.querySelector("pre");
        pre.scrollTop = textarea.scrollTop;
        pre.scrollLeft = textarea.scrollLeft;
    }

    onMouseMove(ev) {
        const codeBlock = ev.target.closest?.(".o_syntax_highlighting");
        const isLanguageSelectorOpen = !!this.document.querySelector(
            ".dropdown-menu.o_language_selector"
        );
        if (isLanguageSelectorOpen) {
            return;
        }
        if (codeBlock && codeBlock !== this.activeCodeBlock && this.editable.contains(codeBlock)) {
            this.setActiveCodeBlock(codeBlock);
        } else if (this.activeCodeBlock) {
            const isOverlay = !!ev.target.closest(".o-overlay-container");
            if (isOverlay) {
                return;
            }
            if (!codeBlock) {
                this.setActiveCodeBlock(null);
            }
        }
    }

    onLanguageChange(codeBlock, languageId) {
        if (codeBlock.dataset.languageId !== languageId) {
            codeBlock.dataset.languageId = languageId;
            this.highlight(codeBlock);
        }
    }

    async highlight(codeBlock, focus = true) {
        if (!window.Prism) {
            await this.loadPrism();
        }
        const pre = codeBlock.querySelector("pre");
        const textarea = codeBlock.querySelector("textarea.o_prism_source");
        const languageId = codeBlock.dataset.languageId || DEFAULT_LANGUAGE_ID;
        // Make sure the step is properly recorded to include the code block's
        // data attribute and the PRE's content.
        this.dependencies.protectedNode.setProtectingNode(codeBlock, false);
        // Highlight.
        pre.innerHTML = Prism.highlight(textarea.value, Prism.languages[languageId], languageId);
        // Post-process the inserted HTML:
        // 1. Replace \n with <br>.
        for (const node of descendants(pre).filter((node) => node.nodeType === Node.TEXT_NODE)) {
            let newline = node.textContent.indexOf("\n");
            while (newline !== -1) {
                node.before(this.document.createTextNode(node.textContent.slice(0, newline)));
                node.before(this.document.createElement("BR"));
                node.textContent = node.textContent.slice(newline + 1);
                newline = node.textContent.indexOf("\n");
            }
            if (!node.textContent) {
                node.remove(); // Prevent empty trailing text node that would become the last leaf.
            }
        }
        // 2. Handle trailing BRs. Eg, <span>ab\n</span> -> <span>ab</span><br><br>
        const trailingBr = lastLeaf(pre);
        if (trailingBr?.nodeName === "BR") {
            pre.append(trailingBr); // <span>ab<br></span> -> <span>ab</span><br>
            trailingBr.after(this.document.createElement("BR")); // <br></pre> -> <br><br></pre>
        }
        this.dependencies.history.addStep();
        // Will be done in normalize handler triggered by addStep:
        // this.dependencies.protectedNode.setProtectingNode(codeBlock, true);
        if (focus) {
            textarea.focus({ preventScroll: true });
        }
    }

    setActiveCodeBlock(codeBlock) {
        this.activeCodeBlock = codeBlock;
        this.codeToolbar.close();
        if (codeBlock) {
            this.codeToolbar.open({
                target: codeBlock,
                props: {
                    target: codeBlock,
                    prismSource: codeBlock.querySelector("textarea"),
                    languages: LANGUAGES,
                    onLanguageChange: this.onLanguageChange.bind(this),
                },
            });
        }
    }
}

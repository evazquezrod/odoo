import { beforeEach, expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { unformat } from "./_helpers/format";
import {
    animationFrame,
    click,
    manuallyDispatchProgrammaticEvent,
    press,
    queryOne,
    waitFor,
} from "@odoo/hoot-dom";
import { insertText } from "./_helpers/user_actions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { SyntaxHighlightingPlugin } from "@html_editor/main/syntax_highlighting_plugin";

const DEFAULT_LANGUAGE_ID = "plaintext";
const WITH_LANGUAGE_ID = (html, languageId = DEFAULT_LANGUAGE_ID) =>
    `<span id="${languageId}">${html}</span>`;
const getPreStyle = (editor) =>
    editor.document.defaultView.getComputedStyle(editor.editable.querySelector("pre"));
const SYNTAX_HIGHLIGHTING_WRAPPER = (
    content,
    preStyle,
    { language = DEFAULT_LANGUAGE_ID, highlit = true } = {}
) =>
    unformat(`
        <div class="o_syntax_highlighting" data-language-id="${language}"
            style='font: ${preStyle.font};' data-oe-protected="true" contenteditable="false">
            <pre>${highlit ? WITH_LANGUAGE_ID(content, language) : content}</pre>
            <textarea class="o_prism_source" contenteditable="true"
            style="padding: ${preStyle.padding}; margin: ${preStyle.margin};"></textarea>
            </div>
    `);

beforeEach(() => {
    patchWithCleanup(SyntaxHighlightingPlugin.prototype, {
        async loadPrism() {
            window.Prism = {
                highlight: (html, l, languageId = DEFAULT_LANGUAGE_ID) =>
                    WITH_LANGUAGE_ID(html, languageId),
                languages: {},
            };
        },
    });
});

test("starting edition with a code block activates syntax highlighting", async () => {
    const { editor, el } = await setupEditor(`<pre>some code[]</pre>`);
    const preStyle = getPreStyle(editor);
    await animationFrame();
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("some code", preStyle, {
            highlit: false,
        })
    );
});

test.tags("focus required");
test("inserting a code block activates syntax highlighting plugin, typing triggers highlight", async () => {
    const { editor, el } = await setupEditor("<p>[]abc</p>");
    await insertText(editor, "/code");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Code");
    await press("enter");
    const preStyle = getPreStyle(editor);
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER("abc", preStyle, { highlit: false }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    const textarea = editor.document.querySelector("textarea");
    expect(editor.document.activeElement).toBe(textarea, { message: "The textarea is focused." });
    expect(textarea.value).toBe("abc", {
        message: "The paragraph's content was transferred to the textarea.",
    });
    expect([textarea.selectionStart, textarea.selectionEnd]).toEqual([3, 3], {
        message: "The textarea selection is at the end of its content.",
    });
    await press("d");
    expect(textarea.value).toBe("abcd", { message: "Typing occurred in the textarea." });
    expect(getContent(el).replace("[]", "")).toBe(SYNTAX_HIGHLIGHTING_WRAPPER(`abcd`, preStyle), {
        message:
            "The change of value in the textarea is reflected in the pre, which is now highlited.",
    });
});

const changeLanguage = async (from, to) => {
    await click("textarea");
    // Code Toolbar should open.
    await waitFor(".o_code_toolbar");
    await click(`.o_code_toolbar button[name='language'][title='${from}']`);
    // Language selector dropdown should open.
    await waitFor(".o_language_selector");
    await click(`.o_language_selector .o-dropdown-item[name='${to}']`);
    // Code Toolbar should show the new language name.
    await waitFor(`.o_code_toolbar button[name='language'][title='${to}']`);
};

test("changing languages in a code block changes its highlighting", async () => {
    const { editor, el } = await setupEditor(`<pre>some code[]</pre>`);
    const preStyle = getPreStyle(editor);
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { highlit: false }),
        {
            message: "The syntax highlighting wrapper was inserted, without highlighting.",
        }
    );
    await changeLanguage("Plain Text", "Javascript");
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }),
        {
            message: "The code was highlighted in javascript.",
        }
    );
});
test("multiple ctrl+z in a highlighted code block undo changes in the block and any other changes before", async () => {
    const { editor, el } = await setupEditor(`<pre>some code</pre><p>hell[]</p>`);
    const preStyle = getPreStyle(editor);
    // Write in the P.
    await insertText(editor, "o!"); // <wrapper><pre>some code</pre></wrapper><p>hello![]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { highlit: false }) + "<p>hello![]</p>",
        { message: "should have inserted 'o!' into the paragraph" }
    );
    // Change the language -> code gets highlighted.
    await changeLanguage("Plain Text", "Javascript"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: "should have changed the language to javascript and highlighted the code" }
    );
    // Write in the TEXTAREA.
    await click("textarea");
    await press("n"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("o"); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: "should have inserted 'no' into the pre" }
    );
    await press("Backspace"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("Backspace"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await press("y"); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press("e"); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press("s"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: "should have replaced 'no' with 'yes' in the pre" }
    );
    // Write in the P again.
    await click("p");
    setSelection({ anchorNode: queryOne("p").firstChild, anchorOffset: 6 });
    await insertText(editor, "ok"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok[]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!ok[]</p>",
        { message: "should have inserted 'ok!' into the paragraph" }
    );
    // Undo everything.
    // We simulate undo with Ctrl+Z because we want to see how it
    // interacts with native browser behavior.
    const ctrlZ = async () => {
        const target = editor.document.activeElement;
        const keydown = await manuallyDispatchProgrammaticEvent(target, "keydown", {
            key: "z",
            ctrlKey: true,
        });
        if (keydown.defaultPrevented) {
            return;
        }
        editor.document.execCommand("undo", false, null);
        // The input events don't get triggered if the input has
        // nothing to undo.
        const beforeInput = await manuallyDispatchProgrammaticEvent(target, "beforeinput", {
            inputType: "historyUndo",
        });
        // --> Here the editor should do its own UNDO.
        if (beforeInput.defaultPrevented) {
            return;
        }
        const inputEvent = await manuallyDispatchProgrammaticEvent(target, "input", {
            inputType: "historyUndo",
        });
        if (inputEvent.defaultPrevented) {
            return;
        }
        await manuallyDispatchProgrammaticEvent(target, "keyup", {
            key: "z",
            ctrlKey: true,
        });
    };
    await ctrlZ(); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello![]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello![]</p>",
        { message: "should have removed 'ok!' from the paragraph" }
    );
    await ctrlZ(); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await ctrlZ(); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await ctrlZ(); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: "should have removed 's', then 'e', then 'y' from the pre" }
    );
    await ctrlZ(); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await ctrlZ(); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: "should have re-inserted 'n', then 'o' into the pre" }
    );
    await ctrlZ(); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await ctrlZ(); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: "should have remove 'o', then 'n' from the pre" }
    );
    await ctrlZ(); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "plaintext" }) +
            "<p>hello!</p>",
        { message: "should have removed the language" }
    );
    await ctrlZ(); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "plaintext" }) +
            "<p>hell[]</p>",
        { message: "should have removed the text inserted in the paragraph" }
    );
});
test("tab in code block inserts 4 spaces", async () => {});
test("tab in selection in code block indents each selected line", async () => {});
test("shift+tab in selection in code block outdents each selected line", async () => {});

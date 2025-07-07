import { beforeEach, expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { unformat } from "./_helpers/format";
import { animationFrame, click, press, queryOne, waitFor } from "@odoo/hoot-dom";
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
            <pre data-oe-protected="false" contenteditable="true">${
                highlit ? WITH_LANGUAGE_ID(content, language) : content
            }</pre>
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
test("multiple ctrl+z in a highlighted code block undo changes in the block and any other changes before (all redone with ctrl+y or ctrl+shift+z)", async () => {
    const { editor, el } = await setupEditor(`<pre>some code</pre><p>hell[]</p>`);

    const testSelectionInTextarea = (textarea, value, start, end = start) => {
        const { anchorNode, anchorOffset, focusNode, focusOffset } = editor.document.getSelection();
        expect({
            activeElement: editor.document.activeElement,
            anchorTarget: anchorNode.childNodes[anchorOffset],
            focusTarget: focusNode.childNodes[focusOffset],
            textareaValue: textarea.value,
            textareaSelection: [textarea.selectionStart, textarea.selectionEnd],
        }).toEqual(
            {
                activeElement: textarea,
                anchorTarget: textarea,
                focusTarget: textarea,
                textareaValue: value,
                textareaSelection: [start, end],
            },
            { message: "Selection should be correct in the textarea." }
        );
    };
    const preStyle = getPreStyle(editor);

    // Perform a series of actions to undo later.
    // ------------------------------------------

    const actions = [];
    const listActions = (...actionNumbers) =>
        actionNumbers
            .map((actionNumber) => `${actionNumber}. ${actions[actionNumber - 1]}`)
            .join("\n");

    // Perform a series of actions to undo later.
    // ------------------------------------------

    // Write in the P.
    actions.push("type: insert 'o' into the paragraph", "type: insert '!' into the paragraph");
    await insertText(editor, "o!"); // <wrapper><pre>some code</pre></wrapper><p>hello![]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { highlit: false }) + "<p>hello![]</p>",
        { message: listActions(1, 2) }
    );
    // Change the language -> code gets highlighted.
    actions.push("language: change the language to javascript and highlight the code");
    await changeLanguage("Plain Text", "Javascript"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: listActions(3) }
    );
    const textarea = queryOne("textarea");
    testSelectionInTextarea(textarea, "some code", textarea.value.length);
    // Write in the TEXTAREA.
    actions.push("type: insert 'n' into the pre", "type: insert 'o' into the pre");
    await click("textarea");
    await press("n"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("o"); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: listActions(4, 5) }
    );
    actions.push(
        "type: remove 'o' from the pre",
        "type: remove 'n' from the pre",
        "type: insert 'y' into the pre",
        "type: insert 'e' into the pre",
        "type: insert 's' into the pre"
    );
    await press("Backspace"); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press("Backspace"); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    await press("y"); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press("e"); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press("s"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        {
            message: listActions(6, 7, 8, 9, 10),
        }
    );
    testSelectionInTextarea(textarea, "some codeyes", textarea.value.length);
    // Write in the P again.
    actions.push("type: insert 'o' into the paragraph", "type: insert 'k' into the paragraph");
    await click("p");
    setSelection({ anchorNode: queryOne("p").firstChild, anchorOffset: 6 });
    await insertText(editor, "ok"); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok[]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!ok[]</p>",
        {
            message: listActions(11, 12),
        }
    );
    // Write in the TEXTAREA again.
    actions.push("type: insert 'h' into the pre");
    await click("textarea");
    await press("h"); // <wrapper><highlight><pre>some codeyesh</pre></highlight></wrapper><p>hello!ok[]</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyesh`, preStyle, { language: "javascript" }) +
            "<p>hello!ok</p>",
        { message: listActions(13) }
    );
    testSelectionInTextarea(textarea, "some codeyesh", textarea.value.length);

    // Undo everything.
    // ----------------

    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!ok</p>",
        {
            message: `undo:\n${listActions(13)}`,
        }
    );
    testSelectionInTextarea(textarea, "some codeyes", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o[]</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello![]</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello![]</p>",
        {
            message: `undo:\n${listActions(12, 11)}`,
        }
    );
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        {
            message: `undo:\n${listActions(10, 9, 8)}`,
        }
    );
    testSelectionInTextarea(textarea, "some code", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        {
            message: `undo:\n${listActions(7, 6)}`,
        }
    );
    testSelectionInTextarea(textarea, "some codeno", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        {
            message: `undo:\n${listActions(5, 4)}`,
        }
    );
    testSelectionInTextarea(textarea, "some code", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, {
            language: "plaintext",
            highlit: false,
        }) + "<p>hello!</p>",
        {
            message: `undo:\n${listActions(3)}`,
        }
    );
    testSelectionInTextarea(textarea, "some code", textarea.value.length);
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, {
            language: "plaintext",
            highlit: false,
        }) + "<p>hell[]</p>",
        {
            message: `undo:\n${listActions(2, 1)}`,
        }
    );
    await press(["ctrl", "z"]); // <wrapper><pre>some code</pre></wrapper><p>hell</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, {
            language: "plaintext",
            highlit: false,
        }) + "<p>hell[]</p>",
        {
            message: `undo: should have done nothing`,
        }
    );

    // Redo everything.
    // ----------------

    await press(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello</p>
    await press(["ctrl", "y"]); // <wrapper><pre>some code</pre></wrapper><p>hello!</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, {
            language: "plaintext",
            highlit: false,
        }) + "<p>hello![]</p>",
        {
            message: `redo:\n${listActions(1, 2)}`,
        }
    );
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: `redo:\n${listActions(3)}` }
    );
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeno</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeno`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: `redo:\n${listActions(4, 5)}` }
    );
    testSelectionInTextarea(textarea, "some codeno", textarea.value.length);
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some coden</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some code</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some code`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: `redo:\n${listActions(6, 7)}` }
    );
    testSelectionInTextarea(textarea, "some code", textarea.value.length);
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codey</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeye</pre></highlight></wrapper><p>hello!</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!</p>",
        { message: `redo:\n${listActions(8, 9, 10)}` }
    );
    testSelectionInTextarea(textarea, "some codeyes", textarea.value.length);
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!o</p>
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el)).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyes`, preStyle, { language: "javascript" }) +
            "<p>hello!ok[]</p>",
        { message: `redo:\n${listActions(11, 12)}` }
    );
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyesh`, preStyle, { language: "javascript" }) +
            "<p>hello!ok</p>",
        {
            message: `redo:\n${listActions(13)}`,
        }
    );
    testSelectionInTextarea(textarea, "some codeyesh", textarea.value.length);
    await press(["ctrl", "shift", "z"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    await press(["ctrl", "y"]); // <wrapper><highlight><pre>some codeyes</pre></highlight></wrapper><p>hello!ok</p>
    expect(getContent(el).replace("[]", "")).toBe(
        SYNTAX_HIGHLIGHTING_WRAPPER(`some codeyesh`, preStyle, { language: "javascript" }) +
            "<p>hello!ok</p>",
        {
            message: `redo: should have done nothing`,
        }
    );
    testSelectionInTextarea(textarea, "some codeyesh", textarea.value.length);
});
test("tab in code block inserts 4 spaces", async () => {});
test("tab in selection in code block indents each selected line", async () => {});
test("shift+tab in selection in code block outdents each selected line", async () => {});
test("can switch between code blocks without issues", async () => {});

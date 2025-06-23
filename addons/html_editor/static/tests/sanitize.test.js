import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";
import { markup } from "@odoo/owl";
import { expectMarkup } from "@web/../tests/web_test_helpers";

const Markup = markup().constructor;

test("sanitize should remove nasty elements", async () => {
    const { editor } = await setupEditor("");
    expect(editor.shared.sanitize.sanitize("<img src=x onerror=alert(1)//>")).toBe('<img src="x">');
    expect(editor.shared.sanitize.sanitize("<svg><g/onload=alert(2)//<p>")).toBe(
        "<svg><g></g></svg>"
    );
    expect(
        editor.shared.sanitize.sanitize("<p>abc<iframe//src=jAva&Tab;script:alert(3)>def</p>")
    ).toBe("<p>abc</p>");
});

test("sanitize plugin should handle contenteditable attribute with o-contenteditable-[true/false] class", async () => {
    await testEditor({
        contentBefore: `<p class="o-contenteditable-true">a[]</p><p class="o-contenteditable-false">b</p>`,
        contentAfterEdit: `<p class="o-contenteditable-true" contenteditable="true">a[]</p><p class="o-contenteditable-false" contenteditable="false">b</p>`,
        contentAfter: `<p class="o-contenteditable-true">a[]</p><p class="o-contenteditable-false">b</p>`,
    });
});

test("sanitize plugin should handle role attribute with data-oe-role attribute", async () => {
    await testEditor({
        contentBefore: `<p data-oe-role="status">a[]</p>`,
        contentAfterEdit: `<p data-oe-role="status" role="status">a[]</p>`,
        contentAfter: `<p data-oe-role="status">a[]</p>`,
    });
});

test("sanitize plugin should handle aria-label attribute with data-oe-aria-label attribute", async () => {
    await testEditor({
        contentBefore: `<p data-oe-aria-label="status">a[]</p>`,
        contentAfterEdit: `<p data-oe-aria-label="status" aria-label="status">a[]</p>`,
        contentAfter: `<p data-oe-aria-label="status">a[]</p>`,
    });
});

test("fixInvalidHTML should close self-closing elements", () => {
    expectMarkup(fixInvalidHTML(markup("<t/>"))).toBe("<t></t>");
    expectMarkup(fixInvalidHTML(markup('<t class="test"/>'))).toBe('<t class="test"></t>');
    expectMarkup(fixInvalidHTML(markup("<a/>"))).toBe("<a></a>");
    expectMarkup(fixInvalidHTML(markup('<a href="#"/>'))).toBe('<a href="#"></a>');
    expectMarkup(fixInvalidHTML(markup("<strong/>"))).toBe("<strong></strong>");
    expectMarkup(fixInvalidHTML(markup('<strong class="bold"/>'))).toBe(
        '<strong class="bold"></strong>'
    );
    expectMarkup(fixInvalidHTML(markup("<span/>"))).toBe("<span></span>");
    expectMarkup(fixInvalidHTML(markup('<span id="test"/>'))).toBe('<span id="test"></span>');
    expectMarkup(
        fixInvalidHTML(markup('<t t-out="object.name"/>asdf<t t-out="object.parner_id.name"/>'))
    ).toBe('<t t-out="object.name"></t>asdf<t t-out="object.parner_id.name"></t>');
});

test("fixInvalidHTML escapes string input", () => {
    expectMarkup(fixInvalidHTML("<t/>")).toBe("&lt;t/&gt;");
});

test("fixInvalidHTML returns markup", () => {
    const markupInput = markup("<t/>");
    const strInput = "<t/>";
    expect(fixInvalidHTML(markupInput)).toBeInstanceOf(Markup);
    expect(fixInvalidHTML(strInput)).toBeInstanceOf(Markup);
});

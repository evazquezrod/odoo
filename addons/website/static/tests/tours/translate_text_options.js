import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    selectElementInWeSelectWidget,
    selectFullText,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "translate_text_options",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        selectFullText("first text block in the snippet", "#wrap .s_text_block p"),
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o-we-toolbar button[name="expand_toolbar"]',
            run: "click",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o-we-toolbar div[name="websiteDecoration"] button:nth-of-type(2)',
            run: "click",
        },
        selectFullText("second text block in the snippet", "#wrap .s_text_block p:last"),
        {
            content: "Click on the 'Highlight Effects' button to activate the option",
            trigger: '.o-overlay-item .o-we-toolbar button[name="expand_toolbar"]',
            run: "click",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o-we-toolbar div[name="websiteDecoration"] button:nth-of-type(1)',
            run: "click",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o_popover .o_text_highlight_underline',
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Change the language to French",
            trigger: ':iframe .js_language_selector .js_change_lang[data-url_code="fr"]',
            run: "click",
        },
        {
            content: "Click edit button",
            trigger: ".o_menu_systray button:contains('Edit').dropdown-toggle",
            run: "click",
        },
        {
            content: "Enable translation",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",

        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        // // Select the highlighted text content.
        selectFullText("snippet highlighted text content", "#wrap .s_text_block p:last .o_text_highlight"),
        {
            content: "Click on the 'Highlight Effects' button to activate the option",
            trigger: '.o-overlay-item .o-we-toolbar button[name="expand_toolbar"]',
            run: "click",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o-we-toolbar div[name="websiteDecoration"] button:nth-of-type(1)',
            run: "click",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o_popover button#highlightPicker',
            run: "click",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: '.o-overlay-item .o_popover .o_text_highlight_jagged',
            run: "click",
        },
        // // Select a text content without any option.
        selectFullText("text content without any option", "footer .s_text_block p:first span"),
        // {
        //     content: "Check that all text options are removed",
        //     trigger:
        //         "#toolbar:not(:has(.snippet-option-TextHighlight, .snippet-option-WebsiteAnimate))",
        // },
        // // Select the highlighted text content again.
        // selectFullText("highlighted text content again", "#wrap .s_text_block p:last .o_text_highlight"),
        // {
        //     content: "Check that only the highlight options are displayed",
        //     trigger:
        //         "#toolbar:not(:has(.snippet-option-WebsiteAnimate)) .snippet-option-TextHighlight",
        // },
        // ...clickOnSave(),
        // {
        //     content: "Check that the highlight effect was correctly translated",
        //     trigger:
        //         ":iframe .s_text_block .o_text_highlight:has(.o_text_highlight_item:has(.o_text_highlight_path_jagged))",
        // },
    ]
);

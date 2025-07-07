import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSave,
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
} from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registerWebsitePreviewTour('snippet_popup_specific_pages', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        name: "Popup",
        id: "s_popup",
        groupName: "Content",
    }),
    {
        content: "Click on the Popup snippet to edit it.",
        trigger: ":iframe #wrap.o_editable [data-snippet='s_popup']:not(:visible)",
        run: "click",
    },
    ...changeOptionInPopover("Popup", "Show on", "These specific pages"),
    {
        content: "Enter '/' in dropdown.",
        trigger: '.we-bg-options-container [data-label=" "] input:not(:disabled)',
        run: "edit /",
    },
    {
        content: "Select '/' it from dropdown.",
        trigger: '.o_website_ui_autocomplete > li:nth-child(1) a',
        run: "click",
    },
    {
        content: "Enter '/contactus' in dropdown.",
        trigger: '.we-bg-options-container [data-label=" "] input:not(:disabled)',
        run: "edit /contactus",
    },
    {
        content: "Verify autocomplete popover is displayed.",
        trigger: '.o_website_ui_autocomplete',
    },
    {
        content: "Select '/contactus' it from dropdown.",
        trigger: '.o_website_ui_autocomplete > li:nth-child(1) a',
        run: "click",
    },
    ...clickOnSave(),
    {
        content: "Go to Home page",
        trigger: ':iframe .nav-item a:contains("Home")',
        run: "click",
    },
    {
        content: "Verify that we are on Home page",
        trigger: ':iframe .nav-item a.active:contains("Home")',
        run: "click",
    },
    {
        content: "Check popup exists on home page.",
        trigger: ':iframe .s_popup:not(:visible)',
    },
    {
        content: "Go to contactus page",
        trigger: ':iframe .nav-item a:contains("Contact us")',
        run: "click",
    },
    {
        content: "Check popup exists on Contact Us page.",
        trigger: ':iframe .s_popup:not(:visible)',
    },
    {
        content: "Go to Home page",
        trigger: ':iframe .nav-item > a:contains("Home")',
        run: "click",
    },
    stepUtils.waitIframeIsReady(),
    ...clickOnEditAndWaitEditMode(),
    {
        content: 'Toggle the visibility of the Popup',
        trigger: '.o_we_invisible_el_panel .o_we_invisible_entry:contains("Popup")',
        run: "click",
    },
    {
        content: "Remove Home page ('/') from the selection.",
        trigger: '.we-bg-options-container button.fa-minus:nth-child(1)',
        run: "click",
    },
    ...clickOnSave(),
    {
        content: "Go to Home page",
        trigger: ':iframe .nav-item a:contains("Home")',
        run: "click",
    },
    {
        content: "Check popup does not exist on home page.",
        trigger: ':iframe .s_popup:not(:visible)',
    },
    {
        content: "Go to Contact us page",
        trigger: ':iframe .nav-item a:contains("Contact us")',
        run: "click",
    },
    {
        content: "Check popup exists on Contact us page.",
        trigger: ':iframe .s_popup:not(:visible)',
    },
]);

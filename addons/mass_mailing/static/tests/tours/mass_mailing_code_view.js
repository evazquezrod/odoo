import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { simpleTags } from "@web/core/utils/html";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('mass_mailing_code_view_tour', {
    url: '/odoo?debug=tests',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
            run: "click",
        }, {
            trigger: 'button.o_list_button_add',
            run: "click",
        }, {
            trigger: 'input#subject_0',
            content: _t('Pick the %(b_open)semail subject%(b_close)s.', simpleTags),
            tooltipPosition: 'bottom',
            run: "edit Test",
        }, {
            trigger: 'div[name="contact_list_ids"] .o_input_dropdown input[type="text"]',
            content: 'Click on the dropdown to open it and then start typing to search.',
            run: "edit Test"
        }, {
            trigger: 'div[name="contact_list_ids"] .ui-state-active',
            content: 'Select item from dropdown',
            run: 'click',
        }, {
            trigger: 'div[name="body_arch"] :iframe #default',
            content: _t('Choose this %(b_open)stheme%(b_close)s.', simpleTags),
            run: 'click',
        }, {
            trigger: '.o_codeview_btn',
            content: _t('Click here to switch to %(b_open)scode view%(b_close)s', simpleTags),
            run: 'click'
        }, {
            trigger: ':iframe .o_codeview',
            content: ('Remove all content from codeview'),
            run: function () {
                const iframe = document.querySelector('.wysiwyg_iframe');
                const iframeDocument = iframe.contentWindow.document;
                let element = iframeDocument.querySelector(".o_codeview");
                element.value = '';
            }
        }, {
            trigger: '.o_codeview_btn',
            content: _t('Click here to switch back from %(b_open)scode view%(b_close)s', simpleTags),
            run: 'click'
        }, {
            trigger: '[name="body_arch"] :iframe .o_mail_wrapper_td',
            content: 'Verify that the dropable zone was not removed',
        }, {
            trigger: '[name="body_arch"] #email_designer_body_elements [name="Title"] .oe_snippet_thumbnail',
            content: 'Drag the "Title" snippet from the design panel and drop it in the editor',
            async run(helpers) {
                helpers.drag_and_drop(`[name="body_arch"] :iframe .o_editable`, {
                    position: {
                        top: 340,
                    }
                });
            }
        }, {
            trigger: '[name="body_arch"] :iframe .o_editable h1',
            content: 'Verify that the title was inserted properly in the editor',
        },
        ...stepUtils.discardForm(),
    ]
});

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { simpleTags } from "@web/core/utils/html";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('hr_recruitment_tour',{
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
    content: _t("Let's have a look at how to %(b_open)simprove%(b_close)s your %(b_open)shiring process%(b_close)s.", simpleTags),
    tooltipPosition: 'right',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
    content: _t("Let's have a look at how to %(b_open)simprove%(b_close)s your %(b_open)shiring process%(b_close)s.", simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o-kanban-button-new",
    content: _t("Create your first Job Position."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_hr_job_simple_form",
},
{
    trigger: ".o_job_name",
    content: _t("What do you want to recruit today? Choose a job title..."),
    tooltipPosition: "right",
    run: "click",
},
{
    trigger: '.o_hr_job_simple_form',
},
{
    trigger: ".o_job_alias",
    content: _t("Choose an application email."),
    tooltipPosition: "right",
    run: "click",
}, {
    trigger: '.o_create_job',
    content: _t('Let\'s create the position. An email will be setup for applications, and a public job description, if you use the Website app.'),
    tooltipPosition: 'bottom',
    run: "click .modal:visible .btn.btn-primary",
}, {
    trigger: ".o_copy_paste_email",
    content: _t("Copy this email address, to paste it in your email composer, to apply."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_kanban_applicant",
},
{
    trigger: ".breadcrumb-item:not(.active):last",
    content: _t("Let’s go back to the dashboard."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_hr_recruitment_kanban",
},
{
    trigger: "button.oe_kanban_action",
    content: _t("%(b_open)sDid you apply by sending an email?%(b_close)s Check incoming applications.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_kanban_applicant",
},
{
    trigger: ".o_kanban_record",
    content: _t("%(b_open)sDrag this card%(b_close)s, to qualify him for a first interview.", simpleTags),
    tooltipPosition: "bottom",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
},
{
    trigger: ".o_kanban_applicant",
},
{
    trigger: ".o_kanban_record",
    content: _t("%(b_open)sClick to view%(b_close)s the application.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_applicant_form",
},
{
    trigger: "button:contains(Send message)",
    content: _t("%(div_open)s%(b_open)sTry to send an email%(b_close)s to the applicant.%(div_close)s%(div_open)s%(i_open)sTips: All emails sent or received are saved in the history here%(i_close)s%(div_close)s", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_applicant_form",
},
{
    trigger: ".o-mail-Chatter .o-mail-Composer button[aria-label='Send']",
    content: _t("Send your email. Followers will get a copy of the communication."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_applicant_form",
},
{
    trigger: "button:contains(Log note)",
    content: _t("Or talk about this applicant privately with your colleagues."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_applicant_form",
},
{
    trigger: ".o_create_employee",
    content: _t("Let’s create this new employee now."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_hr_employee_form_view",
},
{
    trigger: ".o_form_button_save",
    content: _t("Save it!"),
    tooltipPosition: "bottom",
    run: "click",
}]});

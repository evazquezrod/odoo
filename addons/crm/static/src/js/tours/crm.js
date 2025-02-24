import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { simpleTags } from "@web/core/utils/html";
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('crm_tour', {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Ready to boost your sales? Let\'s have a look at your %(b_open)sPipeline%(b_close)s.', simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Ready to boost your sales? Let\'s have a look at your %(b_open)sPipeline%(b_close)s.', simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_opportunity_kanban",
},
{
    trigger: '.o_opportunity_kanban .o-kanban-button-new',
    content: _t("%(b_open)sCreate your first opportunity.%(b_close)s", simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id'] input",
    content: _t('%(b_open)sWrite a few letters%(b_close)s to look for a company, or create a new one.', simpleTags),
    tooltipPosition: "top",
    run: "edit Brandon Freeman",
}, {
    isActive: ["auto"],
    trigger: ".ui-menu-item > a",
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: _t("Now, %(b_open)sadd your Opportunity%(b_close)s to your Pipeline.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_opportunity_kanban",
},
{
    trigger: ".o_opportunity_kanban .o_kanban_group:first-child .o_kanban_record:last-of-type",
    content: _t("%(b_open)sDrag &amp; drop opportunities%(b_close)s between columns as you progress in your sales cycle.", simpleTags),
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(2))",
},
{
    trigger: ".o_opportunity_kanban",
},
{
    // Choose the element that is not going to be moved by the previous step.
    trigger: ".o_opportunity_kanban .o_kanban_group .o_kanban_record .o-mail-ActivityButton",
    content: _t("Looks like nothing is planned. :(%(br)s%(br)s%(i_open)sTip: Schedule activities to keep track of everything you have to do!%(i_close)s", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_opportunity_kanban",
},
{
    trigger: ".o-mail-ActivityListPopover button:contains(Schedule an activity)",
    content: _t("Let's %(b_open)sSchedule an Activity.%(b_close)s", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: '.modal-footer button[name="action_schedule_activities"]',
    content: _t("All set. Let’s %(b_open)sSchedule%(b_close)s it.", simpleTags),
    tooltipPosition: "top",  // dot NOT move to bottom, it would cause a resize flicker, see task-2476595
    run: "click",
}, {
    id: "drag_opportunity_to_won_step",
    trigger: ".o_opportunity_kanban .o_kanban_record:last-of-type",
    content: _t("Drag your opportunity to %(b_open)sWon%(b_close)s when you get the deal. Congrats!", simpleTags),
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(3))",
},
{
    trigger: ".o_opportunity_kanban",
},
{
    trigger: ".o_kanban_record",
    content: _t("Let’s have a look at an Opportunity."),
    tooltipPosition: "right",
    run: "click",
}, {
    trigger: ".o_lead_opportunity_form .o_statusbar_status",
    content: _t("You can make your opportunity advance through your pipeline from here."),
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".breadcrumb-item:not(.active):first",
    content: _t("Click on the breadcrumb to go back to your Pipeline. Odoo will save all modifications as you navigate."),
    tooltipPosition: "bottom",
    run: "click .breadcrumb-item:not(.active):last",
}]});

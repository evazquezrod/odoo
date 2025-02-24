import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { simpleTags } from "@web/core/utils/html";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import EventAdditionalTourSteps from "@event/js/tours/event_steps";


registry.category("web_tour.tours").add('event_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="event.event_main_menu"]',
    content: _t("Ready to %(b_open)sorganize events%(b_close)s in a few minutes? Let's get started!", simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="event.event_main_menu"]',
    content: _t("Ready to %(b_open)sorganize events%(b_close)s in a few minutes? Let's get started!", simpleTags),
    run: "click",
},
{
    trigger: ".o_event_kanban_view",
},
{
    trigger: '.o-kanban-button-new',
    content: _t("Let's create your first %(b_open)sevent%(b_close)s.", simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.o_event_form_view div[name="name"] textarea',
    content: _t("This is the %(b_open)sname%(b_close)s your guests will see when registering.", simpleTags),
    run: "edit Odoo Experience 2020",
}, {
    trigger: '.o_event_form_view div[name="date_begin"]',
    run: function () {
        const el1 = this.anchor.querySelector('input[data-field="date_begin"]');
        el1.value = '09/30/2020 08:00:00';
        el1.dispatchEvent(new Event("change"));
        const el2 = this.anchor.querySelector('input[data-field="date_end"]');
        el2.value = '10/02/2020 23:00:00';
        el2.dispatchEvent(new Event("change"));
    },
}, {
    trigger: '.o_event_form_view input[data-field="date_begin"]',
    content: _t("Open date range picker.%(br)sPick a Start and End date for your event.", simpleTags),
    run: "click",
}, {
    content: _t("Apply change."),
    trigger: '.o_datetime_picker .o_datetime_buttons .o_apply',
    run: "click",
}, {
    trigger: '.o_event_form_view div[name="event_ticket_ids"] .o_field_x2many_list_row_add a',
    content: _t("Ticket types allow you to distinguish your attendees. Let's %(b_open)screate%(b_close)s a new one.", simpleTags),
    run: "click",
}, stepUtils.autoExpandMoreButtons(),
...new EventAdditionalTourSteps()._get_website_event_steps(), {
    trigger: '.o_event_form_view div[name="stage_id"]',
    content: _t("Now that your event is ready, click here to move it to another stage."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: `.o_event_form_view div[name="stage_id"]`,
},
{
    trigger: 'ol.breadcrumb li.breadcrumb-item:first',
    content: _t("Use the %(b_open)sbreadcrumbs%(b_close)s to go back to your kanban overview.", simpleTags),
    tooltipPosition: 'bottom',
    run: 'click',
}].filter(Boolean)});

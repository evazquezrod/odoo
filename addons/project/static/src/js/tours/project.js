import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { simpleTags } from "@web/core/utils/html";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('project_tour', {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: _t('Want a better way to %(b_open)smanage your projects%(b_close)s? %(i_open)sIt starts here.%(i_close)s', simpleTags),
    tooltipPosition: 'right',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: _t('Want a better way to %(b_open)smanage your projects%(b_close)s? %(i_open)sIt starts here.%(i_close)s', simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_project_kanban",
},
{
    trigger: '.o-kanban-button-new',
    content: _t('Let\'s create your first %(b_open)sproject%(b_close)s.', simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.o_project_name input',
    content: _t('Choose a %(b_open)sname%(b_close)s for your project. %(i_open)sIt can be anything you want: the name of a customer, of a product, of a team, of a construction site, etc.%(i_close)s', simpleTags),
    tooltipPosition: 'right',
    run: "edit Test",
}, {
    trigger: '.o_open_tasks',
    content: _t('Let\'s create your first %(b_open)sproject%(b_close)s.', simpleTags),
    tooltipPosition: 'top',
    run: "click .modal:visible .btn.btn-primary",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: _t("Add columns to organize your tasks into %(b_open)sstages%(b_close)s %(i_open)se.g. New - In Progress - Done%(i_close)s.", simpleTags),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: _t('Let\'s create your first %(b_open)sstage%(b_close)s.', simpleTags),
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: ".o_kanban_group",
},
{
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: _t("Add columns to organize your tasks into %(b_open)sstages%(b_close)s %(i_open)se.g. New - In Progress - Done%(i_close)s.", simpleTags),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: _t('Let\'s create your second %(b_open)sstage%(b_close)s.', simpleTags),
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: ".o_kanban_group:eq(1)",
},
{
    trigger: '.o-kanban-button-new',
    content: _t("Let's create your first %(b_open)stask%(b_close)s.", simpleTags),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    content: _t('Choose a task %(b_open)sname%(b_close)s %(i_open)s(e.g. Website Design, Purchase Goods...)%(i_close)s', simpleTags),
    tooltipPosition: 'right',
    run: "edit Test",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create .o_kanban_add',
    content: _t("Add your task once it is ready."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: ".o_kanban_record",
    content: _t("%(b_open)sDrag &amp; drop%(b_close)s the card to change your task from stage.", simpleTags),
    tooltipPosition: "bottom",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: ".o_kanban_record:first",
    content: _t("Let's start working on your task."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    content: _t("Use the chatter to %(b_open)ssend emails%(b_close)s and communicate efficiently with your customers. Add new people to the followers' list to make them aware of the main changes about this task.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: "button.o-mail-Chatter-logNote",
    content: _t("%(b_open)sLog notes%(b_close)s for internal communications %(i_open)s(the people following this task won't be notified of the note you are logging unless you specifically tag them)%(i_close)s. Use @ %(b_open)smentions%(b_close)s to ping a colleague or # %(b_open)smentions%(b_close)s to reach an entire team.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-activity",
    content: _t("Create %(b_open)sactivities%(b_close)s to set yourself to-dos or to schedule meetings.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".modal-dialog .btn-primary",
    content: _t("Schedule your activity once it is ready."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    isActive: ["auto"],
    trigger: ".o_field_widget[name='user_ids'] input",
    content: _t("Assign a responsible to your task"),
    tooltipPosition: "right",
    run: "edit Admin",
},
{
    isActive: ["manual"],
    trigger: ".o_field_widget[name='user_ids']",
    content: _t("Assign a responsible to your task"),
    tooltipPosition: "right",
    run: "click",
},
{
    isActive: ["desktop", "auto"],
    trigger: "a.dropdown-item[id*='user_ids'] span",
    content: _t("Select an assignee from the menu"),
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: "div.o_kanban_renderer > article.o_kanban_record",
    run: "click",
}, {
    isActive: ["auto"],
    trigger: 'a[name="sub_tasks_page"]',
    content: _t('Open sub-tasks notebook section'),
    run: 'click',
}, {
    isActive: ["auto"],
    trigger: '.o_field_subtasks_one2many .o_list_renderer a[role="button"]',
    content: _t('Add a sub-task'),
    run: 'click',
}, {
    isActive: ["auto"],
    trigger: '.o_field_subtasks_one2many div[name="name"] input',
    content: _t('Give the sub-task a %(b_open)sname%(b_close)s', simpleTags),
    run: "edit New Sub-task",
},
{
    trigger: ".o_form_project_tasks .o_form_dirty",
},
{
    isActive: ["auto"],
    trigger: ".o_form_button_save",
    content: _t("You have unsaved changes - no worries! Odoo will automatically save it as you navigate.%(br)s You can discard these changes from here or manually save your task.%(br)sLet's save it manually.", simpleTags),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o_breadcrumb .o_back_button",
    content: _t("Let's go back to the %(b_open)skanban view%(b_close)s to have an overview of your next tasks.", simpleTags),
    tooltipPosition: "right",
    run: 'click',
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_counter .subtask_list_button",
    content: _t("You can open sub-tasks from the kanban card!"),
    run: "click",
},
{
    trigger: ".o_widget_subtask_kanban_list .subtask_list",
},
{
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create",
    content: _t("Create a new sub-task"),
    run: "click",
},
{
    trigger: ".subtask_create_input",
},
{
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create_input input",
    content: _t("Give the sub-task a %(b_open)sname%(b_close)s", simpleTags),
    run: "edit Newer Sub-task && click body",
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_list_row:contains(newer sub-task) .o_field_project_task_state_selection button",
    content: _t("You can change the sub-task state here!"),
    run: "click",
},
{
    trigger: ".project_task_state_selection_menu.dropdown-menu",
},
{
    isActive: ["auto"],
    trigger: ".project_task_state_selection_menu.dropdown-menu span.text-danger",
    content: _t("Mark the task as %(b_open)sCancelled%(b_close)s", simpleTags),
    run: "click",
}, {
    trigger: ".o-overlay-container:not(:visible):not(:has(.project_task_state_selection_menu))",
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_counter .subtask_list_button:contains('1/2')",
    content: _t("Close the sub-tasks list"),
    run: "click",
}, {
    isActive: ["auto"],
    trigger: '.o_kanban_renderer',
    // last step to confirm we've come back before considering the tour successful
    run: "click",
}]});

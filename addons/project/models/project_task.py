# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from pytz import UTC
from collections import defaultdict
from datetime import timedelta, datetime, time

from odoo import api, Command, fields, models, tools, SUPERUSER_ID, _
from odoo.addons.rating.models import rating_data
from odoo.addons.web_editor.tools import handle_history_divergence
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import format_list, SQL, LazyTranslate
from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.addons.project.controllers.project_sharing_chatter import ProjectSharingChatter
from odoo.addons.mail.tools.discuss import Store

_lt = LazyTranslate(__name__)

PROJECT_TASK_READABLE_FIELDS = {
    'id',
    'active',
    'priority',
    'project_id',
    'display_in_project',
    'allow_task_dependencies',
    'subtask_count',
    'email_from',
    'create_date',
    'write_date',
    'company_id',
    'displayed_image_id',
    'display_name',
    'portal_user_names',
    'user_ids',
    'display_parent_task_button',
    'current_user_same_company_partner',
    'allow_milestones',
    'milestone_id',
    'has_late_and_unreached_milestone',
    'date_assign',
    'dependent_ids',
    'message_is_follower',
    'recurring_task',
    'closed_subtask_count',
    'dependent_tasks_count',
    'depend_on_ids',
    'depend_on_count',
    'repeat_interval',
    'repeat_unit',
    'repeat_type',
    'repeat_until',
    'recurrence_id',
    'recurring_count',
    'duration_tracking',
    'display_follow_button',
    'is_template',
    'has_template_ancestor',
}

PROJECT_TASK_WRITABLE_FIELDS = {
    'name',
    'description',
    'partner_id',
    'date_deadline',
    'date_last_stage_update',
    'tag_ids',
    'sequence',
    'stage_id',
    'child_ids',
    'color',
    'parent_id',
    'priority',
    'state',
    'is_closed',
}


class ProjectTask(models.Model):
    _name = 'project.task'
    _description = "Task"
    _date_name = "date_assign"
    _inherit = 'project.task.template',

    _primary_email = 'email_from'


    date_last_stage_update = fields.Datetime(string='Last Stage Update',
        index=True,
        copy=False,
        readonly=True,
        help="Date on which the state of your task has last been modified.\n"
            "Based on this information you can identify tasks that are stalling and get statistics on the time it usually takes to move tasks from one stage/state to another.")

    role_ids = fields.Many2many('project.role', string='Project Roles')
    # Need this field to check there is no email loops when Odoo reply automatically
    email_from = fields.Char('Email From')
    email_cc = fields.Char(help='Email addresses that were in the CC of the incoming emails from this task and that are not currently linked to an existing customer.')
    color = fields.Integer(string='Color Index', export_string_translation=False)
    rating_active = fields.Boolean(string='Project Rating Status', related="project_id.rating_active")
    attachment_ids = fields.One2many(
        'ir.attachment',
        compute='_compute_attachment_ids',
        string="Attachments",
        export_string_translation=False,
        help="Attachments that don't come from a message",
    )
    # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
    displayed_image_id = fields.Many2one('ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Cover Image')

    link_preview_name = fields.Char(compute='_compute_link_preview_name', export_string_translation=False)
    has_project_template = fields.Boolean(related='project_id.is_template', string="Has Project Template", export_string_translation=False)
    has_template_ancestor = fields.Boolean(compute='_compute_has_template_ancestor', search='_search_has_template_ancestor',
                                           recursive=True, export_string_translation=False)

    @property
    def TASK_PORTAL_READABLE_FIELDS(self):
        return PROJECT_TASK_READABLE_FIELDS

    @property
    def TASK_PORTAL_WRITABLE_FIELDS(self):
        return PROJECT_TASK_WRITABLE_FIELDS
   
    def _compute_access_url(self):
        super()._compute_access_url()
        for task in self:
            task.access_url = f'/my/tasks/{task.id}'

    def _compute_access_warning(self):
        super()._compute_access_warning()
        for task in self.filtered(lambda x: x.project_id.privacy_visibility != 'portal'):
            visibility_field = self.env['ir.model.fields'].search([('model', '=', 'project.project'), ('name', '=', 'privacy_visibility')], limit=1)
            visibility_public = self.env['ir.model.fields.selection'].search([('field_id', '=', visibility_field.id), ('value', '=', 'portal')])
            task.access_warning = _(
                "The task cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy of the project to '%(visibility)s' in order to make it accessible by the recipient(s).",
                visibility=visibility_public.name,
            )

    def _compute_link_preview_name(self):
        for task in self:
            link_preview_name = task.display_name
            if task.project_id:
                link_preview_name += f' | {task.project_id.sudo().name}'
            task.link_preview_name = link_preview_name

    @api.depends('is_template', 'parent_id.has_template_ancestor')
    def _compute_has_template_ancestor(self):
        for task in self:
            task.has_template_ancestor = task.is_template or (task.parent_id and task.parent_id.has_template_ancestor)

    def _search_has_template_ancestor(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            return NotImplemented
        template_tasks = self.env['project.task'].with_context(active_test=False).sudo().search([('is_template', '=', True)])
        domain = [('id', 'child_of', template_tasks.ids)]
        if (operator == "=") != value:
            domain = ['!', ('id', 'child_of', template_tasks.ids)]
        return domain

    def copy_data(self, default=None):
        default = dict(default or {})
        default.update({
            'depend_on_ids': False,
            'dependent_ids': False,
        })
        vals_list = super().copy_data(default=default)
        # filter only readable fields
        vals_list = [
            {
                k: v
                for k, v in vals.items()
                if self._has_field_access(self._fields[k], 'read')
            }
            for vals in vals_list
        ]

        active_users = self.env['res.users']
        has_default_users = 'user_ids' in default
        if not has_default_users:
            active_users = self.user_ids.filtered('active')
        milestone_mapping = self.env.context.get('milestone_mapping', {})
        for task, vals in zip(self, vals_list):

            if not default.get('stage_id'):
                vals['stage_id'] = task.stage_id.id
            if 'active' not in default and not task['active'] and not self.env.context.get('copy_project'):
                vals['active'] = True
            vals['name'] = task.name if self.env.context.get('copy_project') or self.env.context.get('copy_from_template') else _("%s (copy)", task.name)
            if task.recurrence_id and not default.get('recurrence_id'):
                vals['recurrence_id'] = task.recurrence_id.copy().id
            if task.allow_milestones:
                vals['milestone_id'] = milestone_mapping.get(vals['milestone_id'], vals['milestone_id'])
            if not default.get('child_ids') and task.child_ids:
                default = {
                    'parent_id': False,
                }
                current_task = task
                if self.env.context.get('copy_from_template'):
                    current_task = current_task.with_context(active_test=True)
                child_ids = current_task.child_ids
                vals['child_ids'] = [Command.create(child_id.copy_data(default)[0]) for child_id in child_ids]
            if not has_default_users and vals['user_ids']:
                task_active_users = task.user_ids & active_users
                vals['user_ids'] = [Command.set(task_active_users.ids)]
            if task.is_template and not self.env.context.get('copy_from_template'):
                vals['is_template'] = True
            if self.env.context.get('copy_from_template'):
                for field in set(self._get_template_field_blacklist()) & set(vals.keys()):
                    del vals[field]
        return vals_list

    def _create_task_mapping(self, copied_tasks):
        """
        Thanks to the way create and command.create is handled, when a task with 2 children is copied, we have the guarantee that the children of the
        copied task will have the same index in the child_ids recordset. We can use this behavior to create a mapping containing all the original tasks and their copy.
        :return:
            task_mapping: a dict containing the mapping of the original task ids and their copied task (k: original_task.id, v: new_task)
            task_dependencies: a dict containing the ids of the dependencies of the original task when they have one.
            (k: original_task_id, v: [original_task.depend_on_ids.ids, original_task.dependent_ids.ids]
        """
        task_mapping, task_dependencies = {}, {}
        for original_task, copied_task in zip(self, copied_tasks):
            task_mapping[original_task.id] = copied_task
            if original_task.allow_task_dependencies and (original_task.depend_on_ids or original_task.dependent_ids):
                task_dependencies[original_task.id] = [original_task.depend_on_ids.ids, original_task.dependent_ids.ids]
            if original_task.child_ids:
                # If the task has children, we have to call the method create_task_mapping to get their ids and dependencies mapping too.
                children_mapping, children_dependencies = original_task.child_ids._create_task_mapping(copied_task.child_ids)
                task_mapping.update(children_mapping)
                task_dependencies.update(children_dependencies)
        return task_mapping, task_dependencies

    def _portal_get_parent_hash_token(self, pid):
        return self.project_id._sign_token(pid)

    def _resolve_copied_dependencies(self, copied_tasks):
        task_mapping, task_dependencies = self._create_task_mapping(copied_tasks)

        for original_task_id, (depend_on_ids, dependant_ids) in task_dependencies.items():
            # If one of the task_id in the dependencies mapping is also a key of the task_mapping, it means that this task was copied too.
            # In this case, we should exchange this id with the id of the corresponding copied task
            task_mapping[original_task_id].depend_on_ids = [
                task_id if task_id not in task_mapping else task_mapping[task_id].id
                for task_id in depend_on_ids
            ]
            task_mapping[original_task_id].dependent_ids = [
                task_id if task_id not in task_mapping else task_mapping[task_id].id
                for task_id in dependant_ids
            ]

    def copy(self, default=None):
        default = default or {}
        copied_tasks = super(ProjectTask, self.with_context(
            mail_auto_subscribe_no_notify=True,
            mail_create_nosubscribe=True,
            mail_create_nolog=True,
        )).copy(default=default)

        self._resolve_copied_dependencies(copied_tasks)
        log_message = _("Task Created")
        copied_tasks._message_log_batch(bodies={task.id: log_message for task in copied_tasks})

        return copied_tasks

    @api.model
    def get_empty_list_help(self, help_message):
        tname = _("task")
        project_id = self.env.context.get('default_project_id', False)
        if project_id:
            name = self.env['project.project'].browse(project_id).label_tasks
            if name: tname = name.lower()

        self = self.with_context(
            empty_list_help_id=self.env.context.get('default_project_id'),
            empty_list_help_model='project.project',
            empty_list_help_document_name=tname,
        )
        return super().get_empty_list_help(help_message)

    # ----------------------------------------
    # Case management
    # ----------------------------------------

    def stage_find(self, section_id, domain=[], order='sequence, id'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        section_ids.extend(self.mapped('project_id').ids)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        return self.env['project.task.type'].search(search_domain, order=order, limit=1).id

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of fields_get making fields readonly for portal users
        makes the view cache dependent on the fact the user has the group portal or not"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.user._is_portal(),)

    @api.model
    def default_get(self, default_fields):
        vals = super().default_get(default_fields)

        if project_id := self.env.context.get('default_create_in_project_id'):
            vals['project_id'] = project_id

        # prevent creating new task in the waiting state
        if 'state' in default_fields and vals.get('state') == '04_waiting_normal':
            vals['state'] = '01_in_progress'

        if 'repeat_until' in default_fields:
            vals['repeat_until'] = fields.Date.today() + timedelta(days=7)

        if 'partner_id' in vals and not vals['partner_id']:
            # if the default_partner_id=False or no default_partner_id then we search the partner based on the project and parent
            project_id = vals.get('project_id')
            parent_id = vals.get('parent_id', self.env.context.get('default_parent_id'))
            if project_id or parent_id:
                partner_id = self._get_default_partner_id(
                    project_id and self.env['project.project'].browse(project_id),
                    parent_id and self.env['project.task'].browse(parent_id)
                )
                if partner_id:
                    vals['partner_id'] = partner_id
        project_id = vals.get('project_id', self.env.context.get('default_project_id'))
        if project_id:
            project = self.env['project.project'].browse(project_id)
            if 'company_id' in default_fields and 'default_project_id' not in self.env.context:
                vals['company_id'] = project.sudo().company_id.id
        elif 'default_user_ids' not in self.env.context and 'user_ids' in default_fields:
            user_ids = vals.get('user_ids', [])
            user_ids.append(Command.link(self.env.user.id))
            vals['user_ids'] = user_ids

        return vals

    @api.model
    @tools.ormcache()
    def _portal_accessible_fields(self) -> tuple[frozenset[str], frozenset[str]]:
        """Readable and writable fields by portal users."""
        readable = frozenset(self.TASK_PORTAL_READABLE_FIELDS)
        writeable = frozenset(self.TASK_PORTAL_WRITABLE_FIELDS)
        return readable | writeable, writeable

    def _has_field_access(self, field, operation):
        if not super()._has_field_access(field, operation):
            return False
        if not self.env.su and self.env.user._is_portal():
            # additional checks for portal users
            readable, writeable = self._portal_accessible_fields()
            if operation == 'read':
                return field.name in readable
            if operation == 'write':
                return field.name in writeable
        return True

    def _set_stage_on_project_from_task(self):
        stage_ids_per_project = defaultdict(list)
        for task in self:
            if task.stage_id and task.stage_id not in task.project_id.type_ids and task.stage_id.id not in stage_ids_per_project[task.project_id]:
                stage_ids_per_project[task.project_id].append(task.stage_id.id)

        for project, stage_ids in stage_ids_per_project.items():
            project.write({'type_ids': [Command.link(stage_id) for stage_id in stage_ids]})

    def _load_records_create(self, vals_list):
        for vals in vals_list:
            if vals.get('recurring_task'):
                if not vals.get('recurrence_id'):
                    default_val = self.default_get(self._get_recurrence_fields())
                    vals.update(**default_val)
            project_id = vals.get('project_id')
            if project_id:
                self = self.with_context(default_project_id=project_id)
        tasks = super()._load_records_create(vals_list)

        return tasks

    @api.model_create_multi
    def create(self, vals_list):
        # Some values are determined by this override and must be written as
        # sudo for portal users, because they do not have access to these
        # fields. Other values must not be written as sudo.
        additional_vals_list = [{} for _ in vals_list]

        new_context = dict(self.env.context)
        default_personal_stage = new_context.pop('default_personal_stage_type_ids', False)
        default_project_id = new_context.pop('default_project_id', False)
        if not default_project_id:
            parent_task = self.browse({parent_id for vals in vals_list if (parent_id := vals.get('parent_id'))})
            if len(parent_task) == 1:
                default_project_id = parent_task.sudo().project_id.id
        # (portal) users that don't have write access can still create a task
        # in the project that will be checked using record rules
        new_context["default_create_in_project_id"] = default_project_id
        if not self._has_field_access(self._fields['user_ids'], 'write'):
            # remove user_ids if we have no access to it
            new_context.pop('default_user_ids', False)
        self = self.with_context(new_context)

        self.browse().check_access('create')
        default_stage = dict()
        for vals, additional_vals in zip(vals_list, additional_vals_list):
            project_id = vals.get('project_id') or default_project_id

            if vals.get('user_ids'):
                additional_vals['date_assign'] = fields.Datetime.now()
                if not (vals.get('parent_id') or project_id):
                    user_ids = self._fields['user_ids'].convert_to_cache(vals.get('user_ids', []), self.env['project.task'])
                    if self.env.user.id not in list(user_ids) + [SUPERUSER_ID]:
                        additional_vals['user_ids'] = [Command.set(list(user_ids) + [self.env.user.id])]
            if default_personal_stage and 'personal_stage_type_id' not in vals:
                additional_vals['personal_stage_type_id'] = default_personal_stage[0]
            if not vals.get('name') and vals.get('display_name'):
                vals['name'] = vals['display_name']

            if project_id and not "company_id" in vals:
                additional_vals["company_id"] = self.env["project.project"].browse(
                    project_id
                ).company_id.id
            if not project_id and ("stage_id" in vals or self.env.context.get('default_stage_id')):
                vals["stage_id"] = False

            if project_id and "stage_id" not in vals:
                # 1) Allows keeping the batch creation of tasks
                # 2) Ensure the defaults are correct (and computed once by project),
                # by using default get (instead of _get_default_stage_id or _stage_find),
                if project_id not in default_stage:
                    default_stage[project_id] = self.with_context(
                        default_project_id=project_id
                    ).default_get(['stage_id']).get('stage_id')
                vals["stage_id"] = default_stage[project_id]

            # Stage change: Update date_end if folded stage and date_last_stage_update
            if vals.get('stage_id'):
                additional_vals.update(self.update_date_end(vals['stage_id']))
                additional_vals['date_last_stage_update'] = fields.Datetime.now()
            # recurrence
            rec_fields = vals.keys() & self._get_recurrence_fields()
            if rec_fields and vals.get('recurring_task') is True:
                rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
                recurrence = self.env['project.task.recurrence'].create(rec_values)
                vals['recurrence_id'] = recurrence.id

        # create the task, write computed inaccessible fields in sudo
        for vals, computed_vals in zip(vals_list, additional_vals_list):
            for field_name in list(computed_vals):
                if self._has_field_access(self._fields[field_name], 'write'):
                    vals[field_name] = computed_vals.pop(field_name)
        # no track when the portal user create a task to avoid using during tracking
        # process since the portal does not have access to tracking models
        tasks = super(ProjectTask, self.with_context(mail_create_nosubscribe=True, mail_notrack=not self.env.su and self.env.user._is_portal())).create(vals_list)
        for task, computed_vals in zip(tasks.sudo(), additional_vals_list):
            if computed_vals:
                task.write(computed_vals)
        tasks.sudo()._populate_missing_personal_stages()
        self._task_message_auto_subscribe_notify({task: task.user_ids - self.env.user for task in tasks})

        current_partner = self.env.user.partner_id

        all_partner_emails = []
        for task in tasks.sudo():
            all_partner_emails += tools.email_normalize_all(task.email_cc)
        partners = self.env['res.partner'].search([('email', 'in', all_partner_emails)])
        partner_per_email = {
            partner.email: partner
            for partner in partners
            if not all(u.share for u in partner.user_ids)
        }
        if tasks.project_id:
            tasks.sudo()._set_stage_on_project_from_task()
        for task in tasks.sudo():
            if task.project_id.privacy_visibility == 'portal':
                task._portal_ensure_token()
            for follower in task.parent_id.message_follower_ids:
                task.message_subscribe(follower.partner_id.ids, follower.subtype_ids.ids)
            if current_partner not in task.message_partner_ids:
                task.message_subscribe(current_partner.ids)
            if task.email_cc:
                partners_with_internal_user = self.env['res.partner']
                for email in tools.email_normalize_all(task.email_cc):
                    new_partner = partner_per_email.get(email)
                    if new_partner:
                        partners_with_internal_user |= new_partner
                if not partners_with_internal_user:
                    continue
                task._send_email_notify_to_cc(partners_with_internal_user)
                task.message_subscribe(partners_with_internal_user.ids)
        return tasks

    def update_date_end(self, stage_id):
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.fold:
            return {'date_end': fields.Datetime.now()}
        return {'date_end': False}

    def _search_on_comodel(self, domain, field, comodel, additional_domain=None):
        """ This method is called by `group_expand` methods, whose purpose is to add empty groups to the `read_group`
            (which otherwise returns groups containing records that match the domain).
            When specifically filtering on a comodel's field, the result of the `read_group` should contain all matching groups.
            However, if the search isn't filtered on any comodel's field, the result shouldn't be affected,
            which explains why we return `False` if `filtered_domain` is empty.

            Returns:
                False or recordset of the comodel given in parameter.
        """
        def _change_operator(domain):
            new_domain = []
            for dom in domain:
                if len(dom) == 3:
                    _, op, value = dom
                    op = "ilike" if op == "child_of" else op
                    if isinstance(value, list) and all(isinstance(val, int) for val in value):
                        new_domain.append(("id", op, value))
                    if isinstance(value, str) or (isinstance(value, list) and not all(isinstance(val, str) for val in value)):
                        new_domain.append(("name", op, value))
                    if isinstance(value, int):
                        if op == "=":
                            op = "in"
                        if op == "!=":
                            op = "not in"
                        new_domain.append(("id", op, [value]))
                else:
                    new_domain.append(dom)
            return new_domain

        filtered_domain = filter_domain_leaf(domain, lambda field_to_check: field_to_check in [
            field,
            f"{field}.id",
            f"{field}.name",
        ], {
            field: "name",
            f"{field}.id": "id",
            f"{field}.name": "name",
        })
        if not filtered_domain.is_true():
            # If domain is not equal to Domain.TRUE then
            filtered_domain = _change_operator(filtered_domain)
        if not filtered_domain:
            return self.env[comodel]
        if additional_domain:
            filtered_domain = expression.AND([filtered_domain, additional_domain])
        return self.env[comodel].search(filtered_domain)

    # ---------------------------------------------------
    # Subtasks
    # ---------------------------------------------------

    @api.depends('parent_id.partner_id', 'project_id')
    def _compute_partner_id(self):
        """ Compute the partner_id when the tasks have no partner_id.

            Use the project partner_id if any, or else the parent task partner_id.
        """
        for task in self:
            if task.has_template_ancestor:
                continue
            if task.partner_id and not (task.project_id or task.parent_id):
                task.partner_id = False
                continue
            if not task.partner_id:
                task.partner_id = self._get_default_partner_id(task.project_id, task.parent_id)

    @api.depends('project_id')
    def _compute_milestone_id(self):
        for task in self:
            if task.project_id != task.milestone_id.project_id:
                task.milestone_id = task.parent_id.project_id == task.project_id and task.parent_id.milestone_id

    def _compute_has_late_and_unreached_milestone(self):
        if all(not task.allow_milestones for task in self):
            self.has_late_and_unreached_milestone = False
            return
        late_milestones = self.env['project.milestone'].sudo()._search([  # sudo is needed for the portal user in Project Sharing.
            ('id', 'in', self.milestone_id.ids),
            ('is_reached', '=', False),
            ('deadline', '<=', fields.Date.today()),
        ])
        for task in self:
            task.has_late_and_unreached_milestone = task.allow_milestones and task.milestone_id.id in late_milestones

    def _search_has_late_and_unreached_milestone(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [
            ('allow_milestones', '=', True),
            ('milestone_id', 'any', [
                ('is_reached', '=', False),
                ('deadline', '<', fields.Date.today()),
            ]),
        ]

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        project_name = self.project_id.sudo().name
        stage_name = self.stage_id.name
        subtitles = ""
        if project_name and stage_name:
            subtitles = _('Project: %(project_name)s, Stage: %(stage_name)s', project_name=project_name, stage_name=stage_name)
        elif project_name:
            subtitles = _('Project: %(project_name)s', project_name=project_name)
        elif stage_name:
            subtitles = _('Stage: %(stage_name)s', stage_name=stage_name)
        if subtitles:
            render_context['subtitles'].append(subtitles)
        return render_context

    def _send_email_notify_to_cc(self, partners_to_notify):
        # TDE TODO: this should be removed with email-like recipients management
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('project.task_invitation_follower', raise_if_not_found=False)
        if not template_id:
            return
        task_model_description = self.env['ir.model']._get(self._name).display_name
        values = {
            'object': self,
        }
        for partner in partners_to_notify:
            values['partner_name'] = partner.name
            assignation_msg = self.env['ir.qweb']._render('project.task_invitation_follower', values, minimal_qcontext=True)
            self.message_notify(
                subject=_('You have been invited to follow %s', self.display_name),
                body=assignation_msg,
                partner_ids=partner.ids,
                record_name=self.display_name,
                email_layout_xmlid='mail.mail_notification_layout',
                model_description=task_model_description,
                mail_auto_delete=True,
            )

    @api.model
    def _task_message_auto_subscribe_notify(self, users_per_task):
        if self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        # Utility method to send assignation notification upon writing/creation.
        template_id = self.env['ir.model.data']._xmlid_to_res_id('project.project_message_user_assigned', raise_if_not_found=False)
        if not template_id:
            return
        task_model_description = self.env['ir.model']._get(self._name).display_name
        for task, users in users_per_task.items():
            if not users:
                continue
            values = {
                'object': task,
                'model_description': task_model_description,
                'access_link': task._notify_get_action_link('view'),
            }
            for user in users:
                values.update(assignee_name=user.sudo().name)
                assignation_msg = self.env['ir.qweb']._render('project.project_message_user_assigned', values, minimal_qcontext=True)
                assignation_msg = self.env['mail.render.mixin']._replace_local_links(assignation_msg)
                task.message_notify(
                    subject=_('You have been assigned to %s', task.display_name),
                    body=assignation_msg,
                    partner_ids=user.partner_id.ids,
                    record_name=task.display_name,
                    email_layout_xmlid='mail.mail_notification_layout',
                    model_description=task_model_description,
                    mail_auto_delete=False,
                )

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        if 'user_ids' not in updated_values:
            return []
        # Since the changes to user_ids becoming a m2m, the default implementation of this function
        #  could not work anymore, override the function to keep the functionality.
        new_followers = []
        # Normalize input to tuple of ids
        value = self._fields['user_ids'].convert_to_cache(updated_values.get('user_ids', []), self.env['project.task'], validate=False)
        users = self.env['res.users'].browse(value)
        for user in users:
            try:
                if user.partner_id:
                    # The you have been assigned notification is handled separately
                    new_followers.append((user.partner_id.id, default_subtype_ids, False))
            except Exception:
                pass
        return new_followers

    def _track_template(self, changes):
        res = super()._track_template(changes)
        test_task = self[0]
        if 'stage_id' in changes and test_task.stage_id.mail_template_id and not test_task.is_template:
            res['stage_id'] = (test_task.stage_id.mail_template_id, {
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res

    def _creation_subtype(self):
        return self.env.ref('project.mt_task_new')

    def _creation_message(self):
        self.ensure_one()
        if self.project_id:
            return _('A new task has been created in the "%(project_name)s" project.',
                     project_name=self.project_id.display_name)
        return _('A new task has been created and is not part of any project.')

    def _track_subtype(self, init_values):
        self.ensure_one()
        mail_message_subtype_per_state = {
            '1_done': 'project.mt_task_done',
            '1_canceled': 'project.mt_task_canceled',
            '01_in_progress': 'project.mt_task_in_progress',
            '03_approved': 'project.mt_task_approved',
            '02_changes_requested': 'project.mt_task_changes_requested',
            '04_waiting_normal': 'project.mt_task_waiting',
        }

        if 'stage_id' in init_values:
            return self.env.ref('project.mt_task_stage')
        elif 'state' in init_values and self.state in mail_message_subtype_per_state:
            return self.env.ref(mail_message_subtype_per_state[self.state])
        return super()._track_subtype(init_values)

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if not self.project_id.rating_active:
            res -= self.env.ref('project.mt_task_rating')
        if len(self) == 1:
            waiting_subtype = self.env.ref('project.mt_task_waiting')
            if ((self.project_id and not self.project_id.allow_task_dependencies)\
                or (not self.project_id and not self.env.user.has_group('project.group_project_task_dependencies')))\
                and waiting_subtype in res:
                res -= waiting_subtype
        return res

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        # Handle project users and managers recipients that can assign
        # tasks and create new one directly from notification emails. Also give
        # access button to portal users and portal customers. If they are notified
        # they should probably have access to the document.
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()

        project_user_group_id = self.env.ref('project.group_project_user').id
        new_group = ('group_project_user', lambda pdata: pdata['type'] == 'user' and project_user_group_id in pdata['groups'], {})
        groups = [new_group] + groups

        if self.project_privacy_visibility == 'portal':
            groups.insert(0, (
                'allowed_portal_users',
                lambda pdata: pdata['type'] == 'portal',
                {
                    'active': True,
                    'has_button_access': True,
                }
            ))
        portal_privacy = self.project_id.privacy_visibility == 'portal'
        for group_name, _group_method, group_data in groups:
            if group_name in ('customer', 'user') or group_name == 'portal_customer' and not portal_privacy:
                group_data['has_button_access'] = False
            elif group_name == 'portal_customer' and portal_privacy:
                group_data['has_button_access'] = True

        return groups

    def _notify_get_reply_to(self, default=None, author_id=False):
        # Override to set alias of tasks to their project if any
        aliases = self.sudo().mapped('project_id')._notify_get_reply_to(default=default, author_id=author_id)
        res = {task.id: aliases.get(task.project_id.id) for task in self}
        leftover = self.filtered(lambda rec: not rec.project_id)
        if leftover:
            res.update(super(ProjectTask, leftover)._notify_get_reply_to(default=default, author_id=author_id))
        return res

    def _ensure_personal_stages(self):
        user = self.env.user
        ProjectTaskTypeSudo = self.env['project.task.type'].sudo()
        # In the case no stages have been found, we create the default stages for the user
        if not ProjectTaskTypeSudo.search_count([('user_id', '=', user.id)], limit=1):
            ProjectTaskTypeSudo.with_context(lang=user.lang, default_project_id=False).create(
                self.with_context(lang=user.lang)._get_default_personal_stage_create_vals(user.id)
            )

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_ids'] = False
        if custom_values is None:
            custom_values = {}
        # Auto create partner if not existent when the task is created from email
        if not msg_dict.get('author_id') and msg_dict.get('email_from'):
            author = self.env['mail.thread']._partner_find_from_emails_single([msg_dict['email_from']], no_create=False)
            msg_dict['author_id'] = author.id

        defaults = {
            'name': msg_dict.get('subject') or _("No Subject"),
            'allocated_hours': 0.0,
            'partner_id': msg_dict.get('author_id'),
        }
        defaults.update(custom_values)

        task = super(ProjectTask, self.with_context(create_context)).message_new(msg_dict, custom_values=defaults)
        partners = task._partner_find_from_emails_single(tools.email_split((msg_dict.get('to') or '') + ',' + (msg_dict.get('cc') or '')), no_create=True)
        task.message_subscribe(partners.ids)
        return task

    def message_update(self, msg_dict, update_vals=None):
        for task in self:
            partners = task._partner_find_from_emails_single(tools.email_split((msg_dict.get('to') or '') + ',' + (msg_dict.get('cc') or '')), no_create=True)
            task.message_subscribe(partners.ids)
        return super().message_update(msg_dict, update_vals=update_vals)

    def _notify_by_email_get_headers(self, headers=None):
        headers = super()._notify_by_email_get_headers(headers=headers)
        if self.project_id:
            current_objects = [h for h in headers.get('X-Odoo-Objects', '').split(',') if h]
            current_objects.insert(0, 'project.project-%s, ' % self.project_id.id)
            headers['X-Odoo-Objects'] = ','.join(current_objects)
        if self.tag_ids:
            headers['X-Odoo-Tags'] = ','.join(self.tag_ids.mapped('name'))
        return headers

    def _message_post_after_hook(self, message, msg_vals):
        if message.attachment_ids and not self.displayed_image_id:
            image_attachments = message.attachment_ids.filtered(lambda a: a.mimetype == 'image')
            if image_attachments:
                self.displayed_image_id = image_attachments[0]

        # use the sanitized body of the email from the message thread to populate the task's description
        if (
           not self.description
           and message.subtype_id == self._creation_subtype()
           and self.partner_id == message.author_id
           and msg_vals['message_type'] == 'email'
        ):
            self.description = message.body
        return super()._message_post_after_hook(message, msg_vals)

    def _get_projects_to_make_billable_domain(self, additional_domain=None):
        return expression.AND([
            [('partner_id', '!=', False)],
            additional_domain or [],
        ])

    def _get_all_subtasks(self):
        return self.browse(set.union(set(), *self._get_subtask_ids_per_task_id().values()))

    def _get_subtask_ids_per_task_id(self):
        if not self:
            return {}

        res = dict.fromkeys(self._ids, [])
        if all(self._ids):
            self.env.cr.execute(
                """
         WITH RECURSIVE task_tree
                     AS (
                     SELECT id, id as supertask_id
                       FROM project_task
                      WHERE id IN %(ancestor_ids)s
                      UNION
                         SELECT t.id, tree.supertask_id
                           FROM project_task t
                           JOIN task_tree tree
                             ON tree.id = t.parent_id
                            AND t.active in (TRUE, %(active)s)
                          WHERE t.parent_id IS NOT NULL
               ) SELECT supertask_id, ARRAY_AGG(id)
                   FROM task_tree
                  WHERE id != supertask_id
               GROUP BY supertask_id
                """,
                {
                    "ancestor_ids": tuple(self.ids),
                    "active": self.env.context.get('active_test', True),
                }
            )
            res.update(dict(self.env.cr.fetchall()))
        else:
            res.update({
                task.id: task._get_subtasks_recursively().ids
                for task in self
            })
        return res

    def _get_subtasks_recursively(self):
        children = self.child_ids
        if not children:
            return self.env['project.task']
        return children + children._get_subtasks_recursively()

    def action_open_parent_task(self):
        return {
            'name': _('Parent Task'),
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context
        }

    def action_project_sharing_view_parent_task(self):
        if self.parent_id.project_id != self.project_id and self.env.user._is_portal():
            project = self.parent_id.project_id._filtered_access('read')
            if project:
                url = f"/my/projects/{self.parent_id.project_id.id}/task/{self.parent_id.id}"
                if project._check_project_sharing_access():
                    url = f"/my/projects/{self.parent_id.project_id.id}?task_id={self.parent_id.id}"
                return {
                    "name": "Portal Parent Task",
                    "type": "ir.actions.act_url",
                    "url": url,
                }
            elif self.display_parent_task_button:
                return self.parent_id.get_portal_url()
            # The portal user has no access to the parent task, so normally the button should be invisible.
            return {}
        action = self.with_context({
            'search_view_ref': 'project.project_sharing_project_task_view_search',
        }).action_open_parent_task()
        action['views'] = [(self.env.ref('project.project_sharing_project_task_view_form').id, 'form')]
        action['search_view_id'] = self.env.ref("project.project_sharing_project_task_view_search").id
        return action

    # ------------
    # Actions
    # ------------

    def action_open_task(self):
        return {
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context
        }

    def action_project_sharing_open_task(self):
        action = self.action_open_task()
        action['views'] = [[self.env.ref('project.project_sharing_project_task_view_form').id, 'form']]
        return action

    def action_project_sharing_open_subtasks(self):
        self.ensure_one()
        subtasks = self.env['project.task'].search([('id', 'child_of', self.id), ('id', '!=', self.id)])
        if subtasks.project_id == self.project_id:
            action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_action_sub_task')
            if len(subtasks) == 1:
                action['view_mode'] = 'form'
                action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form']
                action['res_id'] = subtasks.id
            return action
        return {
            'name': 'Portal Sub-tasks',
            'type': 'ir.actions.act_url',
            'url': f'/my/projects/{self.project_id.id}/task/{self.id}/subtasks' if len(subtasks) > 1 else subtasks.get_portal_url(query_string='project_sharing=1'),
        }

    def action_project_sharing_open_blocking(self):
        self.ensure_one()
        blockings = self.dependent_ids
        action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_action_blocking_tasks')
        if len(blockings) == 1:
            action['view_mode'] = 'form'
            action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form']
            action['res_id'] = blockings.id
        return action

    def action_dependent_tasks(self):
        self.ensure_one()
        return {
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'context': {**self.env.context, 'default_depend_on_ids': [Command.link(self.id)], 'show_project_update': False, 'search_default_open_tasks': True},
            'domain': [('depend_on_ids', '=', self.id)],
            'name': _('Dependent Tasks'),
            'view_mode': 'list,form,kanban,calendar,pivot,graph,activity',
        }

    def action_recurring_tasks(self):
        return {
            'name': _('Tasks in Recurrence'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form,kanban,calendar,pivot,graph,activity',
            'context': {'create': False},
            'domain': [('recurrence_id', 'in', self.recurrence_id.ids)],
        }

    def action_project_sharing_recurring_tasks(self):
        self.ensure_one()
        recurrent_tasks = self.env['project.task'].search([('recurrence_id', 'in', self.recurrence_id.ids)])
        # If all the recurrent tasks are in the same project, open the list view in sharing mode.
        if recurrent_tasks.project_id == self.project_id:
            action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_recurring_tasks_action')
            action.update({
                'context': {'default_project_id': self.project_id.id},
                'domain': [
                    ('project_id', '=', self.project_id.id),
                    ('recurrence_id', 'in', self.recurrence_id.ids)
                ]
            })
            return action
        # If at least one recurrent task belong to another project, open the portal page
        return {
            'name': 'Portal Recurrent Tasks',
            'type': 'ir.actions.act_url',
            'url':  f'/my/projects/{self.project_id.id}/task/{self.id}/recurrent_tasks',
        }

    def action_open_ratings(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.rating_rating_action_task')
        if self.rating_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.rating_ids[0].id
            action['views'] = [[self.env.ref('project.rating_rating_view_form_project').id, 'form']]
            return action
        else:
            return action

    def action_unlink_recurrence(self):
        self.recurrence_id.task_ids.recurring_task = False
        self.recurrence_id.unlink()

    def action_convert_to_subtask(self):
        self.ensure_one()
        if self.project_id:
            return {
                'name': _('Convert to Task/Sub-Task'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'res_id': self.id,
                'views': [(self.env.ref('project.project_task_convert_to_subtask_view_form', False).id, 'form')],
                'target': 'new',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'danger',
                'message': _('Private tasks cannot be converted into sub-tasks. Please set a project on the task to gain access to this feature.'),
            }
        }

    def action_convert_to_template(self):
        self.ensure_one()
        if not self.project_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _('Private tasks cannot be converted into templates'),
                },
            }
        if self.is_template:
            if self.project_id.is_template:
                raise UserError(self.env._("Tasks in a project template cannot be converted into regular tasks."))

            return {
                'type': 'ir.actions.client',
                'tag': 'project_show_template_undo_confirmation_dialog',
                'params': {
                    'task_id': self.id,
                },
            }
        self.is_template = True
        self.message_post(body=_("Task converted to template"))
        return {
            'type': 'ir.actions.client',
            'tag': 'project_show_template_notification',
            'params': {
                'task_id': self.id,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            },
        }

    def action_undo_convert_to_template(self):
        self.ensure_one()
        self.is_template = False
        self.role_ids = False
        self.message_post(body=_("Template converted back to regular task"))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Template converted back to regular task'),
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            },
        }

    def plan_task_in_calendar(self, vals):
        self.ensure_one()
        return self.write(vals)

    @api.model
    def _get_template_default_context_whitelist(self):
        """
        Whitelist of fields that can be set through the `default_` context keys when creating a task from a template.
        """
        return [
            "parent_id",
        ]

    @api.model
    def _get_template_field_blacklist(self):
        """
        Blacklist of fields to not copy when creating a task from a template.
        """
        return [
            "partner_id",
        ]

    def action_create_from_template(self):
        self.ensure_one()
        default = {
            key[8:]: value
            for key, value in self.env.context.items()
            if key.startswith('default_') and key[8:] in self._get_template_default_context_whitelist()
        } | {
            field: False
            for field in self._get_template_field_blacklist()
        }
        return self.with_context(copy_from_template=True).copy(default=default).id

    def action_archive(self):
        child_tasks = self.child_ids.filtered(lambda child_task: not child_task.display_in_project)
        if child_tasks:
            child_tasks.action_archive()
        self.filtered(lambda t: not t.display_in_project and t.parent_id).display_in_project = True
        return super().action_archive()

    # ---------------------------------------------------
    # Rating business
    # ---------------------------------------------------

    def _send_task_rating_mail(self, force_send=False):
        for task in self:
            rating_template = task.stage_id.rating_template_id
            partner = task.partner_id
            if rating_template and partner and partner != self.env.user.partner_id and not task.is_template:
                task.rating_send_request(rating_template, lang=task.partner_id.lang, force_send=force_send)

    def _rating_get_partner(self):
        res = super()._rating_get_partner()
        if not res and self.project_id.partner_id:
            return self.project_id.partner_id
        return res

    def rating_apply(self, rate, token=None, rating=None, feedback=None,
                     subtype_xmlid=None, notify_delay_send=False):
        rating = super().rating_apply(
            rate, token=token, rating=rating, feedback=feedback,
            subtype_xmlid=subtype_xmlid, notify_delay_send=notify_delay_send)
        if self.stage_id and self.stage_id.auto_validation_state:
            state = '03_approved' if rating.rating >= rating_data.RATING_LIMIT_SATISFIED else '02_changes_requested'
            self.write({'state': state})
        return rating

    def _rating_apply_get_default_subtype_id(self):
        return self.env['ir.model.data']._xmlid_to_res_id("project.mt_task_rating")

    def _rating_get_parent_field_name(self):
        return 'project_id'

    def _rating_get_operator(self):
        """ Overwrite since we have user_ids and not user_id """
        tasks_with_one_user = self.filtered(lambda task: len(task.user_ids) == 1 and task.user_ids.partner_id)
        return tasks_with_one_user.user_ids.partner_id or self.env['res.partner']

    # ---------------------------------------------------
    # Privacy
    # ---------------------------------------------------
    def _unsubscribe_portal_users(self):
        self.message_unsubscribe(partner_ids=self.message_partner_ids.filtered('user_ids.share').ids)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        calendar = self.env.company.resource_calendar_id
        return calendar._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=UTC),
            datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=UTC)
        )

    def action_redirect_to_project_task_form(self):
        menu_id = self.env.ref('project.menu_project_management_all_tasks').id
        return {
            'type': 'ir.actions.act_url',
            'url': f"/odoo/1/action-project.act_project_project_2_project_task_all/{self.id}?menu_id={menu_id}",
            'target': 'new',
        }

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None) -> list[tuple]:
        # A _read_group cannot be performed if records are grouped by personal_stage_type_id
        # as it is a computed field. personal_stage_type_ids behaves like a M2O from the point
        # of view of the user, we therefore use this field instead.
        if 'personal_stage_type_id' in groupby:
            # limitation: problem when both personal_stage_type_id and personal_stage_type_ids
            # appear in read_group, but this has no functional utility
            groupby = ['personal_stage_type_ids' if fname == 'personal_stage_type_id' else fname for fname in groupby]
            if order:
                order = order.replace('personal_stage_type_id', 'personal_stage_type_ids')
        return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

    # ---------------------------------------------------
    # Project Sharing
    # ---------------------------------------------------

    def project_sharing_toggle_is_follower(self):
        self.ensure_one()
        self.check_access('write')
        is_follower = self.message_is_follower
        if is_follower:
            self.sudo().message_unsubscribe(self.env.user.partner_id.ids)
        else:
            self.sudo().message_subscribe(self.env.user.partner_id.ids)
        return not is_follower

    @api.depends('subtask_count', 'closed_subtask_count')
    def _compute_subtask_completion_percentage(self):
        for task in self:
            task.subtask_completion_percentage = task.subtask_count and task.closed_subtask_count / task.subtask_count

    @api.model
    def _get_allowed_access_params(self):
        return super()._get_allowed_access_params() | {'project_sharing_id'}

    @api.model
    def _get_thread_with_access(self, thread_id, *, project_sharing_id=None, token=None, **kwargs):
        if project_sharing_id:
            if token := ProjectSharingChatter._check_project_access_and_get_token(
                self, project_sharing_id, self._name, thread_id, token
            ):
                token = token
        return super()._get_thread_with_access(thread_id, project_sharing_id=project_sharing_id, token=token, **kwargs)

    def get_mention_suggestions(self, search, limit=8):
        """Return the 'limit'-first followers of the given task or followers of its project matching
        a 'search' string as a list of partner data (returned by `_to_store()`).
        See similar method for all partners `get_mention_suggestions()`.
        """
        self.ensure_one()
        project = self.project_id
        if not (
            project
            and project._check_project_sharing_access()
            and project._get_thread_with_access(project.id)
        ):
            return {}
        # sudo: mail.followers - reading message_follower_ids on accessible task/project is allowed
        followers = project.sudo().message_follower_ids | self.sudo().message_follower_ids
        domain = expression.AND([
            self.env["res.partner"]._get_mention_suggestions_domain(search),
            [("id", "in", followers.partner_id.ids)],
        ])
        partners = self.env["res.partner"].sudo()._search_mention_suggestions(domain, limit)
        return (
            Store()
            .add(
                self,
                {"limitedMentions": Store.Many(partners, ["email", "im_status", "name"])},
                as_thread=True,
            )
            .get_result()
        )

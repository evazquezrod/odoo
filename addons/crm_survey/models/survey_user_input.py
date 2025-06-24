from markupsafe import Markup, escape
from odoo import models, _


class SurveyUser_Input(models.Model):
    _inherit = "survey.user_input"

    def _mark_done(self):
        """ Check if we need to create a lead on answer submission, except for live sessions.

            (note: Here, we are going to filter the surveys submitted at the end by the user according to type.
            However, the live_session and custom types are present in the filter below.
            Their presence here corresponds to the case where a survey has simply been shared
            (as for the classic 'survey' type) without there being a live session.
            In this case, it is when the user has finally submitted the survey.
            Otherwise, if the submission is due from the host of a live session, this function is not called.
            So, please refer to the action_end_session function in survey.survey.)
        """
        super()._mark_done()

        # Generate lead
        user_inputs = self.filtered(lambda user_input:
            user_input.survey_id.survey_type in ['survey', 'live_session', 'custom']
        )
        user_inputs._create_leads_if_generative_answers()

    def _create_leads_if_generative_answers(self):
        """ This method filters the inputs to create leads and prepares the field
            data for each input accordingly. """
        user_inputs_generating_leads = self.filtered(lambda user_input:
            any(answer.is_create_lead for answer in user_input.user_input_line_ids.suggested_answer_id))
        user_inputs_grouped_by_survey = user_inputs_generating_leads.grouped('survey_id')
        lead_create_vals = []
        for __, user_input_ids in user_inputs_grouped_by_survey.items():
            survey_lead_values = self._prepare_common_survey_lead_values()
            for user_input_id in user_input_ids:
                lead_create_vals.append(user_input_id._prepare_user_input_lead_values() | survey_lead_values)
        odoobot = self.env.ref('base.user_root')
        self.env['crm.lead'].with_user(odoobot).create(lead_create_vals)

    def _prepare_common_survey_lead_values(self):
        source = self.env['utm.source'].search([('name', '=', self.survey_id.title)])
        if not source:
            source = self.env['utm.source'].create({'name': self.survey_id.title})
        return {
            'medium_id': self.env['utm.medium']._fetch_or_create_utm_medium('Survey').id,
            'source_id': source.id,
            'survey_id': self.survey_id.id,
            'type': 'opportunity',
        }

    def _prepare_user_input_lead_values(self):
        """ This method will prepare the user values dictionary for making the lead """
        self.ensure_one()

        user_input_lines_lead_data = self._prepare_lead_values_from_user_input_lines()

        # Check if the survey responsible is from, at least, a sales team
        survey_responsible = self.survey_id.user_id if self.survey_id.user_id.crm_team_ids else self.env['res.users']

        # Get the username
        username = self.partner_id.name
        if not username:  # Public user
            lead_title_start = _('New')
            used_name_for_lead_title = user_input_lines_lead_data["user_nickname"] or user_input_lines_lead_data["public_user_mail"]
            if used_name_for_lead_title:
                lead_title_start = _("%s's", used_name_for_lead_title)
        else:
            lead_title_start = _("%s's", username)

        lead_values = {
            'contact_name': username or user_input_lines_lead_data["user_nickname"],
            'description': user_input_lines_lead_data["description"],
            'name': f"{lead_title_start} {_('live session results')}" if self.is_session_answer else f"{lead_title_start} {_('survey results')}",
            'user_id': survey_responsible.id,
        }

        # Associate lead to the existing partner when known. Either because the person is connected
        # or because they received the survey with a unique token (by email for example).
        if self.partner_id:
            lead_values['partner_id'] = self.partner_id.id
        else:  # Save email field answer otherwise
            lead_values['email_from'] = user_input_lines_lead_data["public_user_mail"]

        return lead_values

    def _prepare_lead_values_from_user_input_lines(self):
        """ This method will prepare necessary lead values (in a dictionary), from the
            content of user input lines, to create a lead: it will format the lead
            description and get user's nickname and his email, if they're provided.
            To write the description (notes in CRM) in HTML format, there are 5 cases:
                - Suggested answers question: Question — Answer 1, Answer 3
                    (==> expected html line: <li>Question — Answer 1, Answer 3</li>)
                - Matrix question:  Question
                                    Line label 1 — Answer 1
                                    Line label 1 — Answer 3
                                    Line label 4 — Answer 2
                    (==> expected html line: <li>
                                                Question
                                                <br>&esmpLine label 1 — Answer 1
                                                <br>&esmpLine label 1 — Answer 3
                                                <br>&esmpLine label 4 — Answer 2
                                             </li>)
                - Long text question: Question
                                      Text line 1
                                      Text line 2
                                      Text line 3
                    (==> expected html line: <li>
                                                Question
                                                <br>&esmpText line 1
                                                <br>&esmpText line 2
                                                <br>&esmpText line 3
                                             </li>)
                - Other types: Question — Answer
                    (==> expected html line: <li>Question — Answer</li>)
                - Skipped question: Question — Skipped
                    (==> expected html line: <li>Question — <i>Skipped</i></li>)

            Note: "<br/>&emsp;" is used to get a line break with indentation.
        """
        self.ensure_one()

        answers_grouped_by_question = self.user_input_line_ids.grouped('question_id')
        html_input_lines = []
        user_nickname, public_user_mail = "", ""
        for question_id, input_lines in answers_grouped_by_question.items():
            answer_description, last_row_id = "", ""
            # Check if the main question is skipped but a comment was submitted
            if not all(input_line.skipped for input_line in input_lines):
                for answer_index, answer_id in enumerate(input_lines):
                    if not answer_id.skipped:
                        # Check if the question has a nickname recorded or an email answer
                        if question_id.question_type == "char_box":
                            if not user_nickname and question_id.save_as_nickname:
                                user_nickname = answer_id._get_answer_value()
                            if not public_user_mail and question_id.validation_email:
                                public_user_mail = answer_id._get_answer_value()

                        # Write description line
                        if question_id.question_type == "text_box":
                            answer_description = Markup("<br/>&emsp;%s" % escape(answer_id._get_answer_value()).replace('\n', Markup("<br/>&emsp;")))
                        elif question_id.question_type == "matrix":
                            row_id = answer_id.matrix_row_id
                            if row_id.display_name:
                                col_value = answer_id.suggested_answer_id.display_name
                                if last_row_id != row_id:
                                    last_row_id = row_id
                                    answer_description += Markup("<br/>&emsp;%s — %s" % (escape(row_id.display_name), escape(col_value)))
                                else:  # For multiple suggested answers
                                    answer_description += Markup(", %s" % escape(col_value))
                            else:  # Comment field
                                comment_answer = answer_id._get_answer_value()
                                answer_description += Markup("<br/>&emsp;%s — %s" % (_('Comment'), escape(comment_answer).replace('\n', Markup("<br/>&emsp;"))))
                        else:
                            answer = escape(str(answer_id._get_answer_value())).replace('\n', Markup("<br/>&emsp;"))
                            # For picture answers without label, we use the filename by the way
                            if answer_id.suggested_answer_id and not answer_id._get_answer_value():
                                answer = escape(answer_id.suggested_answer_id.value_image_filename)
                            answer_description += Markup("%s%s" % ((" — " if answer_index == 0 else ", "), answer))  # The "else" useful for multiple suggested answers
            else:
                answer_description = Markup("<i> — %s </i>" % _('Skipped'))

            questions_with_answers_description = Markup("<li>%s%s</li>" % (escape(question_id.title), answer_description))
            html_input_lines.append(questions_with_answers_description)

        description = Markup("%s:<ul>%s</ul>" % (_('Answers'), ''.join(html_input_lines)))
        return {
            'description': description,
            'user_nickname': user_nickname,
            'public_user_mail': public_user_mail,
        }

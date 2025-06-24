from odoo.addons.survey.tests import common
from odoo.tests.common import HttpCase


class TestCrmSurvey(common.TestSurveyCommon, HttpCase):
    """
    These tests will check:
    - 1st case: if connected user's inputs contains "Create lead" answers, then a lead is created successfully
    - 2nd case: if connected user's inputs not contain "Create lead" answers, a lead isn't created anymore
    - 3rd case: if not connected user's inputs contains "Create lead" answers, then a lead is created with his email answer
    """
    def _create_lead_qualification_survey(self, survey_type="survey"):
        # Create lead qualification survey
        survey = self.env['survey.survey'].with_user(self.survey_manager).create({
            'title': 'Questionnaire for the position of software developer',
            'survey_type': survey_type,
            'questions_layout': 'page_per_question',
            'access_mode': 'public',
            'users_login_required': False,
        })

        # Create questions
        q01 = self._add_question(
            None, 'How old are you?', 'simple_choice',
            sequence=1,
            constr_mandatory=False, survey_id=survey.id,
            labels=[
                {'value': '18-30'},
                {'value': '30-50'},
                {'value': '50+'},
            ])
        q01.suggested_answer_ids[2].is_create_lead = True

        q02 = self._add_question(
            None, 'What programming languages do you use on a daily basis?', 'multiple_choice',
            sequence=2,
            constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
            labels=[
                {'value': 'Assembly'},
                {'value': 'Java'},
                {'value': 'C'},
                {'value': 'Python'},
            ])
        q02.suggested_answer_ids[0].is_create_lead = True
        q02.suggested_answer_ids[2].is_create_lead = True

        q03 = self._add_question(
            None, 'Please add or verify your email address:', 'char_box',
            sequence=3,
            validation_email=True,
            constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=survey.id,
            )

        self.assertTrue(q01.is_lead_generating)
        self.assertTrue(q02.is_lead_generating)
        self.assertFalse(q03.is_lead_generating)

        return survey

    def test_survey_with_lead_generation_logged_in(self):
        # Step 1 : Connected access + lead generation
        survey = self._create_lead_qualification_survey(survey_type="custom")
        self.authenticate(self.survey_user.login, self.survey_user.login)

        # Start page
        self._access_start(survey)
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(user_inputs.survey_id.lead_count, 0)
        user_inputs.partner_id = self.survey_user.partner_id
        answer_token = user_inputs.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        question_ids = list(survey.question_ids)
        self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[2], self.survey_user.email, answer_token, csrf_token, 'submit')

        ### Check if the last created lead was from the survey
        self.assertEqual(user_inputs.survey_id.lead_count, 1)
        lead_created = user_inputs.survey_id.lead_ids
        self.assertEqual(lead_created.name, f"{self.survey_user.display_name}'s survey results")

        # Ensure that the result values are present in lead description
        description = lead_created.description
        for answer in user_inputs.user_input_line_ids:
            self.assertIn(answer._get_answer_value(), description)

        # Ensure contact, salesperson, medium, source, email and the contact name are rights
        self.assertEqual(lead_created.partner_id, self.survey_user.partner_id)
        self.assertFalse(lead_created.user_id.id)
        self.assertEqual(lead_created.medium_id.name, "Survey")
        self.assertEqual(lead_created.source_id.name, survey.title)
        self.assertEqual(lead_created.email_from, self.survey_user.email)
        self.assertEqual(lead_created.contact_name, self.survey_user.partner_id.name)

        # Ensure Odoobot created the lead
        for message in lead_created.message_ids:
            self.assertEqual(message.author_id.name, self.env.ref('base.user_root').name)

    def test_survey_without_lead_generation_logged_in(self):
        # Step 2 : Connected access + no lead generation
        survey = self._create_lead_qualification_survey("live_session")
        self.authenticate(self.survey_user.login, self.survey_user.login)

        # Start page
        self._access_start(survey)
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(user_inputs.survey_id.lead_count, 0)
        answer_token = user_inputs.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        question_ids = list(survey.question_ids)
        self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[1], question_ids[1].suggested_answer_ids.ids[3], answer_token, csrf_token)
        self._answer_question(question_ids[2], self.survey_user.email, answer_token, csrf_token, 'submit')

        ### Check if a lead was created
        self.assertEqual(user_inputs.survey_id.lead_count, 0)

    def test_survey_with_lead_generation_public(self):
        # Step 3 : Public access + lead generation
        # Before, add survey manager in a sales team
        sales_team = self.env['crm.team'].create({
            'name': 'Odoo Survey Team',
            'use_leads': True
        })
        sales_team.member_ids = [(4, self.survey_manager.id)]
        survey = self._create_lead_qualification_survey()
        self.authenticate(None, None)

        # Start page
        self._access_start(survey)
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(user_inputs.survey_id.lead_count, 0)
        answer_token = user_inputs.access_token

        # First page
        response = self._access_page(survey, answer_token)
        csrf_token = self._find_csrf_token(response.text)
        self._access_begin(survey, answer_token)

        # Answers
        question_ids = list(survey.question_ids)
        self._answer_question(question_ids[0], question_ids[0].suggested_answer_ids.ids[0], answer_token, csrf_token)
        self._answer_question(question_ids[1], [question_ids[1].suggested_answer_ids.ids[0], question_ids[1].suggested_answer_ids.ids[1]],
                                answer_token, csrf_token)
        self._answer_question(question_ids[2], "beautiful_address@example.com", answer_token, csrf_token, 'submit')

        ### Check if the last created lead was from the survey
        self.assertEqual(user_inputs.survey_id.lead_count, 1)
        lead_created = user_inputs.survey_id.lead_ids
        self.assertEqual(lead_created.name, "beautiful_address@example.com's survey results")

        # Ensure that the result values are present in lead description
        description = lead_created.description
        for answer in user_inputs.user_input_line_ids:
            self.assertIn(answer._get_answer_value(), description)

        # Ensure contact, salesperson, medium, source, email and contact name are rights
        self.assertFalse(lead_created.partner_id.id)  # Public user
        self.assertEqual(lead_created.user_id.id, survey.user_id.id)  # Survey created by a sales team person
        self.assertEqual(lead_created.medium_id.name, "Survey")
        self.assertEqual(lead_created.source_id.name, survey.title)
        self.assertEqual(lead_created.email_from, "beautiful_address@example.com")
        self.assertEqual('', lead_created.contact_name)

        # Ensure Odoobot created the lead
        for message in lead_created.message_ids:
            self.assertEqual(message.author_id.name, self.env.ref('base.user_root').name)

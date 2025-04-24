import itertools

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):
    def test_independent_attachment_delete(self):
        """Test access to delete an attachment"""
        # Subtest format: (user, token, result)
        denied_cases = itertools.product(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            (False, True),
            [False],
        )
        allowed_cases = itertools.product(self.user_admin, (False, True), [True])
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases))

    def test_attachment_delete_linked_to_public_thread(self):
        """Test access to delete an attachment associated with a public thread"""
        thread = self.env["mail.test.access.public"].create({"name": "Test"})
        # Subtest format: (user, token, result)
        denied_cases = itertools.product(
            (self.guest, self.user_portal, self.user_public),
            (False, True),
            [False],
        )
        allowed_cases = itertools.product(
            (self.user_admin, self.user_employee), (False, True), [True]
        )
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases), thread=thread)

    def test_attachment_delete_linked_to_non_accessible_thread(self):
        """Test access to delete an attachment associated with a non-accessible thread"""
        thread = self.env["mail.test.access.admin"].create({"name": "Test"})
        # Subtest format: (user, token, result)
        denied_cases = itertools.product(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            (False, True),
            [False],
        )
        allowed_cases = itertools.product(self.user_admin, (False, True), [True])
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases), thread=thread)

    def test_attachment_delete_linked_to_message(self):
        """Test access to delete an attachment associated with a message"""
        message = self.env["mail.message"].create({"body": "Test"})
        # Subtest format: (user, token, result, {"author": message author})
        tokens = (False, True)
        no_author_denied_cases = itertools.product(
            (self.guest, self.user_employee, self.user_portal, self.user_public), tokens, [False]
        )
        no_author_allowed_cases = itertools.product(self.user_admin, tokens, [True])
        subtests = itertools.chain(
            no_author_denied_cases,
            no_author_allowed_cases,
            iter(
                (
                    (self.guest, False, False, {"author": self.guest}),
                    (self.guest, True, False, {"author": self.guest}),
                    (self.user_admin, False, True, {"author": self.user_admin.partner_id}),
                    (self.user_admin, True, True, {"author": self.user_admin.partner_id}),
                    (self.user_employee, False, False, {"author": self.user_employee.partner_id}),
                    (self.user_employee, True, False, {"author": self.user_employee.partner_id}),
                    (self.user_portal, False, False, {"author": self.user_portal.partner_id}),
                    (self.user_portal, True, False, {"author": self.user_portal.partner_id}),
                )
            ),
        )
        self._execute_subtests_delete(subtests, message=message)

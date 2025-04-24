import itertools

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestPortalAttachmentController(MailControllerAttachmentCommon):

    def test_attachment_upload_portal(self):
        """Test access to upload an attachment on portal"""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        self._execute_subtests_upload(
            record,
            (
                (self.user_public, False),
                (self.user_public, True, token),
                (self.user_public, True, sign),
                (self.guest, False),
                (self.guest, True, token),
                (self.guest, True, sign),
                (self.user_portal, False),
                (self.user_portal, False, bad_token),
                (self.user_portal, False, bad_sign),
                (self.user_portal, True, token),
                (self.user_portal, True, sign),
                (self.user_employee, True),
                (self.user_employee, True, bad_token),
                (self.user_employee, True, bad_sign),
                (self.user_employee, True, token),
                (self.user_employee, True, sign),
                (self.user_admin, True),
                (self.user_admin, True, bad_token),
                (self.user_admin, True, bad_sign),
                (self.user_admin, True, token),
                (self.user_admin, True, sign),
            ),
        )

    def test_independent_attachment_delete_portal(self):
        """Test access to delete an attachment on portal"""
        # Subtest format: (user, token, result, {"route_kw": security params})
        record = self.env["mail.test.portal"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        not_allowed_users = (self.guest, self.user_employee, self.user_portal, self.user_public)
        allowed_users = (self.user_admin,)
        tokens = (False, True)
        route_kws = (
            {"route_kw": token},
            {"route_kw": sign},
            {"route_kw": bad_token},
            {"route_kw": bad_sign},
        )
        denied_cases = itertools.product(not_allowed_users, tokens, [False], route_kws)
        allowed_cases = itertools.product(allowed_users, tokens, [True], route_kws)
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases))

    def test_attachment_delete_portal_linked_to_thread(self):
        """Test access to delete an attachment on portal associated with a thread"""
        record = self.env["mail.test.portal"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        not_allowed_users = (self.guest, self.user_portal, self.user_public)
        allowed_users = (self.user_admin, self.user_employee)
        # Subtest format: (user, token, result, {"route_kw": security params})
        tokens = (False, True)
        route_kws = (
            {},
            {"route_kw": token},
            {"route_kw": sign},
            {"route_kw": bad_token},
            {"route_kw": bad_sign},
        )
        denied_cases = itertools.product(not_allowed_users, tokens, [False], route_kws)
        allowed_cases = itertools.product(allowed_users, tokens, [True], route_kws)
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases), thread=record)

    def get_delete_attachment_subtests(self, sign_token_params, different_result):
        token, bad_token, sign, bad_sign, doc_partner = sign_token_params
        # Subtest format: (user, token, result, {"author": message author, "route_kw": security params})
        portal_partner = self.user_portal.partner_id
        return (
            (self.user_portal, False, False, {"route_kw": token}),
            (self.user_portal, True, False, {"route_kw": token}),
            (self.user_portal, False, False, {"route_kw": sign}),
            (self.user_portal, True, False, {"route_kw": sign}),
            (self.user_portal, False, False, {"route_kw": bad_token}),
            (self.user_portal, True, False, {"route_kw": bad_token}),
            (self.user_portal, False, False, {"route_kw": bad_sign}),
            (self.user_portal, True, False, {"route_kw": bad_sign}),
            (self.user_portal, False, False, {"author": doc_partner, "route_kw": token}),
            (self.user_portal, True, False, {"author": doc_partner, "route_kw": token}),
            (self.user_portal, False, False, {"author": doc_partner, "route_kw": sign}),
            (self.user_portal, True, False, {"author": doc_partner, "route_kw": sign}),
            (self.user_portal, False, False, {"author": doc_partner, "route_kw": bad_token}),
            (self.user_portal, True, False, {"author": doc_partner, "route_kw": bad_token}),
            (self.user_portal, False, False, {"author": doc_partner, "route_kw": bad_sign}),
            (self.user_portal, True, False, {"author": doc_partner, "route_kw": bad_sign}),
            (self.user_portal, False, True, {"author": portal_partner, "route_kw": token}),
            (self.user_portal, True, True, {"author": portal_partner, "route_kw": token}),
            (self.user_portal, False, True, {"author": portal_partner, "route_kw": sign}),
            (self.user_portal, True, True, {"author": portal_partner, "route_kw": sign}),
            (self.user_portal, False, False, {"author": portal_partner, "route_kw": bad_token}),
            (self.user_portal, True, False, {"author": portal_partner, "route_kw": bad_token}),
            (self.user_portal, False, False, {"author": portal_partner, "route_kw": bad_sign}),
            (self.user_portal, True, False, {"author": portal_partner, "route_kw": bad_sign}),
            (self.user_public, False, False, {"route_kw": token}),
            (self.user_public, True, False, {"route_kw": token}),
            (self.user_public, False, False, {"route_kw": sign}),
            (self.user_public, True, False, {"route_kw": sign}),
            (self.user_public, False, False, {"route_kw": bad_token}),
            (self.user_public, True, False, {"route_kw": bad_token}),
            (self.user_public, False, False, {"route_kw": bad_sign}),
            (self.user_public, True, False, {"route_kw": bad_sign}),
            (self.user_public, False, different_result, {"author": doc_partner, "route_kw": token}),
            (self.user_public, True, different_result, {"author": doc_partner, "route_kw": token}),
            (self.user_public, False, True, {"author": doc_partner, "route_kw": sign}),
            (self.user_public, True, True, {"author": doc_partner, "route_kw": sign}),
            (self.user_public, False, False, {"author": doc_partner, "route_kw": bad_token}),
            (self.user_public, True, False, {"author": doc_partner, "route_kw": bad_token}),
            (self.user_public, False, False, {"author": doc_partner, "route_kw": bad_sign}),
            (self.user_public, True, False, {"author": doc_partner, "route_kw": bad_sign}),
        )

    def test_attachment_delete_portal_no_partner(self):
        """Test access to delete an attachment on a portal document without partner which is
        associated with a message"""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        message = self.env["mail.message"].create({"model": record._name, "res_id": record.id})
        sign_token_params = self._get_sign_token_params(record)
        self._execute_subtests_delete(
            self.get_delete_attachment_subtests(sign_token_params, False),
            message=message,
        )

    def test_attachment_delete_portal_assigned_partner(self):
        """Test access to delete an attachment on a portal document with a partner which is
        associated with a message"""
        record = self.env["mail.test.portal"].create({"name": "Test"})
        sign_token_params = self._get_sign_token_params(record)
        record.partner_id = sign_token_params[-1]
        message = self.env["mail.message"].create({"model": record._name, "res_id": record.id})
        self._execute_subtests_delete(
            self.get_delete_attachment_subtests(sign_token_params, True),
            message=message,
        )

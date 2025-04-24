# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestDiscussAttachmentController(MailControllerAttachmentCommon):
    def test_attachment_allowed_upload_public_channel(self):
        """Test access to upload an attachment on an allowed upload public channel"""
        channel = self.env["discuss.channel"].create(
            {"group_public_id": None, "name": "public channel"}
        )
        channel.add_members(guest_ids=[self.guest.id])
        channel.env.context = {**channel.env.context, "guest": self.guest}
        self._execute_subtests_upload(
            channel,
            (
                (self.guest, True),
                (self.user_admin, True),
                (self.user_employee, True),
                (self.user_portal, True),
                (self.user_public, True),
            ),
        )

    def test_attachment_delete_linked_to_public_channel(self):
        """Test access to delete an attachment associated with a public channel"""
        channel = self.env["discuss.channel"].create({"name": "public channel"})
        denied_cases = itertools.product(
            (self.guest, self.user_portal, self.user_public),
            (False, True),
            [False],
        )
        allowed_cases = itertools.product(
            (self.user_admin, self.user_employee),
            (False, True),
            [True],
        )
        # Subtest format: (user, token, result)
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases), thread=channel)

    def test_attachment_delete_linked_to_private_channel(self):
        """Test access to delete an attachment associated with a private channel"""
        channel = self.env["discuss.channel"].create(
            {"name": "Private Channel", "channel_type": "group"}
        )
        denied_cases = itertools.product(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            (False, True),
            [False],
        )
        allowed_cases = itertools.product(self.user_admin, (False, True), [True])
        # Subtest format: (user, token, result)
        self._execute_subtests_delete(itertools.chain(denied_cases, allowed_cases), thread=channel)

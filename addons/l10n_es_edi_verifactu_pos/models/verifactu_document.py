<<<<<<< HEAD
import contextlib
=======
import logging
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c

from odoo import fields, models
from odoo.exceptions import UserError

<<<<<<< HEAD
=======
_logger = logging.getLogger(__name__)

>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c

class L10nEsEdiVerifactuDocument(models.Model):
    _inherit = 'l10n_es_edi_verifactu.document'

    pos_order_id = fields.Many2one(
        string="PoS Order",
        comodel_name='pos.order',
        readonly=True,
    )

    def _post_send_hook(self, info):
        super()._post_send_hook(info)
        for document in self:
            order = document.pos_order_id
            if order.l10n_es_edi_verifactu_state == 'cancelled' and order.state != 'cancel':
<<<<<<< HEAD
                with contextlib.suppress(UserError):
                    order.action_pos_order_cancel()
=======
                try:
                    order.button_cancel()
                except UserError as error:
                    _logger.error("Error while canceling order %(name)s (id %(record_id)s) after Veri*Factu cancellation:\n%(error)s",
                                  record_id=order.id, name=order.name, error=error)
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c

# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from odoo import _, fields, models, api
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('qfpay', 'QFPay')]

    qfpay_terminal_ip_address = fields.Char('QFPay Terminal IP Address')
    qfpay_pos_key = fields.Char('QFPay POS Key', groups='base.group_erp_manager')
    qfpay_aes_iv = fields.Char('QFPay AES IV', groups='base.group_erp_manager')
    qfpay_payment_type = fields.Selection([
        ('card_payment', 'Visa/Mastercard'),
        ('wx', 'WeChat Pay'),
        ('alipay', 'Alipay'),
        ('payme', 'PayMe'),
        ('union', 'UnionPay QuickPass'),
        ('fps', 'FPS'),
        ('octopus', 'Octopus'),
        ('unionpay_card', 'Unionpay Card'),
        ('amex_card', 'American Express Card'),
    ], 'QFPay Payment Type', copy=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['qfpay_terminal_ip_address', 'qfpay_payment_type']
        return params

    @api.constrains('use_payment_terminal')
    def _check_qfpay_terminal(self):
        if any(record.use_payment_terminal == 'qfpay' and record.company_id.currency_id.name != 'HKD' for record in self):
            raise UserError(_('QFPay is only valid for HKD Currency'))

    def qfpay_sign_request(self, payload):
        self.ensure_one()
        self.check_access('read')

        if self.use_payment_terminal != 'qfpay':
            raise UserError(_('This method can only be used with QFPay payment terminal.'))

        key = self.sudo().qfpay_pos_key
        aes_iv = self.sudo().qfpay_aes_iv

        if not key or not aes_iv:
            raise UserError(_('Please set the QFPay POS Key and AES IV in the payment method.'))

        # Sort the payload items and format
        payload_items = sorted((k, '' if v is None else v) for k, v in payload.items())
        formated_payload = ','.join(f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}" for k, v in payload_items)
        formated_payload = '{' + formated_payload + '}'

        # Generate Digest
        md5 = hashlib.md5()
        md5.update((formated_payload + key).encode('utf-8'))
        digest = md5.hexdigest().upper()

        # Prepare the payload to encrypt
        payload_to_encrypt = "{content:" + formated_payload + ", digest:'" + digest + "'}"

        # Encrypt the payload
        backend = default_backend()
        cipher = Cipher(algorithms.AES(key.encode('utf-8')), modes.CBC(aes_iv.encode('utf-8')), backend=backend)
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(payload_to_encrypt.encode('utf-8')) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode('utf-8')

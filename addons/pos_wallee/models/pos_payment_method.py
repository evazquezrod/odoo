from odoo import _, fields, models
from odoo.exceptions import UserError

from .wallee_pos_request import call_wallee_web_service_api

# TRANSACTION_STATES = ['create', 'pending', 'confirmed', 'processing', 'failed', 'authorized', 'completed', 'fulfill', 'decline', 'voided']
# Create	The create state is set during the creation of the transaction.
# Pending	The transaction is created but it is not confirmed by the merchant system.
# Confirmed	The transaction is created and confirmed however the processing has not yet started.
# Processing	The transaction is processing.
# Failed	The transaction authorization failed.
# Authorized	The transaction is authorized.
# Completed	The transaction is completed.
# Fulfill	The transaction is ready to be delivered.
# Decline	The goods or services should not be delivered.
# Voided	The authorization is voided and hence no money is transferred.


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    wallee_userid = fields.Char(string="Wallee User ID")
    wallee_spaceid = fields.Char(string="Wallee Space ID")
    # auth_key / app_key / application_user_key / api_key
    wallee_auth_key = fields.Char(string="Wallee Authentication Key", help="Generated when an application user is created in Wallee")
    wallee_terminalid = fields.Char(string="Wallee Terminal ID", help="It would be of 3xxx xxxx pattern, and is also printed on receipt", copy=False)
    wallee_terminal_identifier = fields.Char(string="Wallee Terminal Identifier", copy=False)
    # HTTP GET /api/transaction/fetch-payment-methods?spaceId={wallee_spaceid}&id={wallee_transactionid}&integrationMode=terminal
    # wallee_allowed_payment_modes = fields.Selection(selection=[
    #     ('all', "All"),
    #     ('card', "Card"),
    # ], string="Allowed Payment Modes", default='all')
    wallee_test_mode = fields.Boolean(string="Wallee Test Mode", help="Turn it on when in Test Mode")

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('wallee', "Wallee")]

    # currency, transactionId
    # wallee_make_payment_request
    def wallee_create_transaction(self, amount, referenceId, uuid, product_ids_joined="1", product_names_joined="PRODUCT_NAME", product_quantities_joined=1):
        if not all([self.wallee_userid, self.wallee_spaceid, self.wallee_auth_key]) or not any([self.wallee_terminalid, self.wallee_terminal_identifier]):
            raise UserError(_("Please configure wallee credentials in the payment method."))

        ####################################################################################################
        # Transaction Create
        # https://app-wallee.com/en/doc/api/model/transaction
        # https://app-wallee.com/doc/api/web-service#_transaction
        # https://app-wallee.com/en-us/doc/api/web-service#_transaction_create
        # https://app-wallee.com/en-us/doc/api/web-service#transaction-service--create
        # https://app-wallee.com/api/client/transaction-service--create
        ####################################################################################################
        path = "/transaction/create"
        params = {
            'spaceId': self.wallee_spaceid,
        }
        payload = {
            'currency': self.company_id.currency_id.name,
            'merchantReference': referenceId,
            'lineItems': [
                {
                    'amountIncludingTax': amount,
                    'name': product_names_joined,
                    'quantity': product_quantities_joined,
                    # SHIPPING, DISCOUNT, FEE, PRODUCT, TIP
                    'type': "PRODUCT",
                    'uniqueId': product_ids_joined,
                },
            ],
            'environment': "PREVIEW" if self.wallee_test_mode else "LIVE",
            # USE_CONFIGURATION, FORCE_TEST_ENVIRONMENT, FORCE_PRODUCTION_ENVIRONMENT
            'environmentSelectionStrategy': "FORCE_TEST_ENVIRONMENT" if self.wallee_test_mode else "FORCE_PRODUCTION_ENVIRONMENT",
            # 'customerEmailAddress': ???
            # 'invoiceMerchantReference': ???
        }
        response = call_wallee_web_service_api(self.wallee_userid, self.wallee_auth_key, "POST", path, params, payload)
        # data = response.get('data')
        # if response.get('status_code') == 200:
        if 'id' in response:
            return {'transaction_id': response.get('id')}
        # elif 'error' in response:
        # elif response.get('error'):
            # return {'error': response.get('error')}
        # elif response.get('status_code') in [442, 542] or data.get('message') or (data.get('type') and "ERROR" in data.get('type')):
            # return {'error': f"{data.get('type')} - {data.get('message')}"}
        return {'error': response.get('error', "Unknown Error")}

    # wallee_fetch_payment_status
    def wallee_perform_transaction(self, transactionId):
        if not all([self.wallee_userid, self.wallee_spaceid, self.wallee_auth_key]) or not any([self.wallee_terminalid, self.wallee_terminal_identifier]):
            raise UserError(_("Please configure wallee credentials in the payment method."))
        if not transactionId:
            raise UserError(_("Transaction ID is required to fetch payment status."))

        ####################################################################################################
        # Payment Terminal Till Service - Perform Transaction using Terminal ID
        # https://app-wallee.com/en-us/doc/api/web-service#payment-terminal-till-service--perform-transaction
        # https://app-wallee.com/api/client/payment-terminal-till-service--perform-transaction
        ####################################################################################################
        # Payment Terminal Till Service - Perform Transaction using Terminal Identifier
        # https://app-wallee.com/en-us/doc/api/web-service#payment-terminal-till-service--perform-transaction-by-identifier
        # https://app-wallee.com/api/client/payment-terminal-till-service--perform-transaction-by-identifier
        ####################################################################################################
        path = "/payment-terminal-till/perform-transaction"
        params = {
            'spaceId': self.wallee_spaceid,
            'transactionId': transactionId,
        }
        if self.wallee_terminalid:
            params['terminalId'] = self.wallee_terminalid
        elif self.wallee_terminal_identifier:
            path += "-by-identifier"
            params['terminalIdentifier'] = self.wallee_terminal_identifier
        # 80 is the maximum seconds while wallee tries to process the transaction before returning a 543 status code
        # than we need to call the API again with the exact same parameters
        response = call_wallee_web_service_api(self.wallee_userid, self.wallee_auth_key, "GET", path, params, read_timeout=90)
        # data = response.get('data')
        if response.get('status_code') == 200:
        # if 'id' in response:
            return {
                'transaction_id': transactionId,
                'transaction_state': response.get('state'),
            }
        elif response.get('status_code') == 543:
            return {'request_timeout': True}
        return {'error': response.get('error', "Unknown Error")}

        # elif response.get('status_code') in [409, 442, 542] or data.get('message') or (data.get('type') and data.get('type').find("ERROR") != -1):
            # return {'error': f"{data.get('type', 'Unknown Error')} - {data.get('message', 'Unknown Error')}"}
            # return {'error': data.get('message', 'Unknown Error')}






        ####################################################################################################
        ####################################################################################################
        # path = f"/transaction/read?spaceId={self.wallee_spaceid}&id={transaction_id}"
        # payload = {
        # }
        # response = call_wallee_web_service_api(payment_method=self, http_method="", path=path, payload=payload)

    def wallee_cancel_payment_request(self, transactionId):
        if not all([self.wallee_userid, self.wallee_spaceid, self.wallee_auth_key]) or not any([self.wallee_terminalid, self.wallee_terminal_identifier]):
            raise UserError(_("Please configure wallee credentials in the payment method."))
        ####################################################################################################
        # https://app-wallee.com/en-us/doc/api/web-service#transaction-void-service--void-online
        ####################################################################################################
        path = "/transaction-void/voidOnline"
        params = {
            'spaceId': self.wallee_spaceid,
            'id': transactionId,
        }
        response = call_wallee_web_service_api(self.wallee_userid, self.wallee_auth_key, "POST", path, params)
        # data = response.get('data')
        # elif response.get('status_code') in [442, 542]:
        #     return {'error': f"{data.get('type')} - {data.get('message')}"}
        if response.get('status_code') == 200:
            return {
                'transaction_id': response.get('id'),
                'transaction_state': response.get('state'),
            }
        return {'error': response.get('error', "Unknown Error")}

    # wallee_make_refund_request
    def wallee_send_refund_request(self, transactionId, amount, uuid):
        if not all([self.wallee_userid, self.wallee_spaceid, self.wallee_auth_key]) or not any([self.wallee_terminalid, self.wallee_terminal_identifier]):
            raise UserError(_("Please configure wallee credentials in the payment method."))
        if not transactionId:
            raise UserError(_("Transaction ID is required for refund."))

        ####################################################################################################
        # https://app-wallee.com/en-us/doc/api/model/refund
        # https://app-wallee.com/en-us/doc/api/web-service#_refund
        # https://app-wallee.com/doc/api/web-service#_refund_create
        # https://app-wallee.com/doc/api/web-service#refund-service--refund
        # https://app-wallee.com/api/client/refund-service--refund
        ####################################################################################################
        path = "/refund/refund"
        params = {
            'spaceId': self.wallee_spaceid,
        }
        payload = {
            # id of pos.payment or account.move.line. if request with same externalId is made, it will be ignored by walllee
            'externalId': uuid,
            # Eg: RINV/2025/0001
            'merchantReference': "???",
            'transaction': {
                'id': transactionId,
            },
            'type': "MERCHANT_INITIATED_ONLINE",
        }
        if amount:
            payload.update({'amount': amount})
        response = call_wallee_web_service_api(self.wallee_userid, self.wallee_auth_key, "POST", path, params, payload)
        # response.ok
        if 'status_code' in response and response.get('status_code') == 200:
            return {
                'refund_id': response.get('id'),
                'refund_state': response.get('state'),
            }
        return {'error': response.get('error', "Unknown Error")}

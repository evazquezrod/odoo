import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";


export class PaymentQFpay extends PaymentInterface {
    static terminalInstances = new Map();

    setup() {
        super.setup(...arguments);
        this.orm = this.env.services.orm;
        this.domain = `http://${this.payment_method_id.qfpay_terminal_ip_address}:9001`;
        this.dialog = this.env.services.dialog;
        this.paymentLineResolvers = {};
    }

    async sendPaymentRequest(uuid) {
        await super.sendPaymentRequest(...arguments);
        const order = this.pos.getOrder()
        const line = order.getSelectedPaymentline();

        let response;
        if (line.amount < 0) {
            const originalPayment = order.refunded_order_id.payment_ids.find((l) => l.payment_method_id.id === this.payment_method_id.id);
            if (!originalPayment) {
                this._showError(_t(`No payment with QFPay ${this.payment_method_id.display_name} found for this order.`));
                return Promise.resolve(false);
            }
            if (this._isCreditCardPayment() && originalPayment.amount !== -line.amount) {
                this._showError(_t("Credit card payments refund must be for the full amount."));
                return Promise.resolve(false);
            }
            if (originalPayment.amount < -line.amount) {
                this._showError(_t("Refund amount cannot be greater than the original payment amount."));
                return Promise.resolve(false);
            }
            response = await this._make_qfpay_request('cancel', {
                func_type: 1002,
                orderId: originalPayment.transaction_id,
                refund_amount: (-line.amount).toFixed(2),
            });
        } else {
            response = await this._make_qfpay_request('trade', {
                func_type: 1001,
                amt: line.amount,
                channel: this.payment_method_id.qfpay_payment_type,
                out_trade_no: order.pos_reference + "-" + this._generate_terminal_request_id(),
            });
        }

        if (!response) {
            return Promise.resolve(false);
        }

        // if credit card payment, we need to handle the card details
        if (this._isCreditCardPayment()) {
            line.card_brand = response.cardscheme
            line.card_type = response.cardType;
            line.card_no = response.cardNo;
        }
        line.payment_ref_no = response.chnlsn;
        line.transaction_id = response.syssn;
        return Promise.resolve(true);
    }

    async sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        return await this._make_qfpay_request('cancel_request', {
            func_type: 5001,
        });
    }

    _generate_terminal_request_id() {
        this.terminalRequestId = Math.random().toString(36).substring(2, 12);
        return this.terminalRequestId;
    }

    async _make_qfpay_request(endpoint, payload) {
        const signedPayload = await this.orm.call("pos.payment.method", "qfpay_sign_request", [
            this.payment_method_id.id,
            payload,
        ]);
        const result = await fetch(
            `${this.domain}/api/pos/${endpoint}`,
            {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(signedPayload),
            }
        );
        const response = await result.json();

        if (response.respcd !== "6000") {
            if (response.respcd !== "6001") {
                this._showError(`Error Code: ${response.respcd}\nError Message: ${response.resperr || response.respmsg || _t("Unknown error occurred")}`);
            }
            return false;
        }
        console.log("QFPay Response:", response);
        return response.data ? JSON.parse(response.data) : true;
        // {'data': '{"accountId":null,"address":"HK","batchNo":"250703","busicd":"802808","cardNo":"541375******6830","cardType":"MASTERCARD","cardscheme":"MASTERCARD","chnlsn":"2025070375830316","clisn":"030800","mchntnm":"Odoo HK Limited","octopusOrderId":null,"octopus_no":null,"octopus_order_status":null,"octopus_paydtm":null,"out_trade_no":"456799999999","paydtm":"2025-07-03 14:33:23","paymentMethod":"Visa / Mastercard","paymentType":"SALES","remark":null,"reserr":"trade success","resmsg":"AUTHORISED","respcd":"0000","rv":null,"storeId":"1000035753","sysdtm":"2025-07-03 14:33:22","syssn":"20250703155400020061880690","terminalId":"253SCASG9109","traceNo":"880690","txamt":"100","txcurrcd":"344","udid":"869071059175183","userid":"1000035753"}', 'respcd': '6000', 'resperr': 'trade success', 'respmsg': 'AUTHORISED'}
        // {'data': '{"accountId":null,"address":"HK","batchNo":null,"busicd":"800108","cardNo":null,"cardType":null,"cardscheme":null,"chnlsn":"2025070399401001260274915671","clisn":"056686","mchntnm":"Odoo HK Limited","octopusOrderId":null,"octopus_no":null,"octopus_order_status":null,"octopus_paydtm":null,"out_trade_no":"456799999998","paydtm":"2025-07-03 21:44:46","paymentMethod":"Alipay","paymentType":"Sales","remark":null,"reserr":"交易成功","resmsg":"","respcd":"0000","rv":null,"storeId":"1000035753","sysdtm":"2025-07-03 21:44:46","syssn":"20250703155400020061915158","terminalId":"253SCASG9109","traceNo":null,"txamt":"100","txcurrcd":"344","udid":null,"userid":"1000035753"}', 'respcd': '6000', 'resperr': '交易成功', 'respmsg': ''}
    }

    handleSuccessResponse(line, notification) {
        const isCreditCard = Boolean(notification.refNo);
        line.payment_method_payment_mode = kpay.PAYMENT_METHODS_MAPPING[notification.payMethod];
        if (isCreditCard) {
            line.transaction_id = notification.refNo;
        } else {
            line.transaction_id = notification.transactionNo;

        }
        this.terminalRequestId = 0;
    }

    _isCreditCardPayment() {
        return ["card_payment", "unionpay_card", "amex_card"].includes(this.payment_method_id.qfpay_payment_type);
    }

    _showError(msg, title) {
        if (!title) {
            title = _t("QFPay Error");
        }
        this.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("qfpay", PaymentQFpay);

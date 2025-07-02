import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
// import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
// import { offlineErrorHandler, handleRPCError } from "@point_of_sale/app/errors/error_handlers";

// const REQUEST_TIMEOUT_MS = 10000;

/* payment_states: pending waiting waitingCard waitingCapture retry force_done done reversing reversed */

// ways to fetch payment status
// 1. long polling
// 2. web socket directly from web client

export class PaymentWallee extends PaymentInterface {
    setup() {
        super.setup(...arguments);
    }

    send_payment_request(uuid) {
        // console.log("uuid:", uuid);
        super.send_payment_request(uuid);

        const order = this.pos.get_order();
        const line = order.get_selected_paymentline();
        // console.log(order, line);
        if (line.amount < 0 && !order._isRefundOrder()) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            // return Promise.resolve();
            return false;
        }

        /* unique random ID to identify request/response pairs */
        // this.most_recent_service_id = Math.floor(Math.random() * Math.pow(2, 64)).toString().substring(0, 10);
        // const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        // const referenceId = referencePrefix.concat(Math.floor(Math.random() * 1000000000));
        const orderId = order.pos_reference.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        line.payment_ref_no = referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", "");
        // console.log("payment_ref_no: ", line.payment_ref_no);

        if (order._isRefundOrder()) {
            return this._make_wallee_refund_request(uuid, line);
        } else {
            return this._make_wallee_payment_request(uuid, line);
        }
    }

    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);

        // const line = this._pending_wallee_line();
        // const line = order.get_selected_paymentline();
        const line = this.payment_ids.find((line) => line.uuid === uuid);
        let data = [line.transaction_id];
        return this._call_wallee(data, "wallee_cancel_payment_request").then((response) => {
            if (!response || response?.error) {
                this._show_error(_t("Wallee payment cancellation request failed: %s", response?.error));
                return false;
            }
            line.set_payment_status("retry");
            return true;
        });
    }

    _pending_wallee_line() {
        // finds with line.uuid
        // const line = this.pos.get_order().get_selected_paymentline();
        // matches wallee payment method
        return this.pos.getPendingPaymentLine("wallee");
    }

    _call_wallee(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [
                [this.payment_method_id.id],
                ...data,
            ])
            .catch((error) => {
                // handle timeout
                const line = this._pending_wallee_line();
                if (line) {
                    line.set_payment_status("retry");
                }
                this._show_error(_t(
                    "Could not connect to the Odoo server, please check your internet connection and try again."
                ));
                // prevent subsequent onFullFilled's from being called
                return Promise.reject(error);
                // return false;
            });
    }

    async _make_wallee_payment_request(uuid, line) {
        // _name = "pos.payment" model of line
        // "line.uuid" is same as "uuid"
        // line.payment_status
        // line.id // pos.payment_5

        // stop any request that is in progress for fetching payment status
        // && line.payment_status in ["waitingCard", "waiting", "retry"]) {
        if (!line.transaction_id) {
            // currency: this.pos.currency.name,
            // product_ids_concatenated: line.product_id.id,
            // product_names_concatenated: line.name,
            line.set_payment_status("waitingCapture");

            const data = [line.amount, line.payment_ref_no, uuid]
            const response = await this._call_wallee(data, "wallee_create_transaction")
            if (!response || response.error || !response.transaction_id) {
                this._show_error(_t(response?.error), _t("Wallee Payment Error"));
                // line.set_payment_status("retry");
                return false;
            }
            line.transaction_id = response.transaction_id;
        }
        return this._fetch_wallee_payment_status(uuid, line);
    }

    _make_wallee_refund_request(uuid, line) {
        // const line = this.pos.get_order().get_selected_paymentline();
        line.set_payment_status("waitingCard");
        // console.log("Refund ------------------------", line)
        const data = [
            line.transaction_id,
            Math.abs(line.amount),
            // merchantReference: line?.uiState.merchantReference,
            // externalId: line.payment_ref_no,
            uuid,
        ]
        return this._call_wallee(data, "wallee_make_refund_request").then((data) => {
            // console.log("refund response: ", data);
            if (data.error) {
                line.set_payment_status("retry");
                this._show_error(_t("Wallee refund request failed."));
                return false;
            }
            line.set_payment_status("done");
            // where to store data.refund_id ???
            return true;
        })
    }

    /* Long polling - This method calls wallee to perform payment transaction until it gets a successful response */
    async _fetch_wallee_payment_status(uuid, line) {
        line.set_payment_status("waitingCard");

        const data = [line.transaction_id]
        let response = await this._call_wallee(data, "wallee_perform_transaction")
        // let line = this._pending_wallee_line();
        // if (!line) {
            // return false;
        // }
        if (!response || response.error) {
            this._show_error(_t(response?.error), _t("Wallee Payment Error"));
            line.set_payment_status("retry");
            return false;
        } else if (response.request_timeout) {
            // payment is being processed, request again to fetch status
            return this._fetch_wallee_payment_status(uuid, response.transaction_id);
        } else if (response.transaction_state === "COMPLETED") {
            line.set_payment_status("done");
            return true;
        }
        line.set_payment_status("retry");
        return false;
    }

    _show_error(message, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Wallee Error"),
            body: message,
        });
    }

    // _make_wallee_payment_request() {}
    // _make_wallee_refund_request() {}
    // _make_wallee_cancel_request() {}
    // _handle_wallee_payment_response() {}
    // _handle_wallee_refund_response() {}
    // _handle_wallee_cancel_response() {}
}

register_payment_method("wallee", PaymentWallee);

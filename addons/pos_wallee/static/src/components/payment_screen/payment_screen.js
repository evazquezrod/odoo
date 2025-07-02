import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(async () => {
            const pendingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === "wallee" &&
                    !paymentLine.is_done() &&
                    paymentLine.get_payment_status() !== "pending" &&
                    !this.currentOrder._isRefundOrder()
            );
            if (pendingPaymentLine) {
                console.log("Wallee payment screen: ", pendingPaymentLine);
                const res =
                    await pendingPaymentLine.payment_method_id.payment_terminal._fetch_wallee_payment_status();
                // if (res?.transaction.state in ["AUTHORIZED", "COMPLETED"]) {
                //     pendingPaymentLine.set_payment_status("done");
                // } else {
                //     pendingPaymentLine.set_payment_status("force_done");
                // }
            }
        });
    },
});

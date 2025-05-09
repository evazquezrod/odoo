import { EpsonPrinter } from "@pos_epson_printer/app/utils/payment/epson_printer";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { patch } from "@web/core/utils/patch";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);
        if (!this.config.epson_printer_ip || !this.config.other_devices) {
            return;
        }
        this.printer.setPrinter(
            new EpsonPrinter({
                ip: this.config.epson_printer_ip,
            })
        );
    },
    createPrinter(printer) {
        if (printer.printer_type === "esc_pos_printer") {
            return new EpsonPrinter({ ip: printer.epson_printer_ip });
        }
        return super.createPrinter(...arguments);
    },
});

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosPrinter } from "@pos_printer/app/utils/pos_printer";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    afterProcessServerData() {
        var self = this;
        return super.afterProcessServerData(...arguments).then(function () {
            if (self.config.network_printer && self.config.nw_printer_ip) {
                self.hardwareProxy.printer = new PosPrinter({
                    nw_printer_ip: self.config.nw_printer_ip,
                    device_ip: self.config.device_ip,
                });
            }
        });
    },
    createPrinter(config) {
        if (config.printer_type === "esc_pos_printer") {
            return new PosPrinter({
                nw_printer_ip: config.nw_printer_ip,
                device_ip: config.device_ip,
            });
        } else {
            return super.createPrinter(...arguments);
        }
    },
});

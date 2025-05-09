import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PosPrinter } from "@pos_printer/app/utils/pos_printer";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    afterProcessServerData() {
        var self = this;
        return super.afterProcessServerData(...arguments).then(function () {
            if (self.config.other_devices && self.config.printer_ip) {
                self.hardwareProxy.printer = new PosPrinter({ ip: self.config.printer_ip });
            }
        });
    },
    createPrinter(config) {
        if (config.printer_type === "esc_pos_printer") {
            return new PosPrinter({ ip: config.printer_ip });
        } else {
            return super.createPrinter(...arguments);
        }
    },
});

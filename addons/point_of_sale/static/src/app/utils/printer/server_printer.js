import { rpc } from "@web/core/network/rpc";

import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

/**
 * Printer that polls a backend route for new print requests.
 * Epson: "Server Direct Print" / https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
 */
export class ServerPrinter extends BasePrinter {

    setup({ orm, posConfigId }) {
        debugger;
        this.orm = orm;
        this.posConfigId = posConfigId;
        super.setup(...arguments);
    }

    sendAction(receipt) {
        return rpc(`/point_of_sale/server_print/${this.posConfigId}/add_receipt_to_print_queue`, {
            pos_config_id: this.posConfigId,
            receipt_to_print: receipt
        })
    }

    /**
     * @override
     */
    sendPrintingJob(img) {
        debugger;
        return this.sendAction({ receipt: img });
    }
}

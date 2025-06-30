/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    _compute_qr_code_field(tag, field) {
        if (tag === 3) {
            if (field !== "03/07/2025, 13:15:17") {
                throw new Error(
                    `Expected "03/07/2025, 13:15:17" but got "${field}". It should take the timezone into account.`
                );
            }
        }
        return [];
    },
});

registry.category("web_tour.tours").add("test_sa_qr_in_right_timezone", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Test that the value given to the QR code contains the right timezone",
                trigger: "body",
                run: function () {
                    posmodel
                        .get_order()
                        .compute_sa_qr_code(
                            "SA Company",
                            "123456789012345",
                            "2025-03-07T10:15:17",
                            100.0,
                            0
                        );
                },
            },
        ].flat(),
});

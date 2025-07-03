import { test, describe, expect } from "@odoo/hoot";
import { getService, makeMockEnv } from "@web/../tests/web_test_helpers";

describe("pos.order", () => {
    odoo.pos_session_id = 1;

    test("uiState", async () => {
        await makeMockEnv();

        const store = getService("pos");
        const order = store.addNewOrder();

        expect(order.uiState).toEqual({
            unmerge: {},
            lastPrint: false,
            lineToRefund: {},
            displayed: true,
            booked: false,
            screen_data: {},
            selected_orderline_uuid: undefined,
            selected_paymentline_uuid: undefined,
            locked: false,
            TipScreen: {
                inputTipAmount: "",
            },
        });
    });

    test("totalQuantity", async () => {
        await makeMockEnv();

        const store = getService("pos");
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);
        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 3,
            },
            order
        );
        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 2,
            },
            order
        );
        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
            },
            order
        );

        expect(order.totalQuantity).toBe(6);
    });

    test("setPreset", async () => {
        await makeMockEnv();

        const store = getService("pos");
        const order = store.addNewOrder();

        expect(order.totalQuantity).toBe(6);
    });
});

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { StockValuationReport } from "@stock_account/stock_valuation/stock_valuation_report";


patch(StockValuationReport.prototype, {
    defineInitialState() {
        const initialState = super.defineInitialState();
        initialState.displayNotInvoicedDeliveredGoods = false;
        return initialState;
    },

    async defineData() {
        await super.defineData();
        this.saleOrderIds = this.data.not_invoiced_delivered_goods.lines.map((line) => line.id);
    },

    // Getters -----------------------------------------------------------------
    get notInvoicedDeliveredValuation() {
        return this.formatMonetary(this.data.not_invoiced_delivered_goods.total);
    },

    // On Click Methods --------------------------------------------------------
    openSaleOrder(line=false) {
        const action = {
            type: "ir.actions.act_window",
            name: _t("Sale Orders"),
            res_model: "sale.order",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        }
        if (line) {
            action.views = [[false, "form"]],
            action.res_id = line.id;
        } else {
            action.domain = [["id", "in", this.saleOrderIds]];
        }
        return this.actionService.doAction(action);
    },

    toggleNotInvoicedDeliveredGoodsFold() {
        this.state.displayNotInvoicedDeliveredGoods = !this.state.displayNotInvoicedDeliveredGoods;
    }
});
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, onWillStart, useChildSubEnv, useState } from "@odoo/owl";

import { StockValuationReportController } from "../stock_valuation/controller"
import { StockValuationReportFilters } from "../stock_valuation/filters/filters"
import { StockValuationReportLine } from "../stock_valuation/line/line"


export class StockValuationReport extends Component {
    static template = "stock_account.StockValuationReport";
    static props = { ...standardActionServiceProps };
    static components = {
        ControlPanel,
        StockValuationReportFilters,
        StockValuationReportLine,
    };

    setup() {
        this.controller = useState(new StockValuationReportController(this.props.action));
        this.state = useState(this.defineInitialState())
        this.data = {};
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            await this.defineData();
        })

        useChildSubEnv({
            openStockReport: this.openStockReport.bind(this),
            formatMonetary: this.formatMonetary.bind(this),
        });
    }

    defineInitialState() {
        return { displayInventoryValuationLine: false };
    }

    async defineData() {
        await this.controller.load(this.env);
        const res = await this.orm.call('stock_account.stock.valuation.report', "get_report_values");
        this.data = res.data;
    }

    formatMonetary(value) {
        return formatMonetary(value, {
            currencyId: this.data.currency_id,
        });
    }

    // Getters -----------------------------------------------------------------
    get inventoryValuation() {
        return formatMonetary(this.data.inventory_valuation.total, {
            currencyId: this.data.currency_id,
        });
    }

    get accountingStockValuation() {
        return this.formatMonetary(this.data.accounting_stock_valuation);
    }

    get stockInitial() {
        return this.formatMonetary(this.data.stock_initial);
    }

    get stockVariation() {
        return this.formatMonetary(this.data.stock_variation);
    }

    // On Click Methods --------------------------------------------------------
    openStockReport(line=false) {
        const additionalContext = {};
        if (line) {
            additionalContext.search_default_name = line.name;
        }
        return this.actionService.doAction(
            "stock.action_product_stock_view",
            { additionalContext }
        );
    }

    toggleInventoryValuationFold() {
        this.state.displayInventoryValuationLine = !this.state.displayInventoryValuationLine;
    }
}

registry.category("actions").add("stock_valuation_report", StockValuationReport);

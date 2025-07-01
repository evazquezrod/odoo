import { Component } from "@odoo/owl";


export class StockValuationReportLine extends Component {
    static template = "stock_account.StockValuationReport.InventoryValuationLine";
    static props = {
        class: { type: String, optional: true },
        label: { type: String, optional: true },
        line: { type: Object, optional: true },
        onClickMethod: { type: Function, optional: true },
        value: Number,
    };

    get formattedValue() {
        return this.env.formatMonetary(this.props.value);
    }

    // On Click Methods --------------------------------------------------------
    onClick() {
        this.props.onClickMethod && this.props.onClickMethod(this.props.line);
    }
}

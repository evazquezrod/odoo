export class StockValuationReportController {
    constructor(action) {
        this.action = action;
        // this.actionService = useService("action");
        // this.dialog = useService("dialog");
        // this.orm = useService("orm");
    }

    async load(env) {
        this.env = env;
    }
}

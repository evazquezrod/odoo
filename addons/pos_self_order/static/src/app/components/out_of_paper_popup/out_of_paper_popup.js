import { Component, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class OutOfPaperPopup extends Component {
    static template = "pos_self_order.OutOfPaperPopup";
    static props = {
        trackingNumber: String,
        title: { type: String, optional: true },
        message: String,
        close: Function,
    };

    static defaultProps = {
        title: _t("Printing failed"),
    };

    setup() {
        const timeout = setTimeout(() => {
            this.props.close();
        }, 20000);

        onWillUnmount(() => {
            clearTimeout(timeout);
        });
    }
}

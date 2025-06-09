import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { QuantityButtons } from '@sale/js/quantity_buttons/quantity_buttons';

export class ReturnOrderDialog extends Component {
    static components = { Dialog, QuantityButtons };
    static template = 'website_sale.ReturnOrderDialog';
    static props = {
        saleOrderId: Number,
        accessToken: String,
        save: Function,
        discard: Function,
        close: Function,
    };

    setup() {
        this.dialog = useService("dialog");
        this.state =  useState({ products: [] });
        this.title = _t("Request a return");

        onWillStart(async () => {
            this.content = await this._loadData();
            this.state.products = this.content.products;
            this.formatCurrency = formatCurrency;
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _loadData() {
        return rpc('/return/order/content', {
            order_id: this.props.saleOrderId,
            access_token: this.props.accessToken,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    setQuantity(product, quantity) {
        if (quantity < 0) {
            quantity = 0;
        } else if (quantity > product.order_qty) {
            quantity = product.order_qty;
        }
        if (product.quantity === quantity) {
            return false;
        }
        product.quantity = quantity;
        return true;
    }

    onContinue() {
        const errorMessage = this._getErrorMessage();
        if (errorMessage) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Error"),
                body: errorMessage
            });
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Instuctions"),
            body: _t("Print the return request label.\nAdd this label in your package and sent it to this address:"),
            confirmLabel: _t("Download Label"),
            cancelLabel: _t("Close"),
            confirm: async () => {
                const dayName = record.start.setLocale("en").weekdayLong.toLowerCase();
                const locationField = `${dayName}_location_id`;
                await this.orm.write('res.users', [record.rawRecord.user_id], {[locationField]: false})
                this.model.load();
            },
            cancel: () => {
            },
        });
    }

    _getErrorMessage() {
        const returnReasons = document.querySelector('select[name="return_reason"]');
        if (!returnReasons.value) {
            return _t("Please select a return reason.");
        }
        const noReturnProduct = this.state.products.every(product => Number(product.quantity) === 0);
        if (noReturnProduct) {
            return _t("Please add at least one product to return.");
        }

        return false;

    }

}

import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import {
    ReturnOrderDialog
} from '@website_sale_stock/js/return_order_dialog/return_order_dialog';

export class returnOrder extends Interaction {
    static selector = '.o_portal_sidebar';
    dynamicContent = {
        'button.o_wsale_return_button': { 't-on-click': this.onReturn },
    };

    async onReturn(ev) {
        this.orderId = parseInt(ev.currentTarget.dataset.saleOrderId);
        this.accessToken = new URLSearchParams(window.location.search).get('access_token');
        if (!this.orderId || !this.accessToken) return;

        await this._openReturnOrderDialog();
    }

    async _openReturnOrderDialog() {
        this.services.dialog.add(ReturnOrderDialog, {
            saleOrderId: this.orderId,
            accessToken: this.accessToken,
        })
    }

}

registry
    .category('public.interactions')
    .add('website_sale.return_order', returnOrder);
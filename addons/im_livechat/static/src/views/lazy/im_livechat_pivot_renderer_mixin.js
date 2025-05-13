import { useService } from "@web/core/utils/hooks";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

export const LivechatPivotRendererMixin = (model) =>
    class extends PivotRenderer {
        setup() {
            super.setup();
            this.store = useService("mail.store");
            this.recordCount = 0;
        }

        openView(domain, views, context, newWindow) {
            if (this.recordCount !== 1) {
                const action = this.env.services.orm.call(
                    model,
                    "action_open_discuss_channel_list_view",
                    [],
                    { domain }
                );
                this.env.services.action.doAction(action);
                return;
            }
            this.model.orm.search(model, domain, { limit: 1 }).then(([reportId]) => {
                this.actionService.doAction({
                    name: this.model.metaData.title,
                    type: "ir.actions.act_window",
                    res_model: model,
                    res_id: reportId,
                    views: [[false, "form"]],
                    target: "current",
                    context,
                });
            });
        }

        onOpenView(cell, newWindow) {
            [this.recordCount] = this.model.data.counts[JSON.stringify(cell.groupId)];
            super.onOpenView(cell, newWindow);
        }
    };

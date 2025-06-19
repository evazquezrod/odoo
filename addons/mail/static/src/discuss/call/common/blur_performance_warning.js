import { CallPopover } from "@mail/discuss/call/common/call_popover";

import { Component, useState, useEffect } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class BlurPerformanceWarning extends Component {
    static template = "discuss.BlurPerformanceWarning";
    static props = {};
    static components = { CallPopover };

    setup() {
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.isMobileOS = isMobileOS();
        this.state = useState({
            showWarning: this.rtc.state.isHwAccelerationEnabled,
        });
        useEffect(
            () => {
                if (
                    this.store.settings.useBlur &&
                    !this.rtc.state.isHwAccelerationEnabled &&
                    !this.isMobileOS &&
                    this.rtc.state.cameraTrack
                ) {
                    this.state.showWarning = true;
                } else {
                    this.state.showWarning = false;
                }
            },
            () => [
                this.store.settings.useBlur,
                this.rtc.state.isHwAccelerationEnabled,
                this.rtc.state.cameraTrack,
            ]
        );
    }

    onClickClose() {
        this.state.showWarning = false;
    }

    get warningMessage() {
        return {
            title: _t("Performance Warning"),
            body: _t("Hardware acceleration is disabled. This may affect the blur effect."),
        };
    }
}

import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { GaugeField, gaugeField } from "@web/views/fields/gauge/gauge_field";
import { getCSSVariableValue } from "@html_editor/utils/formatting";

export class SkillMatchGaugeField extends GaugeField {
    static template = "hr_recruitment.SkillMatchGaugeField";
    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            humanReadable: true,
            decimals: 0,
        });
    }

    renderChart() {
        const gaugeValue = this.props.record.data[this.props.name];
        let maxValue = this.props.maxValueField
            ? this.props.record.data[this.props.maxValueField]
            : this.props.maxValue;

        const fgColor =
            gaugeValue > maxValue
                ? getCSSVariableValue("success", getComputedStyle(document.documentElement))
                : getCSSVariableValue("primary", getComputedStyle(document.documentElement));
        maxValue = Math.max(gaugeValue, maxValue);
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
        }
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        backgroundColor: [fgColor, "#dddddd"],
                        label: this.title,
                    },
                ],
            },
            options: {
                circumference: 180,
                rotation: 270,
                responsive: true,
                maintainAspectRatio: false,
                cutout: "50%",
                plugins: {
                    title: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                },
                aspectRatio: 2,
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

export const skillMatchGaugeField = {
    ...gaugeField,
    component: SkillMatchGaugeField,
};

registry.category("fields").add("skill_match_gauge_field", skillMatchGaugeField);

import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { _t } from "@web/core/l10n/translation";

/**
 * Sends print request to ePos printer that is directly connected to the local network.
 */
export class PosPrinter extends BasePrinter {
    setup({ nw_printer_ip, device_ip }) {
        super.setup(...arguments);
        const [host, port] = nw_printer_ip.split(":");
        this.ip = host + (port ? ":" + port : ":9100");
        this.device_ip = device_ip;
    }

    /**
     * @override
     * Create the raster data from a canvas
     */
    processCanvas(canvas) {
        const rasterData = this.canvasToRaster(canvas);
        const encodedData = this.encodeRaster(rasterData);

        return {
            width: canvas.width,
            height: canvas.height,
            raster_base64: encodedData,
        };
    }

    /**
     * @override
     */
    openCashbox() {
        this.sendPrintingJob({ cash_drawer: true });
    }

    /**
     * @override
     */
    async sendPrintingJob(print_data) {
        try {
            const response = await this.posPrintReceipt({
                ...print_data,
                nw_printer_ip: this.ip,
            });
            return {
                result: response.status === "success",
                printerErrorCode: response.message,
            };
        } catch {
            return {
                result: false,
                printerErrorCode: "Not found, the printer is not reachable",
            };
        }
    }

    async posPrintReceipt({ raster_base64, width, height, nw_printer_ip, cash_drawer = false }) {
        const payload = {
            raster_base64,
            width,
            height,
            nw_printer_ip,
            cash_drawer,
        };

        try {
            const response = await fetch(`https://${this.device_ip}/pos/print/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error("Error printing receipt:", error);
            return { status: "error", message: error.message };
        }
    }

    /**
     * Transform a (potentially colored) canvas into a monochrome raster image.
     * We will use Floyd-Steinberg dithering.
     */
    canvasToRaster(canvas) {
        const imageData = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const errors = Array.from(Array(width), (_) => Array(height).fill(0));
        const rasterData = new Array(width * height).fill(0);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let oldColor, newColor;

                // Compute grayscale level. Those coefficients were found online
                // as R, G and B have different impacts on the darkness
                // perception (e.g. pure blue is darker than red or green).
                const idx = (y * width + x) * 4;
                oldColor = pixels[idx] * 0.299 + pixels[idx + 1] * 0.587 + pixels[idx + 2] * 0.114;

                // Propagate the error from neighbor pixels
                oldColor += errors[x][y];
                oldColor = Math.min(255, Math.max(0, oldColor));

                if (oldColor < 128) {
                    // This pixel should be black
                    newColor = 0;
                    rasterData[y * width + x] = 1;
                } else {
                    // This pixel should be white
                    newColor = 255;
                    rasterData[y * width + x] = 0;
                }

                // Propagate the error to the following pixels, based on
                // Floyd-Steinberg dithering.
                const error = oldColor - newColor;
                if (error) {
                    if (x < width - 1) {
                        // Pixel on the right
                        errors[x + 1][y] += (7 / 16) * error;
                    }
                    if (x > 0 && y < height - 1) {
                        // Pixel on the bottom left
                        errors[x - 1][y + 1] += (3 / 16) * error;
                    }
                    if (y < height - 1) {
                        // Pixel below
                        errors[x][y + 1] += (5 / 16) * error;
                    }
                    if (x < width - 1 && y < height - 1) {
                        // Pixel on the bottom right
                        errors[x + 1][y + 1] += (1 / 16) * error;
                    }
                }
            }
        }

        return rasterData.join("");
    }

    /**
     * Base 64 encode a raster image
     */
    encodeRaster(rasterData) {
        let encodedData = "";
        for (let i = 0; i < rasterData.length; i += 8) {
            const sub = rasterData.substr(i, 8);
            encodedData += String.fromCharCode(parseInt(sub, 2));
        }
        return btoa(encodedData);
    }

    /**
     * @override
     */
    getActionError() {
        const printRes = super.getResultsError();
        if (window.location.protocol === "https:") {
            printRes.message.body += _t(
                "If you are on a secure server (HTTPS) please make sure you manually accepted the certificate by accessing %s. ",
                this.url
            );
        }
        return printRes;
    }

    /**
     * @override
     */
    getResultsError(printResult) {
        const errorDetails = printResult.printerErrorCode;

        let message = _t("The printer responded, but printing could not be completed.") + "\n\n";

        if (errorDetails && typeof errorDetails === "object") {
            message += _t("Printer status report:") + "\n";

            for (const [section, messages] of Object.entries(errorDetails)) {
                const label = `-> ${_t(section)}:`;
                const lines = messages.map((msg) => `   - ${msg}`).join("\n");
                message += `\n${label}\n${lines}\n`;
            }
        } else {
            message += _t(
                "No detailed printer response received. Please check the printer hardware and configuration."
            );
        }

        return {
            successful: false,
            errorCode: null,
            message: {
                title: _t("Printing Failed"),
                body: message.trim(),
            },
        };
    }
}

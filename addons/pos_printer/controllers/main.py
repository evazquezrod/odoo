from odoo import http
import requests

class POSPrinterSocket(http.Controller):

    @http.route('/pos/print-receipt/', type='jsonrpc', auth='user')
    def pos_print_receipt(self, raster_base64, width, height, printer_ip, cash_drawer=False):
        payload = {
            "raster_base64": raster_base64,
            "width": width,
            "height": height,
            "printer_ip": printer_ip,
            "cash_drawer": cash_drawer
        }
        try:
            response = requests.post(f"https://{printer_ip.split(':')[0]}/pos/print/", json=payload)
            return response.json()
        except Exception as e:
            print(f"Error printing receipt: {e}")
            return {"status": "error", "message": str(e)}

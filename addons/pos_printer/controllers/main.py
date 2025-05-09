from odoo import http
import base64
import socket
from odoo.http import request


class POSPrinterSocket(http.Controller):

    @http.route('/pos/print-receipt/', type='jsonrpc', auth='user')
    def pos_print_receipt(self, raster_base64, width, height, printer_ip, cash_drawer=False):
        raster_bytes = base64.b64decode(raster_base64)
        bytes_per_row = (width + 7) // 8

        header = b'\x1d' + b'v' + b'0' + b'\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([height % 256, height // 256])
        escpos_data = b'\x1b@' + header + raster_bytes + b'\x1b\x64\x03' + b'\x1dV\x00'

        if cash_drawer:
            escpos_data += b'x1b\x70\x00\x19\x78'
                
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            ip, port = printer_ip.split(':')
            s.connect((ip, int(port)))
            s.sendall(escpos_data)

        return {"status": "success"}

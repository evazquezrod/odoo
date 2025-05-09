from odoo import http
from odoo.http import request
import base64
from io import BytesIO

class POSMyPrinter(http.Controller):
    @http.route('/pos/print-receipt/', type='json', auth='public')
    def print_receipt__(self, raster_base64, width, height):
        # breakpoint()
        raster_bytes = base64.b64decode(raster_base64)
        bytes_per_row = (width + 7) // 8

        # ESC/POS header
        header = b'\x1d' + b'v' + b'0' + b'\x00' + \
                 bytes([bytes_per_row % 256, bytes_per_row // 256]) + \
                 bytes([height % 256, height // 256])
        escpos_data = b'\x1b@' + header + raster_bytes + b'\x1b\x64\x05' + b'\x1dV\x00'
        # Send to printer via socket (adjust to your printer IP and port)
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("192.168.6.80", 9100))  # Change this!
            s.sendall(escpos_data)

        return {"status": "success"}

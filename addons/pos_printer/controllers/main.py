from odoo import http
import base64
import socket
from odoo.http import request
from socket import timeout, error as socket_error


STATUS_COMMANDS = {
    'Printer Status': b'\x10\x04\x01',
    'Offline Status': b'\x10\x04\x02',
    'Error Status': b'\x10\x04\x03',
    'Paper Status': b'\x10\x04\x04',
}

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
            printer_status = self.check_printer_status(ip, int(port))
            print("Printer Status:", printer_status)
            if printer_status:
                return {"status": "error", "message": printer_status}
            s.settimeout(10)
            s.connect((ip, int(port)))
            s.sendall(escpos_data)
        return {"status": "success"}


    def decode_status(self, name, byte_val):
        b = byte_val[0]
        messages = []

        if name == 'Printer Status':
            if b & 0x80: messages.append("Printer is busy")
            if b & 0x40: messages.append("Feeding paper using FEED button")
            if b & 0x20: messages.append("An error has occurred")
            if b & 0x08: messages.append("Cash drawer pin 3 is high")
            if not messages: messages.append("Printer status OK")

        elif name == 'Offline Status':
            if b & 0x80: messages.append("Cover is open")
            if b & 0x40: messages.append("Paper is feeding")
            if b & 0x20: messages.append("Printer is offline")
            if b & 0x08: messages.append("Waiting for recovery")
            if not messages: messages.append("Printer is online and ready")

        elif name == 'Error Status':
            if b & 0x20: messages.append("Auto-recoverable error (e.g., head/motor overheated)")
            if b & 0x08: messages.append("Unrecoverable error occurred")
            if b & 0x04: messages.append("Auto-cutter error")
            if not messages: messages.append("No printer errors")

        elif name == 'Paper Status':
            if b & 0x08: messages.append("Paper end (out of paper)")
            if b & 0x04: messages.append("Paper near-end warning")
            if not messages: messages.append("Paper status OK")

        return messages

    def check_printer_status(self, host, port):
        try:
            errors = {}

            with socket.create_connection((host, int(port)), timeout=3) as sock:
                for name, cmd in STATUS_COMMANDS.items():
                    sock.sendall(cmd)
                    response = sock.recv(1)
                    decoded = self.decode_status(name, response)
                    for msg in decoded:
                        if "OK" not in msg and "ready" not in msg and "No printer errors" not in msg:
                            errors.setdefault(name, []).append(msg)

            if not errors:
                return False
            return errors

        except socket.timeout:
            return {"Connection Error": ["Connection timed out."]}
        except socket.error as e:
            return {"Socket Error": [str(e)]}
        except Exception as e:
            return {"Unexpected Error": [str(e)]}

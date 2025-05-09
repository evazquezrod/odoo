from odoo import fields, models
import socket

class PosConfig(models.Model):
    _inherit = 'pos.config'

    nw_printer_ip = fields.Char(string='Network Printer IP', help="Local IP address of an receipt printer.")


    def print_receipt(self, commands):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("192.168.6.80", 9100))
            s.sendall(create_print_commands())
            print("*"*100)
            print("Print job sent successfully")
            print("*"*100)
        



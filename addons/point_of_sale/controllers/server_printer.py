import logging
import queue

from odoo import http
from odoo.http import request

import xml.etree.ElementTree as gfg 
_logger = logging.getLogger(__name__)

from xml.etree.ElementTree import Element, SubElement, tostring

def generate_receipt_xml():
    return """
<?xml version="1.0" encoding="utf-8" ?>
 <PrintRequestInfo>
 <ePOSPrint>
 <Parameter>
 <devid>local_printer</devid>
 <timeout>10000</timeout>
 </Parameter>
 <PrintData>
 <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
 <text lang="en" />
 <text smooth="true" />
 <text align="center" />
 <text font="font_b" />
 <text width="2" height="2" />
 <text reverse="false" ul="false" em="true" color="color_1" />
 <text>DELIVERY TICKET</text>
 <feed unit="12" />
 <text></text>
 <text align="left" />
 <text font="font_a" />
 <text width="1" height="1" />
 <text reverse="false" ul="false" em="false" color="color_1" />
 <text>Order 0001</text>
 <text width="1" height="1" />
 <text reverse="false" ul="false" em="false" color="color_1" />
 <text>Time Mar 19 2013 13:53:15</text>
 <text>Seat A-3</text>
 <text></text>
 <text width="1" height="1" />
 <text reverse="false" ul="false" em="false" color="color_1" />
 <text>Alt Beer</text>
 <text>$6.00 x 2</text>
 <text x="384" />
 <text>$12.00</text>
 <text></text>
 <text reverse="false" ul="false" em="true" />
 <text width="2" height="1" />
 <text>TOTAL</text>
 <text x="264" />
 <text>$12.00</text>
 <text reverse="false" ul="false" em="false" />
 <text width="1" height="1" />
 <feed unit="12" />
 <text align="center" />
 <barcode type="code39" hri="none" font="font_a" width="2" height="60">0001
</barcode>
 <feed line="3" />
 <cut type="feed" />
 </epos-print>
 </PrintData>
 </ePOSPrint>
 <ePOSPrint>
 <Parameter>
 <devid>kitchen_printer</devid>
 <timeout>10000</timeout>
 </Parameter>
 <PrintData>
 <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
 <text lang="en" />
 <text smooth="true" />
 <text rotate="true" />
 <text align="center" />
 <barcode type="code39" hri="none" font="font_a" width="2" height="60">0001</barcode>
 <feed unit="30" />
 <text align="left" />
 <text>0001</text>
 <text>03-19-2013 13:53:15</text>
 <text reverse="true" />
 <text>Kitchen</text>
 <text reverse="false" />
 <text />
 <text>[New Order]</text>
 <text></text>
 <text width="1" height="2" />
 <text>Seat:</text>
 <text width="2" height="2" />
 <text>A-3</text>
 <text width="1" height="1" />
 <text></text>
 <text width="2" height="2" />
 <text>2</text>
 <text width="1" height="2" />
 <text>Alt Beer</text>
 <text width="1" height="1" />
 <text></text>
 <cut type="feed" />
 <text rotate="false" />
 </epos-print>
 </PrintData>
 </ePOSPrint>
 </PrintRequestInfo>
"""

class ServerPrinterController(http.Controller):
    receipt_jobs_queue = queue.Queue()

    @http.route('/point_of_sale/server_print/<int:pos_config_id>/add_receipt_to_print_queue', auth="public", type='jsonrpc', csrf=False)
    def add_receipt_to_print_queue(self, pos_config_id, receipt_to_print):
        if not receipt_to_print:
            _logger.warning("No receipt provided for printing")
            return {'error': 'No receipt provided for printing'}
        _logger.critical("Here from pos congig %s", pos_config_id)
        self.receipt_jobs_queue.put(receipt_to_print)
        return {'status': 'success', 'message': 'Receipt added to print queue'}

    @http.route('/point_of_sale/server_print/<int:pos_config_id>/poll_server_print', auth="public", type='http', csrf=False)
    def poll_server_print(self, pos_config_id=0):
        par = request.params
        #import pdb; pdb.set_trace()
        _logger.critical("Printer %s polling to check for available print jobs", request.params.get('Name'))
        #receipt_to_print = self.receipt_jobs_queue.get()
        headers = [
            ('Content-Type', 'text/xml;charset=utf-8'),
            ('Content-Length', str(len(generate_receipt_xml()))),
        ]
        return request.make_response(generate_receipt_xml(), status=200, headers=headers)

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json
from datetime import datetime
import os

class OrderList(models.Model):
    _name = 'atm.orderlist'
    _description = 'Order list'

    @api.model
    def export_order_list_to_json(self):
        orders = self.env['sale.order'].search([])
        order_data = []
        exp_dir = self.env['ir.config_parameter'].sudo().get_param('atm.export_dir')

        for order in orders:
            order_line_data = []
            for line in order.order_line:
                order_line_data.append({
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                })
            order_dict = {
                'id': order.id,
                'name': order.name,
                'partner_name': order.partner_id.name,
                'partner_id': order.partner_id.id,
                'state': order.state,
                'amount_total': order.amount_total,
                'date_order': order.date_order,
                'order_line': order_line_data,
                # TODO: add order lines to OrderList JSON files
            }
            order_data.append(order_dict)
        # 
        with open(exp_dir + 'order_list.json', 'w') as f:
            json.dump(order_data, f, cls=DateTimeEncoder, indent=4)
        # get current directory
        current_directory = os.getcwd()
        print("Current directory:", current_directory) 
        # user export directory   
        print("File saved to the export directory - " + exp_dir + 'order_list.json')

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return super().default(o)

class ProductStockReport(models.AbstractModel):
    _name = 'report.product_stock_report.stock_report_template'
    _description = 'Product Stock Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        products = self.env['product.product'].search([])
        report_data = []
        for product in products:
            product_data = {
                'name': product.name,
                'default_code': product.default_code,
                'qty_available': product.qty_available,
                'incoming_qty': product.incoming_qty,
                'outgoing_qty': product.outgoing_qty,
                'virtual_available': product.virtual_available,
            }
            report_data.append(product_data)
        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': self.env['product.product'].browse(docids),
            'report_data': report_data,
        }

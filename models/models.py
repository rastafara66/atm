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
        '''
        Exort sale orders to JSON file "order_list.json" in specified directory
            Return:
        None.
        '''
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

    def import_order_list_from_json(self):
        '''
        Import sale orders from JSON file "order_list.json" in specified directory
            Return:
        None.
        '''

    # We establish a connection with Odoo.
    # env = api.Environment(
    #     client=Client(),
    #     user=user,
    #     password=password,
    #     database=database,
    # )
        
        exp_dir = self.env['ir.config_parameter'].sudo().get_param('atm.export_dir')
        file_name =  exp_dir + 'order_list.json'
        # Читаємо файл JSON.
        with open(file_name, "r") as f:
            data = json.load(f)

        # We get on each order in the JSON file.
        for order in data:
            # We create a new order in Odoo.
            order_id = self.env["sale.order"].create({
            "name": order["name"],
            "partner_id": order["partner_id"],
            "state": order["state"],
            "amount_total": order["amount_total"],
            # "date_order": JSONDecoder.json_decoder(order["date_order"]),
            # "date_order": order["date_order"].replace("T", " "),
            "date_order": order["date_order"],
            })

            # We get on each position in the order.
            for line in order["order_line"]:
                # We create a new order position in Odoo.
                line_id = self.env["sale.order.line"].create({
                    "order_id": order_id,
                    "product_id": line["product_id"],
                    "product_uom_qty": line["product_uom_qty"],
                    "price_unit": line["price_unit"],
                    "price_subtotal": line["price_subtotal"],
                })
                print(line_id)

    # Let's notify the user of success.
    print("Замовлення успішно імпортовані.")
    
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return super().default(o)

class JSONDecoder(json.JSONDecoder):
    def json_decoder(data):
        """
        JSONDecoder that accepts data in any format.

        Args:
            data (str): JSON data.

        Returns:
            dict: JSON data as a dictionary.
        """
        decoder = json.JSONDecoder()
        decoder.strict = False

        try:
            result = decoder.decode(data)
        except json.JSONDecodeError as e:
            raise ValueError(e)

        # Convert dates to Date objects.
        for key, value in result.items():
            if isinstance(value, str):
                if value.startswith("%Y-%m-%dT"):
                    result[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

        return result
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

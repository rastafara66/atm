# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json

class OrderList(models.Model):
    _name = 'order.list'
    
    @api.model
    def export_order_list_to_json(self):
        orders = self.env['sale.order'].search([])
        order_list = []
        for order in orders:
            order_dict = {
                'id': order.id,
                'name': order.name,
                'customer': order.customer.name,
                'partner_id': order.partner_id.name,
                'amount_total': order.amount_total,
                'date_order': order.date_order,
            }
            order_list.append(order_dict)

        with open('order_list.json', 'w') as f:
            json.dump(order_list, f, indent=4)
            
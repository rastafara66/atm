# -*- coding: utf-8 -*-
# from odoo import http


# class Atm(http.Controller):
#     @http.route('/atm/atm', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/atm/atm/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('atm.listing', {
#             'root': '/atm/atm',
#             'objects': http.request.env['atm.atm'].search([]),
#         })

#     @http.route('/atm/atm/objects/<model("atm.atm"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('atm.object', {
#             'object': obj
#         })

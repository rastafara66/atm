# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class ATMController(http.Controller):
    
    @http.route('/atm/save_settings', type='http', auth="user")
    def save_settings(self, **post):
        settings = request.env['atm.settings'].sudo().search([])
        for setting in settings:
            setting.write({
                'value': post.get(setting.name)
            })
        return http.request.redirect('/atm/settings')

    @http.route('/atm/cancel_settings', type='http', auth="user")
    def cancel_settings(self, **post):
        return http.request.redirect('/atm/settings')
    
    @http.route('/atm/settings', type='http', auth="user")
    def open_settings(self, **post):
        settings = request.env['atm.settings'].sudo().search([])
        return http.request.render('atm.view_atm_settings_form', {
            'settings': settings,
        })
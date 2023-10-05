# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']
    # WareHouses
    wh_id_3a = fields.Char("WH ID 3A", default="WareHouse ID 3A")
    wh_id_1c = fields.Char('WH ID 1C', default="WareHouse ID 1C")    
    wh_name_3a = fields.Char('WH Name 3A', default="WareHouse Name 3A")
    wh_name_1c = fields.Char("WH Name 1C", default="WareHouse Name 1C")    

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('adealer.wh_id_3a', \
            self.wh_id_3a)
        self.env['ir.config_parameter'].sudo().set_param('adealer.wh_id_1c', \
            self.wh_id_1c)            
        self.env['ir.config_parameter'].sudo().set_param('adealer.wh_name_3a', \
            self.wh_name_3a)
        self.env['ir.config_parameter'].sudo().set_param('adealer.wh_name_1c', \
            self.wh_name_1c)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        wh_id_3a = self.env['ir.config_parameter'].sudo().get_param('adealer.wh_id_3a')
        wh_id_1c = self.env['ir.config_parameter'].sudo().get_param('adealer.wh_id_1c')
        wh_name_3a = self.env['ir.config_parameter'].sudo().get_param('adealer.wh_name_3a')
        wh_name_1c = self.env['ir.config_parameter'].sudo().get_param('adealer.wh_name_1c')

        res.update({
            'wh_id_3a': wh_id_3a,
            'wh_id_1c': wh_id_1c,
            'wh_name_3a': wh_name_3a,
            'wh_name_1c': wh_name_1c,
        })
        return res

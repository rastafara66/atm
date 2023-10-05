# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']
    export_dir = fields.Char("Export Dir", default="D:\\Export")  

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('atm.export_dir', \
            self.export_dir)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        export_dir = self.env['ir.config_parameter'].sudo().get_param('atm.export_dir')

        res.update({
            'export_dir': export_dir,
        })
        return res

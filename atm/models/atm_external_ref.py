# -*- coding: utf-8 -*-
"""The key that ties an Odoo record to its twin in the external system."""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AtmExternalRefMixin(models.AbstractModel):
    _name = 'atm.external.ref.mixin'
    _description = 'Data Exchange External Reference'

    atm_external_ref = fields.Char(
        string='External Reference',
        index=True,
        copy=False,
        help='Identifier of this record in the external system. Records are '
             'matched by this key during import, so it must stay stable.',
    )

    @api.constrains('atm_external_ref')
    def _check_atm_external_ref_unique(self):
        """Two records sharing a key would make the import ambiguous.

        Checked in Python rather than with a unique index: the field is empty
        on the vast majority of records and the check only has to run when it
        is actually written.
        """
        for record in self:
            if not record.atm_external_ref:
                continue
            duplicate = self.search([
                ('atm_external_ref', '=', record.atm_external_ref),
                ('id', '!=', record.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'External reference "%(ref)s" is already used by %(name)s.',
                    ref=record.atm_external_ref,
                    name=duplicate.display_name,
                ))


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'atm.external.ref.mixin']


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'atm.external.ref.mixin']


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'atm.external.ref.mixin']


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'atm.external.ref.mixin']


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'atm.external.ref.mixin']


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'atm.external.ref.mixin']

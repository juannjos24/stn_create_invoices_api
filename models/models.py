# from odoo import models, fields, api


# class stn_create_invoices_api(models.Model):
#     _name = 'stn_create_invoices_api.stn_create_invoices_api'
#     _description = 'stn_create_invoices_api.stn_create_invoices_api'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100


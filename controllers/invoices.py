import logging
import json
from odoo import http, SUPERUSER_ID
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class ApiController(http.Controller):

    def _create_response(self, data, status_code):
        headers = [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, apiKey, secretKey'),
        ]
        return Response(json.dumps(data), status=status_code, headers=headers)

    def _validate_auth(self, sudo_env):
        """Valida las credenciales contra el modelo stings.key"""
        api_key = request.httprequest.headers.get('apiKey')
        secret_key = request.httprequest.headers.get('secretKey')
        if not api_key or not secret_key:
            return None, "Missing headers", 400
        
        api_record = sudo_env['stings.key'].search([
            ('key', '=', api_key), 
            ('secret_key', '=', secret_key)
        ], limit=1)
        
        if not api_record:
            return None, "Invalid API Key", 401
        return api_record, None, 200

    @http.route('/api/create_invoice', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def create_invoice(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._create_response({}, 200)

        # 1. SOLUCIÓN AL ERROR SINGLETON: Forzar el usuario en el entorno global de la petición
        request.update_env(user=SUPERUSER_ID)
        sudo_env = request.env 

        # 2. Autenticación
        api_record, error_msg, status = self._validate_auth(sudo_env)
        if error_msg:
            return self._create_response({"status": "error", "message": error_msg}, status)

        # 3. Parseo de Datos
        try:
            payload = json.loads(request.httprequest.data)
            invoice_data = payload.get('invoice_data', {})
            invoice_lines = payload.get('invoice_lines', [])
        except Exception:
            return self._create_response({"status": "error", "message": "JSON inválido"}, 400)

        # 4. Búsqueda de Cliente por Referencia (REF)
        partner = sudo_env['res.partner'].search([('ref', '=', invoice_data.get('partner_id'))], limit=1)
        if not partner:
            return self._create_response({"status": "error", "message": "Partner no encontrado"}, 404)

        # 5. Selección Automática de Cuenta de Ingresos e Impuestos
        income_account = sudo_env['account.account'].search([('account_type', '=', 'income')], limit=1)
        if not income_account:
            income_account = sudo_env['account.account'].search([('internal_group', '=', 'income')], limit=1)
        
        tax = sudo_env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 16.0)], limit=1)

        # 6. Preparación de Valores (Cabecera)
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': invoice_data.get('invoice_date'),
            'invoice_date_due': invoice_data.get('invoice_date_due'),
            'l10n_mx_edi_payment_method_id': invoice_data.get('l10n_mx_edi_payment_method_id'),
            'l10n_mx_edi_usage': invoice_data.get('l10n_mx_edi_usage'),
            'invoice_payment_term_id':invoice_data.get('invoice_payment_term_id'),
            'invoice_line_ids': []
        }

        # 7. Procesamiento de Líneas
        if not invoice_lines:
            return self._create_response({"status": "error", "message": "Debe enviar al menos una línea"}, 400)

        for line in invoice_lines:
            # 1. Prioridad: ¿Viene un tax_id en el JSON?
            # Si no viene, usamos el tax.id (IVA 16%) que buscamos automáticamente arriba
            line_tax_id = line.get('tax_ids', [tax.id] if tax else [])
            
            # 2. Aseguramos que sea una lista para el comando (6, 0, [ids])
            if isinstance(line_tax_id, int):
                line_tax_id = [line_tax_id]
                
            move_vals['invoice_line_ids'].append((0, 0, {
                'name': line.get('description', 'Concepto General'),
                'account_id': income_account.id,
                'quantity': line.get('quantity', 1.0),
                'price_unit': line.get('price_unit', 0.0),
                'tax_ids': [(6, 0, line_tax_id)], # Usamos la lista de IDs (propios o automáticos)            
            }))

        # 8. Creación de la Factura
        try:
            invoice = sudo_env['account.move'].with_context(default_move_type='out_invoice').create(move_vals)
            return self._create_response({
                "status": "success",
                "invoice_id": invoice.id,
                "invoice_number": invoice.name or "Borrador",
                "total": invoice.amount_total
            }, 201)
        except Exception as e:
            _logger.error("API Error: %s", str(e))
            return self._create_response({"status": "error", "message": str(e)}, 500)
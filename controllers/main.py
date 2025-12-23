import logging
import json
from odoo import http, SUPERUSER_ID
from odoo.http import request, Response

# Configuramos el logger para ver los mensajes en el log de Odoo
_logger = logging.getLogger(__name__)
# ============================================
#   CONFIGURACIÓN CORS
# ============================================
ALLOWED_ORIGIN = "*"  

def make_cors_headers():
    return [
        ('Access-Control-Allow-Origin', ALLOWED_ORIGIN),
        ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PATCH'),
        ('Access-Control-Allow-Headers', 'Content-Type, apiKey, secretKey'),
        ('Access-Control-Allow-Credentials', 'true'),
        ('Access-Control-Max-Age', '3600'),
    ]

# ============================================
#   CONTROLADOR PRINCIPAL
# ============================================
class ApiController(http.Controller):

    # ---------------------------------------------------------
    # 1. CREAR CLIENTE PRINCIPAL (Empresa o Persona Física)
    # ---------------------------------------------------------
    @http.route('/api/create_partner', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def create_partner(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._create_response({}, 200)

        api_record, error_msg, status = self._validate_auth()
        if error_msg:
            return self._create_response({"status": "error", "message": error_msg}, status)

        try:
            data = json.loads(request.httprequest.data)
            contact_data = data.get('contact_data', {})
        except Exception:
            return self._create_response({"status": "error", "message": "Invalid JSON"}, 400)

        try:
            # Forzamos 'contact' para que sea un partner principal y no una dirección
            vals = {
                'name': contact_data.get('name'),
                'is_company': contact_data.get('company_type') == 'company',
                'company_type': contact_data.get('company_type', 'person'),
                'type': 'contact', # <--- Clave para que NO sea dirección de entrega
                'ref': contact_data.get('ref'),
                'id_secondary': contact_data.get('id_secondary'),
                'vat': contact_data.get('vat'),
                'email': contact_data.get('email'),
                'phone': contact_data.get('phone'),
                'street': contact_data.get('street'),
                'city': contact_data.get('city'),
                'city_id':contact_data.get('city_id'),
                'state_id': contact_data.get('state_id'),
                'zip': contact_data.get('zip'),
                'country_id': contact_data.get('country_id'),
                'l10n_mx_edi_fiscal_regime': contact_data.get('l10n_mx_edi_fiscal_regime'),
                'lang': contact_data.get('lang', 'es_MX'),
            }
            
            new_partner = request.env['res.partner'].sudo().with_user(SUPERUSER_ID).create(vals)
            return self._create_response({'status': 'success', 'id': new_partner.id, 'ref': new_partner.ref}, 201)
        except Exception as e:
            return self._create_response({"status": "error", "message": str(e)}, 500)

    # ---------------------------------------------------------
    # 2. CREAR DIRECCIÓN DE ENTREGA (Vinculada por ref)
    # ---------------------------------------------------------
    @http.route('/api/create_shipping', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def create_shipping(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._create_response({}, 200)

        api_record, error_msg, status = self._validate_auth()
        if error_msg:
            return self._create_response({"status": "error", "message": error_msg}, status)

        try:
            data = json.loads(request.httprequest.data)
            ship_data = data.get('contact_data', {})
        except Exception:
            return self._create_response({"status": "error", "message": "Invalid JSON"}, 400)

        # BUSCAR PADRE POR REF
        parent_ref = ship_data.get('parent_id') # "REF12345"
        parent = request.env['res.partner'].sudo().with_user(SUPERUSER_ID).search([('ref', '=', parent_ref)], limit=1)
        
        if not parent:
            return self._create_response({"status": "error", "message": f"Padre con ref {parent_ref} no existe."}, 404)

        try:
            new_shipping = request.env['res.partner'].sudo().with_user(SUPERUSER_ID).create({
                'name': ship_data.get('name'),
                'parent_id': parent.id,
                'type': 'delivery',
                'street': ship_data.get('street'),
                'street2': ship_data.get('street2'),
                'city': ship_data.get('city'),
                'city_id':ship_data.get('city_id'),
                'zip': ship_data.get('zip'),
                'state_id': ship_data.get('state_id'),
                'country_id': ship_data.get('country_id'),
                'email': ship_data.get('email'),
                'phone': ship_data.get('phone'),
                'comment': ship_data.get('comment'),
            })
            return self._create_response({'status': 'success', 'id': new_shipping.id}, 201)
        except Exception as e:
            return self._create_response({"status": "error", "message": str(e)}, 500)

    # --- Métodos de Soporte ---
    def _validate_auth(self):
        api_key = request.httprequest.headers.get('apiKey')
        secret_key = request.httprequest.headers.get('secretKey')
        api_record = request.env['stings.key'].sudo().with_user(SUPERUSER_ID).search([('key', '=', api_key), ('secret_key', '=', secret_key)], limit=1)
        if not api_record: return None, "Unauthorized", 401
        return api_record, None, 200

    def _create_response(self, data, status_code):
        headers = make_cors_headers()
        headers.append(('Content-Type', 'application/json'))
        return Response(json.dumps(data), status=status_code, headers=headers)

    # Endpoint para actualizar un contacto utilizando el 'ref'
    @http.route('/api/update_contact', 
                type='http', 
                auth='none', 
                methods=['PATCH'], 
                csrf=False)
    def update_contact(self, **kwargs):
        api_key = request.httprequest.headers.get('apiKey')
        secret_key = request.httprequest.headers.get('secretKey')

        # 1. Validar la clave de API
        if not api_key or not secret_key:
            return self._create_response(
                {"status": "error", "message": "Missing required headers (apiKey and/or secretKey)"},
                400
            )

        try:
            api_record = request.env['stings.key'].sudo().search([('key', '=', api_key), ('secret_key', '=', secret_key)], limit=1)
            if not api_record:
                return self._create_response(
                    {"status": "error", "message": "Invalid API Key or Secret Key"},
                    401
                )
        except Exception as e:
            return self._create_response(
                {"status": "error", "message": f"Authentication check failed: {e}"},
                500
            )

        # 2. Obtener y decodificar los datos del cuerpo (Necesario para type='http')
        try:
            # Leemos y decodificamos el JSON del cuerpo de la solicitud
            data = json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return self._create_response(
                {"status": "error", "message": "Invalid JSON payload format."},
                400
            )

        contact_data = data.get('contact_data', {})

        # 3. Validar los datos del contacto
        if not contact_data or not isinstance(contact_data, dict):
            return self._create_response(
                {'status': 'error', 'message': 'No valid contact data provided in payload.'},
                400
            )
        
        name = contact_data.get('name')
        ref = contact_data.get('ref')  # Usamos el ID secundario para identificar el contacto

        # Validación de campos esenciales
        if  not ref or not name:
            missing_fields = []           
            if not ref: missing_fields.append('ref')
            if not name:missing_fields.append('name')
            
            return self._create_response(
                {'status': 'error', 'message': f'Missing required contact fields: {", ".join(missing_fields)}'},
                400
            )

        # Verificar si el contacto existe por 'ref'
        try:
            existing_contact = request.env['res.partner'].sudo().search([
                ('ref', '=', ref),                
            ], limit=1)

            if not existing_contact:
                return self._create_response(
                    {'status': 'error', 'message': f"Contact with ref {ref} not found"},
                    404  # 404 Not Found
                )

            # No permitir la actualización del 'ref' (lo dejamos igual)
            contact_data.pop('ref', None)  # Eliminar el campo de 'ref' si está presente en la solicitud

            # Actualizar el contacto con los nuevos datos
            existing_contact.write({               
                'active': contact_data.get('active', True),
                'company_type': contact_data.get('company_type'),
                'name': contact_data.get('name'),
                'email': contact_data.get('email'),
                'phone': contact_data.get('phone'),
                'parent_id': contact_data.get('parent_id'),
                'street': contact_data.get('street'),
                'street2': contact_data.get('street2'),
                'city_id': contact_data.get('city_id'),
                'city': contact_data.get('city'),
                'state_id': contact_data.get('state_id'),
                'zip': contact_data.get('zip'),
                'country_id': contact_data.get('country_id'),
                'vat': contact_data.get('vat'),
                'l10n_mx_edi_usage': contact_data.get('l10n_mx_edi_usage'),
                'l10n_mx_edi_fiscal_regime': contact_data.get('l10n_mx_edi_fiscal_regime'),
                'l10n_mx_edi_payment_method_id': contact_data.get('l10n_mx_edi_payment_method_id'),
                'property_payment_term_id': contact_data.get('property_payment_term_id'),
                'property_product_pricelist': contact_data.get('property_product_pricelist'),
                'user_id': contact_data.get('user_id'),
                'lang': contact_data.get('lang', 'es_MX'),
                'ref': contact_data.get('ref'),
            })

            return self._create_response(
                {'status': 'success', 'contact_id': existing_contact.id},
                200  # 200 OK
            )

        except Exception as e:
            return self._create_response(
                {"status": "error", "message": f"Update failed: {e}"},
                500
            )

from odoo import http
from odoo.http import request, Response
import json
from odoo.exceptions import AccessDenied

# ============================================
#   CONFIGURACIÓN CORS
# ============================================
ALLOWED_ORIGIN = "*"  # Cambia esto a tu dominio Angular si es necesario

def make_cors_headers():
    return [
        ('Access-Control-Allow-Origin', ALLOWED_ORIGIN),
        ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, apiKey, secretKey'),
        ('Access-Control-Allow-Credentials', 'true'),
        ('Access-Control-Max-Age', '3600'),
    ]

# ============================================
#   OPTIONS → NECESARIO PARA ANGULAR
# ============================================
class ArbolCORS(http.Controller):

    @http.route('/api/arbol/generar',
                auth='public',
                type='http',
                methods=['OPTIONS'],
                csrf=False)
    def options_cors(self, **kwargs):
        headers = make_cors_headers()
        return Response(status=200, headers=headers)


# ============================================
#   CONTROLADOR PRINCIPAL
# ============================================
class ApiController(http.Controller):
    
    # Función de ayuda para construir respuestas HTTP
    def _create_response(self, data, status_code):
        headers = make_cors_headers()
        headers.append(('Content-Type', 'application/json'))
        return Response(json.dumps(data), status=status_code, headers=headers)

    # Endpoint para crear un contacto
    @http.route('/api/create_contact', 
                type='http', 
                auth='none', 
                methods=['POST'], 
                csrf=False)
    def create_contact(self, **kwargs):
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

        # Validación de campos esenciales
        name = contact_data.get('name')
        email = contact_data.get('email')
        phone = contact_data.get('phone')
        id_secondary = contact_data.get('id_secondary')  # Usamos el ID secundario

        if not name or not email or not phone:
            missing_fields = []
            if not name: missing_fields.append('name')
            if not email: missing_fields.append('email')
            if not phone: missing_fields.append('phone')
            if not id_secondary: missing_fields.append('id_secondary')

            return self._create_response(
                {'status': 'error', 'message': f'Missing required contact fields: {", ".join(missing_fields)}'},
                400
            )

        # Validar el formato del correo electrónico
        if '@' not in email:
            return self._create_response(
                {'status': 'error', 'message': 'Invalid email format.'},
                400
            )
        
        # Verificar si ya existe un contacto con el mismo email
        # Intentar crear el nuevo contacto
        try:
            new_contact = request.env['res.partner'].sudo().with_context(l10n_mx_edi_force_validate_vat=False).create({
                'id_secondary': contact_data.get('id_secondary'),
                'active': contact_data.get('active', True),
                'company_type': contact_data.get('company_type'),
                'name': contact_data.get('name'),
                'email': contact_data.get('email'),
                'phone': contact_data.get('phone'),
                'parent_id': contact_data.get('parent_id'),
                'street': contact_data.get('street'),
                'street2': contact_data.get('street2'),
                'city_id':contact_data.get('city_id'),
                'city': contact_data.get('city'),
                'state_id': contact_data.get('state_id'),
                'zip': contact_data.get('zip'),
                'country_id': contact_data.get('country_id'),
                'vat': contact_data.get('vat'),
                'l10n_mx_edi_usage': contact_data.get('l10n_mx_edi_usage'),
                'l10n_mx_edi_fiscal_regime': contact_data.get('l10n_mx_edi_fiscal_regime'),
                'l10n_mx_edi_payment_method_id': contact_data.get('l10n_mx_edi_payment_method_id'),
                'property_payment_term_id': contact_data.get('property_payment_term_id'),
                'property_product_pricelist':  contact_data.get('property_product_pricelist'),
                'user_id': contact_data.get('user_id'),                
                'lang': contact_data.get('lang', 'es_MX'),
                'ref': contact_data.get('ref'),
            })

            return self._create_response(
                {'status': 'success', 'contact_id': new_contact.id},
                201
            )

        except Exception as e:
            # Si ocurre un error, devuelve el mensaje de error específico
            return self._create_response(
                {"status": "error", "message": f"Creation failed: {str(e)}"},
                500
            )

    # Endpoint para actualizar un contacto utilizando el 'id_secondary'
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
        id_secondary = contact_data.get('id_secondary')  # Usamos el ID secundario para identificar el contacto

        # Validación de campos esenciales
        if  not id_secondary or not name:
            missing_fields = []           
            if not id_secondary: missing_fields.append('id_secondary')
            if not name:missing_fields.append('name')
            
            return self._create_response(
                {'status': 'error', 'message': f'Missing required contact fields: {", ".join(missing_fields)}'},
                400
            )

        # Verificar si el contacto existe por 'id_secondary'
        try:
            existing_contact = request.env['res.partner'].sudo().search([
                ('id_secondary', '=', id_secondary),                
            ], limit=1)

            if not existing_contact:
                return self._create_response(
                    {'status': 'error', 'message': f"Contact with id_secondary {id_secondary} not found"},
                    404  # 404 Not Found
                )

            # No permitir la actualización del 'id_secondary' (lo dejamos igual)
            contact_data.pop('id_secondary', None)  # Eliminar el campo de 'id_secondary' si está presente en la solicitud

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

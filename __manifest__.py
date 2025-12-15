{
    'name': 'Stings API Integration',
    'version': '1.0',
    'category': 'Integration',  # Puedes usar 'Integration' si prefieres
    'summary': 'API Integration for Stings with Odoo',
    'description': """
        Este módulo permite la integración con una API externa mediante claves de seguridad (API Key y Secret Key).
        Permite la creación de contactos mediante solicitudes API.
        
        Configura las claves de API necesarias para la autenticación y uso de la API.
        También incluye una vista para gestionar las claves de API dentro de Odoo.
    """,
    'author': 'Tu Nombre',
    'website': 'https://www.tusitio.com',  # Si tienes un sitio web, inclúyelo aquí.
    'depends': ['base', 'contacts'],  # Dependencias correctas para manejar contactos
    'data': [
        'security/ir.model.access.csv',  # Definición de permisos
        'views/inherit_res_partner.xml',
        'views/stings_key_views.xml',  # Vista de las claves API
    ],
    'installable': True,  # Correcto
    'application': True,  # Correcto si deseas que sea una aplicación visible
    'auto_install': False,  # Correcto
}

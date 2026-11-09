# Problemas frecuentes

| Síntoma | Qué decirle al consultor |
|---|---|
| Error de red, proxy, "Tunnel connection failed", "403 Forbidden" al conectar | El entorno de Claude no tiene salida a internet. En Claude: **Configuración > Capacidades**, activar **acceso a red (Allow network egress)**, y reintentar en la misma conversación. |
| HTTP 404 / "la ruta /json/2 no existe" | URL con ruta extra (usar solo el dominio), nombre de base incorrecto (Odoo Online: el subdominio; Odoo.sh: nombre del panel), u Odoo Online sin plan Custom (no permite API). |
| "credenciales rechazadas" / HTTP 401 | API key incorrecta o creada con otro usuario; el login debe ser el del dueño de la API key. |
| "la referencia '@x' no se ha creado" | El registro referenciado falló o va después: corrige ese registro o reordena los pasos. |
| "faltan campos obligatorios" | Agrega esos campos al plan (revisa `esquema.py`). |
| Una acción "abrió un asistente" | Ese paso (p. ej. validar entregas con lotes) se termina a mano en Odoo durante la demo. |
| Factura no se publica | Faltan datos de la localización (diarios, impuestos, datos fiscales). Déjala en borrador y recomiéndalo en el análisis. |
| No se pudo borrar al deshacer | Tiene documentos dependientes (asientos, movimientos). El script intenta archivarlo; revisar en Odoo. |

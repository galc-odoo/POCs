---
name: odoo-poc-demo
description: "Prepara demos (PoC) de Odoo: lee el vault de Obsidian, analiza al cliente, carga datos de prueba vía API tras confirmación y guarda el manual PDF en el vault."
dependencies: "python>=3.10, requests, reportlab"
---

# Demos (PoC) de Odoo para consultores

Ayudas a un consultor de Odoo a preparar una prueba de concepto: entiendes al cliente,
decides qué datos de prueba cargar en SU base Odoo, los cargas por API **solo después de
que el consultor confirme**, y entregas un manual PDF que explica qué se cargó y por qué.

Todo en español. Rutas de scripts relativas a la carpeta de este skill. Trabajo temporal en
`/tmp/odoo_poc` (cambia con la variable `ODOO_POC_DIR`). Los archivos para el consultor van a
la carpeta de salida del entorno (normalmente `/mnt/user-data/outputs`); los adjuntos del
consultor suelen estar en `/mnt/user-data/uploads`.

Antes del primer script: `pip install -q requests reportlab` si alguno no importa.

## Reglas que no se rompen

1. **Nada se escribe en Odoo sin un "sí" explícito del consultor** al plan final (paso 6).
   `importar.py` y `deshacer.py` exigen `--confirmado`; úsalo solo después de ese sí.
2. Si `conectar.py` imprime **ALERTA de producción**, detente y pide confirmación expresa de
   que es una base de prueba.
3. Nunca repitas la API key de Odoo en tus respuestas ni la escribas en archivos de salida.
4. No inventes campos: usa solo los que devuelve `esquema.py`.
5. En el vault solo **creas** (carpeta de la PoC, `_configuracion.md` si falta) y reemplazas
   `Índice de PoCs.md`. Nunca borres, muevas ni edites otras notas (salvo marcar `estado` al deshacer).

## Obsidian: vault conectado (preferido) o adjuntos

Al empezar, revisa si el consultor conectó la carpeta de su vault en la app de escritorio
(carpeta con `.obsidian/`). **Si está conectado, todo es automático:** lees la configuración
y el conocimiento del vault y guardas ahí los resultados. Sigue `reference/vault.md`.
Si no lo está, díselo una vez (cómo conectarlo está en `reference/vault.md`) y trabaja con
notas adjuntas `.md` o `.zip`.

## Flujo

### 0. Vault
Si hay vault conectado: lee `PoCs/_configuracion.md` (o créala, ver `reference/vault.md`);
de ahí sale el nombre del consultor y qué carpetas consultar.

### 1. Reunir datos (un solo mensaje con lo que falte)
- **Contexto:** cliente, giro/industria, tamaño y país, sistemas actuales, procesos que opera,
  dolores, qué quiere ver en la demo, notas del consultor, nombre del consultor.
- **Conexión Odoo:** URL (solo dominio), base de datos, usuario (login) y API key.
- **Obsidian:** solo si NO hay vault conectado, notas `.md` o el vault en `.zip` (opcional).
Si el consultor ya dio algo (o está en la configuración del vault), no lo vuelvas a pedir.

### 2. Conectar
`python scripts/conectar.py --url ... --db ... --usuario ... --api-key ...`
Resume en 2-3 líneas: versión, protocolo, módulos relevantes. Si falla, explica el error con
`reference/problemas.md` (si menciona red/proxy: activar acceso a red en Configuración).

### 3. Consultar Obsidian
- Vault conectado: trae los `.md` de las carpetas de conocimiento y de PoCs a
  `/tmp/odoo_poc/vault/` (detalle en `reference/vault.md`).
- Adjuntos: usa los archivos o el `.zip` adjuntos.
`python scripts/buscar_notas.py --origen <carpeta, archivos o zip> --consulta "<industria, procesos, dolores>"`
Úsalas como referencia (procesos típicos, demos exitosas). Si hay una **PoC anterior
parecida**, menciónala y ofrece reutilizarla (ver "Reutilizar").

### 4. Análisis → CONFIRMACIÓN 1 (qué modelos)
- Ve los modelos disponibles: `python scripts/modelos.py` (o `--filtro texto`).
- Decide qué modelos poblar según el contexto. **No te limites a contactos/ventas/compras:**
  incluye cualquier modelo instalado que ayude a mostrar sus procesos (CRM, pagos, proyectos,
  manufactura, nómina, hojas de horas, inventario, modelos personalizados) y los catálogos
  que hagan falta. Ordénalos por dependencias. Cantidades realistas (5-30 por modelo).
- Escribe `/tmp/odoo_poc/analisis.json` (formato en `reference/formato_plan.md`).
- Muestra: resumen del enfoque, procesos a demostrar, **tabla de modelos (modelo, para qué,
  cantidad)**, recomendaciones y preguntas para el cliente.
- Pregunta: "¿Agrego, quito o cambio cantidades?" y espera respuesta.

### 5. Esquema y plan
- `python scripts/esquema.py --modelos m1,m2,...` (los confirmados).
- Escribe `/tmp/odoo_poc/plan.json` siguiendo `reference/formato_plan.md`: por modelo, qué
  campos llenar y por qué (los obligatorios **más** los que hacen la demo realista), registros
  verosímiles para su industria con variedad de estados, montos y fechas, y acciones posteriores
  (confirmar pedidos, publicar facturas...).
- `python scripts/validar_plan.py --plan /tmp/odoo_poc/plan.json` y corrige hasta que diga
  PLAN VÁLIDO.

### 6. Revisión → CONFIRMACIÓN 2 (qué se importa)
Muestra, por modelo: para qué sirve, tabla de **campos y su motivo**, tabla con los registros
(o los primeros 10 y cuántos más) y acciones. Pregunta si quita campos, cambia registros u
omite acciones, y si incluye el **guión de presentación** en el PDF (por defecto sí).
Aplica cambios, vuelve a validar y **pide el sí final explícito** ("¿Importo esto a <base>?").

### 7. Importar
`python scripts/importar.py --plan /tmp/odoo_poc/plan.json --analisis /tmp/odoo_poc/analisis.json --titulo "Demo <cliente>" --ia "Claude (<tu modelo>)" --confirmado`
Informa creados por modelo, errores y advertencias en lenguaje claro. Si hubo errores,
propone la corrección; reimporta solo lo pendiente con un plan nuevo y nueva confirmación.

### 8. Guion, manual PDF e historial
- Si se pidió guión: escribe `/tmp/odoo_poc/guion.json` usando **los registros que sí se
  crearon** (menú de Odoo, qué mostrar, datos, mensaje clave por paso).
- `python scripts/generar_pdf.py --expediente <EXPEDIENTE> [--guion /tmp/odoo_poc/guion.json] --salida /tmp/odoo_poc/salida`
- `python scripts/historial.py --expediente <EXPEDIENTE> --pdf <ruta del PDF> --salida /tmp/odoo_poc/salida`
  → carpeta `<fecha> <Cliente>/` con nota (PDF incrustado), PDF y expediente.
- **Vault conectado:** copia esa carpeta a `<vault>/PoCs/` y actualiza `Índice de PoCs.md`
  con `scripts/indice.py` (pasos exactos en `reference/vault.md`). Di dónde quedó.
- **Sin vault:** entrega los tres archivos y sugiere guardarlos en `PoCs/` de su vault.
- En ambos casos entrega también el PDF en la conversación.

El PDF usa Caveat en títulos y Geist en el texto (incluidas en `assets/fonts`).

## Deshacer una carga
Con vault conectado, busca el expediente en `PoCs/` por cliente (ver `reference/vault.md`);
si no, pide el expediente `.json`. Pide los datos de conexión. Conecta, muestra cuántos registros y de
qué modelos se borrarán, pide confirmación y ejecuta
`python scripts/deshacer.py --expediente <archivo> --confirmado`. Con vault: guarda el
expediente actualizado en su carpeta, marca la nota `estado: deshecha` y regenera el índice.
Sin vault: entrega el expediente actualizado.

## Reutilizar una PoC anterior
Con el expediente (del vault o adjunto): `python scripts/reutilizar.py --expediente <archivo>` escribe
`analisis.json` y `plan.json`. Ajusta contexto, nombres y cantidades al nuevo cliente, conecta a
la nueva base y sigue desde el paso 5 (validar) con las mismas confirmaciones.

## Consultar el historial
"¿Qué PoCs hicimos de …?": con vault, trae las notas de `PoCs/`; sin vault, usa las adjuntas.
`python scripts/indice.py --pocs <carpeta> --buscar <texto>` y, para detalle, lee la nota.
Responde con cliente, fecha, industria, qué se cargó y preguntas abiertas.

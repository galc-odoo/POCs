# Trabajar con el vault de Obsidian conectado

## Cómo saber si hay vault conectado

Hay vault conectado cuando tienes herramientas para ver carpetas de la computadora del
consultor (carpetas conectadas / de confianza en la app de escritorio) y una de ellas, o una
subcarpeta directa, contiene la carpeta oculta `.obsidian/`. Esa carpeta es la **raíz del
vault**. Si hay varias, pregunta cuál usar.

Si no hay ninguna carpeta conectada, dile al consultor (una sola vez):
"Para que lea y guarde en tu vault automáticamente, en la app de escritorio de Claude dame
acceso a la carpeta de tu vault de Obsidian (la carpeta principal, la que contiene
`.obsidian`). Mientras, puedes adjuntar notas o el vault en .zip." Y sigue con adjuntos.

## Configuración: `PoCs/_configuracion.md`

Si no existe, créala la primera vez. Pregunta el nombre del consultor y qué carpetas tienen
conocimiento de Odoo (muéstrale las carpetas de primer nivel del vault; omite `.obsidian`,
`.trash` y la de PoCs). Formato:

```markdown
---
tipo: configuracion-poc
consultor: "Ana López"
carpeta_pocs: "PoCs"
carpetas_conocimiento:
  - "Odoo"
  - "Industrias"
  - "Clientes"
---

# Configuración del skill de PoCs

Claude lee este archivo al empezar cada PoC. Edítalo para cambiar el consultor o las
carpetas que se consultan.
```

Si ya existe, léela al empezar y úsala sin preguntar.

## Leer conocimiento

1. Trae al entorno de trabajo (`/tmp/odoo_poc/vault/`) **solo los `.md`** de las
   `carpetas_conocimiento` y de `carpeta_pocs` (no PDFs, imágenes ni JSON).
   - Si son muchas notas (más de ~400), y tienes terminal en la computadora del consultor,
     busca ahí primero (por ejemplo con grep por industria/procesos) y trae solo las que coincidan.
2. `python scripts/buscar_notas.py --origen /tmp/odoo_poc/vault --consulta "<industria, procesos, dolores>"`
3. Las PoCs anteriores parecidas (misma industria o procesos) son la mejor referencia:
   menciónalas en el análisis y ofrece reutilizar su expediente.

## Guardar resultados

Después de generar el PDF:

1. `python scripts/historial.py --expediente <EXPEDIENTE> --pdf <ruta del PDF> --salida /tmp/odoo_poc/salida`
   → crea `/tmp/odoo_poc/salida/<fecha> <Cliente>/` con la nota, el PDF y el expediente.
2. Copia esa carpeta completa a `<vault>/<carpeta_pocs>/`. Si ya existe una carpeta con ese
   nombre (misma PoC el mismo día), agrega " (2)" al nombre; nunca sobrescribas otra PoC.
3. Actualiza el índice: trae las notas `.md` de `<vault>/<carpeta_pocs>/` (incluida la nueva),
   ejecuta `python scripts/indice.py --pocs <esa carpeta> --salida /tmp/odoo_poc/salida` y
   escribe `Índice de PoCs.md` en `<vault>/<carpeta_pocs>/` (reemplazando el anterior).
4. Dile al consultor dónde quedó: "Guardé la PoC en tu vault: PoCs/<fecha> <Cliente>/".
   Además entrega el PDF en la conversación para que lo descargue directo.

## Deshacer o reutilizar desde el vault

- Si el consultor pide deshacer o reutilizar la PoC de un cliente, busca en
  `<vault>/<carpeta_pocs>/` la carpeta y su `expediente_*.json` (si hay varias, muestra fechas
  y pregunta). Tráelo al entorno de trabajo y sigue el flujo normal.
- Después de deshacer: escribe el expediente actualizado de vuelta en su carpeta, cambia en la
  nota la propiedad `estado: cargada` por `estado: deshecha`, y regenera el índice.

## Consultar el historial

"¿Qué PoCs hicimos para distribuidoras?" → trae las notas de `carpeta_pocs` y usa
`python scripts/indice.py --pocs <carpeta> --buscar distribu`. Para el detalle, lee la nota.

## Cuidado

- Nunca borres ni muevas notas existentes del vault. Solo crea la carpeta de la PoC,
  `_configuracion.md` (si falta) y reemplazas `Índice de PoCs.md`.
- La API key de Odoo nunca se escribe en el vault.

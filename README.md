# Odoo Skills

Skills de Claude para consultores de Odoo. Hoy incluye:

| Plugin | Skill | Qué hace |
|---|---|---|
| `odoo-poc` | `odoo-poc-demo` | Prepara demos (PoC): analiza al cliente, carga datos de prueba en su base por API tras confirmación y entrega el manual PDF. |

## Instalar (Claude Code o app de escritorio)

Necesitas acceso al repo (pídele a galc-odoo que te invite) y que `git` pueda leerlo
(si `git clone https://github.com/galc-odoo/POCs` funciona, ya está).

En Claude Code escribe:

```
/plugin marketplace add galc-odoo/POCs
/plugin install odoo-poc@odoo-skills
```

Reinicia la sesión y el skill queda disponible como `odoo-poc:odoo-poc-demo`.

## Recibir las actualizaciones

Cada cambio que entra a `main` es una versión nueva.

- **Automático:** `/plugin` → pestaña *Marketplaces* → `odoo-skills` → *Enable auto-update*.
  Como el repo es privado, para que se actualice en segundo plano define `GITHUB_TOKEN`
  en tu shell (un token de GitHub con permiso de lectura al repo).
- **Manual:** `/plugin marketplace update odoo-skills` y reinicia la sesión.

## Proponer mejoras

Lee [CONTRIBUTING.md](CONTRIBUTING.md). En corto: rama nueva → cambios → Pull Request a `main`.

## Estructura

```
.claude-plugin/marketplace.json        catálogo de plugins del repo
plugins/odoo-poc/
  .claude-plugin/plugin.json           datos del plugin
  skills/odoo-poc-demo/                el skill (SKILL.md, scripts, reference, assets)
```

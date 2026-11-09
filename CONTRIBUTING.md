# Cómo proponer mejoras

## Ramas

- **`main`**: la versión que usan todos. Está protegida: nadie sube directo, todo entra por
  Pull Request revisado por galc-odoo. Lo que se fusiona en `main` les llega a todos los
  consultores en su siguiente actualización.
- **Ramas de trabajo**, una por mejora, salen de `main`:
  - `mejora/<tema>`: algo nuevo o mejor (ej. `mejora/datos-inventario`)
  - `fix/<tema>`: corrige algo que falla (ej. `fix/importar-monedas`)
  - `docs/<tema>`: solo textos o guías

## Paso a paso

```bash
git clone https://github.com/galc-odoo/POCs.git
cd odoo-skills
git switch -c mejora/mi-tema
```

1. Edita lo que necesites en `plugins/odoo-poc/skills/odoo-poc-demo/`.
2. Pruébalo sin instalar nada, cargando el plugin desde tu copia:
   ```bash
   claude --plugin-dir plugins/odoo-poc
   ```
3. Sube la rama y abre el Pull Request:
   ```bash
   git add -A
   git commit -m "Qué mejoraste"
   git push -u origin mejora/mi-tema
   ```
   GitHub te muestra el enlace para crear el Pull Request. Llena la plantilla.
4. GitHub corre una validación automática (JSON, SKILL.md, scripts y que no haya claves).
   Cuando pasa y galc-odoo lo aprueba, se fusiona en `main`.

Antes de empezar otra mejora, actualiza tu copia: `git switch main && git pull`.

## Reglas

- Nunca subas API keys, contraseñas, ni datos o documentos reales de clientes.
- Las rutas personales (tu vault de Obsidian, carpetas propias) van en tu
  `~/.claude/CLAUDE.md`, no en el skill.
- Un Pull Request por mejora, con una explicación de qué problema resuelve.

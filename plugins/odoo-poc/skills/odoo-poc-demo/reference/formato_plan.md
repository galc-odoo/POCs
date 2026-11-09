# Formatos de archivo del skill

## analisis.json

```json
{
  "consultor": "Ana López",
  "contexto": {
    "cliente": "Eléctrica del Norte",
    "industria": "Distribución de material eléctrico",
    "tamano_y_pais": "45 empleados, México",
    "sistemas_actuales": "Excel + CONTPAQi",
    "procesos": "Venta a crédito a constructoras, 2 almacenes",
    "dolores": "No saben qué clientes deben",
    "objetivo_demo": "Cobranza y pedidos a entregas",
    "notas_consultor": ""
  },
  "resumen": "Enfoque de la demo en 3-5 frases.",
  "procesos_a_demostrar": ["Venta a crédito -> entrega -> factura -> cobranza"],
  "modelos": [
    {"model": "res.partner", "motivo": "Constructoras con límite de crédito", "cantidad": 12}
  ],
  "recomendaciones": ["Activar límites de crédito en Contabilidad"],
  "preguntas_al_consultor": ["¿Manejan listas de precios por cliente?"],
  "notas_obsidian": ["Industrias/Distribución.md"]
}
```

## plan.json

Lista de pasos en orden de carga (lo que otros referencian va primero):

```json
[
  {
    "model": "res.partner",
    "descripcion": "Clientes constructoras",
    "motivo": "Mostrar crédito y cobranza por cliente",
    "campos": [
      {"campo": "name", "motivo": "Razón social"},
      {"campo": "is_company", "motivo": "Son empresas"},
      {"campo": "email", "motivo": "Contacto de cobranza"}
    ],
    "registros": [
      {"ref": "cli_norte", "valores": {"name": "Constructora Norte", "is_company": true,
                                        "email": "pagos@norte.mx", "country_id": {"$buscar": "México"}}}
    ],
    "acciones": []
  },
  {
    "model": "sale.order",
    "descripcion": "Pedidos a crédito",
    "motivo": "Flujo de venta completo",
    "campos": [{"campo": "partner_id", "motivo": "Cliente"}, {"campo": "order_line", "motivo": "Productos"}],
    "registros": [
      {"ref": "so_1", "valores": {"partner_id": "@cli_norte", "date_order": "$hoy-12",
        "order_line": [{"product_id": "@prod_cable", "product_uom_qty": 200, "price_unit": 18.5}]}}
    ],
    "acciones": [{"metodo": "action_confirm", "descripcion": "Confirmar pedido", "refs": ["so_1"]}]
  }
]
```

- `campos`: lo que el consultor aprueba. Si quita un campo, quítalo también de los registros.
- `acciones`: sin `refs` se aplica a todos los registros del paso.
- `ref`: único y legible en todo el plan.

### Reglas de valores

| Tipo de campo | Cómo se escribe |
|---|---|
| many2one a un registro del plan | `"@ref"` (debe crearse en un paso anterior o antes en el mismo paso) |
| many2one a un registro existente | id numérico de `esquema.py` o `{"$buscar": "texto"}` |
| many2many | lista con los valores anteriores: `["@vip", 3]` |
| Líneas (one2many de la sección `lineas`) | lista de objetos con sus campos |
| Fecha / fecha-hora | `"2026-10-01"`, `"2026-10-01 10:00:00"` o relativas `"$hoy"`, `"$hoy-30"`, `"$hoy+15"` |
| selection | una clave de `opts` |

No incluyas campos calculados, de solo lectura, ni `id`.

### Consejos por proceso
- **Ventas/Compras:** productos (`product.template` o `product.product`) antes que pedidos. Acciones: `action_confirm` (venta), `button_confirm` (compra).
- **Facturas:** `account.move` con `move_type` (`out_invoice`/`in_invoice`), `partner_id`, `invoice_date`, `invoice_line_ids`. Acción: `action_post`. Si la localización exige datos fiscales (CFDI, RFC), deja las facturas en borrador y dilo.
- **Pagos:** registra `account.payment` solo si el modelo y diarios existen; si no, recomienda registrarlos desde la factura durante la demo.
- **Inventario:** almacenes (`stock.warehouse`) y ubicaciones antes que movimientos; validar transferencias puede abrir asistentes: avisa que se terminan en Odoo.
- **CRM:** `crm.lead` con `type` = `opportunity`, etapas (`stage_id`) variadas y `expected_revenue`.
- Varía estados, fechas y montos para que tableros y reportes se vean interesantes.

## guion.json

```json
{
  "introduccion": "Cómo abrir la demo (2-3 frases).",
  "pasos": [
    {"titulo": "Pedido a crédito", "menu": "Ventas > Pedidos", "que_mostrar": "…",
     "datos": "Pedido so_1 de Constructora Norte", "mensaje_clave": "Beneficio para el cliente"}
  ],
  "cierre": "Cómo cerrar y siguientes pasos."
}
```

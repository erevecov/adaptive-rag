# Proposal M34 runtime model catalog

## Why

M33 entrego Runtime settings, pero la UI todavia obliga al usuario a escribir
IDs internos de connections y IDs reales de modelos. Eso no escala: los IDs de
sistema deben generarse solos, y los modelos disponibles deben elegirse desde
un catalogo persistido por provider connection.

Qwen/DashScope expone listado de modelos en el SDK oficial mediante
`Models.list(page, page_size)` y los endpoints OpenAI-compatible/locales suelen
exponer `GET /models`. El listado de modelos puede devolver IDs y metadata, pero
el pricing publico esta documentado aparte y no debe inferirse si la API no lo
devuelve.

## What Changes

- Agregar un catalogo global de modelos por provider connection.
- Agregar creacion de provider connection con `connection_id` generado por el
  backend.
- Mantener el endpoint legacy `PUT /connections/{connection_id}` para scripts y
  compatibilidad.
- Agregar sync de modelos por connection usando APIs provider/local cuando
  existan.
- Guardar `model_id` real del provider, capabilities asociadas, metadata segura
  y pricing opcional si el provider lo entrega.
- Cambiar Runtime settings UI para usar selects de connection/model en slots,
  chat pool, secrets y project overrides.

## Out of Scope

- No administrar pricing mediante scraping o tablas mantenidas a mano.
- No validar cada modelo contra llamadas live antes de guardarlo.
- No hacer dynamic slots.
- No eliminar endpoints legacy que aceptan `model_id` directo.
- No exponer secrets al frontend durante sync.

## Validation

- Tests backend de repository/API/model lister.
- Tests frontend de API client y Runtime settings UI.
- OpenSpec strict.
- Browser QA sobre Runtime settings.

# provider-runtime Specification

## ADDED Requirements

### Requirement: Provider model catalog uses generated system IDs

El sistema MUST generar IDs internos de provider connection cuando el usuario
crea una connection desde las superficies de producto, y MUST persistir los IDs
reales de modelos separados de esos IDs internos.

#### Scenario: Connection create generates internal ID

- **WHEN** un usuario crea una provider connection sin indicar `connection_id`
- **THEN** el backend genera un ID interno estable y unico
- **AND** la respuesta devuelve ese ID para referencias futuras
- **AND** el usuario no necesita memorizar ni escribir ese ID

#### Scenario: Legacy upsert keeps explicit ID support

- **WHEN** un script o test usa `PUT /runtime-settings/connections/{id}`
- **THEN** el backend conserva ese contrato
- **AND** valida provider, tipo y capabilities igual que antes

### Requirement: Provider model catalog persists real model IDs

El sistema MUST mantener un catalogo global de modelos por provider connection
con IDs reales de provider y metadata segura.

#### Scenario: Model sync stores provider IDs

- **WHEN** un usuario sincroniza modelos para una provider connection
- **THEN** el backend consulta el provider o endpoint local configurado
- **AND** persiste cada `model_id` real bajo esa connection
- **AND** no persiste ni retorna API keys, Authorization headers ni ciphertext

#### Scenario: Model list can filter by slot capability

- **WHEN** el frontend solicita modelos para una connection y capability
- **THEN** el backend devuelve solo modelos catalogados compatibles
- **AND** incluye metadata segura y pricing solo si el provider lo entrego

#### Scenario: Pricing absence is explicit

- **WHEN** la API de listado del provider no devuelve pricing
- **THEN** el catalogo guarda `pricing` como `null`
- **AND** no inventa costos desde tablas externas ni defaults locales

#### Scenario: Provider listing failure is stable

- **WHEN** el provider no soporta model listing o responde con formato invalido
- **THEN** el sync devuelve un error estable
- **AND** conserva el catalogo previo sin exponer secretos

## ADDED Requirements

### Requirement: URL fetch policy valida destinos antes de descargar

El sistema MUST validar URLs antes de descargar contenido remoto.

#### Scenario: Solo HTTP y HTTPS son permitidos

- **WHEN** se valida una URL con scheme distinto de `http` o `https`
- **THEN** la policy la rechaza

#### Scenario: Hosts internos o no globales son bloqueados

- **WHEN** el hostname resuelve a loopback, private, link-local, multicast, unspecified o reserved IP
- **THEN** la policy rechaza la URL

#### Scenario: Credenciales embebidas son bloqueadas

- **WHEN** una URL incluye username o password
- **THEN** la policy la rechaza

### Requirement: Redirects se validan manualmente

El sistema MUST seguir redirects solo despues de validar cada destino.

#### Scenario: Redirect seguro se sigue

- **WHEN** una respuesta redirect apunta a otra URL HTTP(S) permitida
- **THEN** el fetcher valida el destino y continua la descarga

#### Scenario: Redirect hacia destino interno se bloquea

- **WHEN** una respuesta redirect apunta a una URL que resuelve a IP no global
- **THEN** el fetcher rechaza el redirect antes de descargar el destino

#### Scenario: Exceso de redirects se bloquea

- **WHEN** la cadena de redirects supera `max_redirects`
- **THEN** el fetcher falla con un error de policy

### Requirement: Content type y tamano de respuesta son limitados

El sistema MUST limitar los content types y el tamano de bytes descargados.

#### Scenario: Content type no permitido se rechaza

- **WHEN** una respuesta final tiene `Content-Type` fuera de la allowlist
- **THEN** el fetcher rechaza la respuesta antes de consumir el cuerpo

#### Scenario: Content-Length excede el limite

- **WHEN** una respuesta final declara `Content-Length` mayor que `max_response_bytes`
- **THEN** el fetcher rechaza la respuesta antes de consumir el cuerpo

#### Scenario: Stream excede el limite

- **WHEN** una respuesta sin `Content-Length` excede `max_response_bytes` mientras se lee
- **THEN** el fetcher detiene la lectura y falla con error de tamano


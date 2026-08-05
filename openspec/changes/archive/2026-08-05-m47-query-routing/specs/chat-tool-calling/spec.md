## ADDED Requirements

### Requirement: Chat retrieval tool honors query routing

The chat retrieval tool MUST consult the query router before calling the
retrieval service and MUST skip retrieval when the route is `skip_retrieval`.

#### Scenario: Skip route does not call retrieval service

- **WHEN** the router returns `skip_retrieval` for a query
- **THEN** the retrieval tool returns zero results
- **AND** does not invoke the underlying retrieval service search

#### Scenario: Dense_sparse route uses dense_sparse strategy

- **WHEN** the router returns `dense_sparse`
- **THEN** the retrieval tool requests strategy `dense_sparse`

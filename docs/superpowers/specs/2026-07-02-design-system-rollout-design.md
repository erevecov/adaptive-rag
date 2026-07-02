# Design System Rollout Readiness Spec

## Objetivo

Dejar la aplicacion lista para una implementacion completa de estilos inspirada en Vercel: minima, moderna, densa cuando corresponde, basada en tokens semanticos y migrada por superficies verificables. Esta spec no cambia la UI todavia; fija el inventario, el contrato visual, el orden de migracion y los gates que debe cumplir el siguiente trabajo.

## Estado actual verificado

- `origin/main` contiene el PR #163 con la fundacion de Tailwind v4 + shadcn-ready.
- `frontend/components.json` esta configurado con `style: "new-york"`, `baseColor: "neutral"`, CSS variables, alias `@/*` y `iconLibrary: "lucide"`.
- `frontend/src/index.css` define tokens semanticos compatibles con Tailwind v4 via `@theme inline`.
- El contrato de tema usa `[data-theme='dark']` y `[data-theme='purple']`, y Tailwind `dark:` esta ligado a `.dark` con `@custom-variant dark (&:where(.dark, .dark *));`.
- Ya existen primitives en `frontend/src/components/ui`: `Button`, `IconButton`, `NavSection`, `SidebarItem`, `Panel`, `PanelHeader`, `PanelTitle`, `PanelDescription`, `PanelBody`, `Field`, `FieldLabel`, `FieldControl`, `FieldHelp`, `FieldError`.
- `frontend/src/App.tsx` sigue concentrando la mayoria de la UI y mide aproximadamente 8937 lineas.
- `frontend/src/App.css` sigue concentrando el styling legacy y mide aproximadamente 3859 lineas.
- `frontend/src/App.test.tsx` contiene la cobertura principal de flujos UI y mide aproximadamente 3881 lineas.

## Problema

La fundacion ya permite construir con primitives y tokens, pero el sistema visual todavia no esta listo para una migracion total de una vez. `App.css` mantiene muchos selectores globales, colores hardcoded, sombras, estados y overrides por tema que pueden pisar utilities y primitives. `App.tsx` mantiene muchas funciones presentacionales locales, por lo que un restyle completo sin slicing mezclaria estilo, estructura y comportamiento en un PR demasiado grande.

## Opciones consideradas

### Opcion A: Big bang sobre toda la app

Migrar todos los estilos y componentes en un solo PR.

Pros:
- Resultado visual completo en una sola entrega.
- Menos tiempo con dos sistemas conviviendo.

Contras:
- Alto riesgo de regressions en chat, runtime, authoring, observability e inspector al mismo tiempo.
- PR dificil de revisar.
- Dificil aislar fallos de CSS cascade, responsive layout o comportamiento.

### Opcion B: Rollout por vertical slices

Migrar superficies completas una por una, empezando por Runtime Settings / Provider Connections.

Pros:
- Cada PR produce una mejora visible y testeable.
- Permite validar primitives reales antes de aplicarlas al resto.
- Reduce conflictos con `App.css` y permite borrar CSS legacy de forma incremental.

Contras:
- Durante el rollout conviven estilo nuevo y legacy.
- Requiere disciplina para no duplicar primitives por slice.

### Opcion C: Nueva capa visual paralela antes de migrar pantallas

Crear una libreria UI interna mas amplia, sin migrar pantallas aun.

Pros:
- Buen contrato antes de tocar flujos complejos.
- Facilita consistencia.

Contras:
- Riesgo de abstraer componentes antes de usarlos.
- Puede producir primitives que no calzan con las necesidades reales de `App.tsx`.

## Decision

Usar Opcion B. El rollout debe migrar una superficie representativa completa, validar el contrato visual y luego repetir el patron. La primera slice recomendada es Runtime Settings / Provider Connections porque contiene formularios, selects, listas, status, acciones destructivas, empty states, carga, errores y layout denso.

## Contrato visual

- Base visual: minimalismo tipo Vercel, neutral, moderno, con bordes finos, fondos planos y foco claro.
- Paleta: usar tokens semanticos (`background`, `foreground`, `card`, `muted`, `accent`, `border`, `input`, `ring`, `destructive`) y evitar nuevos colores hardcoded fuera de `index.css`.
- Radios: mantener `--radius: 8px`; cards y controls no deben exceder 8px salvo caso justificado.
- Espaciado: grids y panels compactos; evitar composicion marketing, hero sections, orbs, blobs o gradientes decorativos.
- Tipografia: texto funcional y escaneable; headings moderados dentro de panels; no usar hero-scale type en dashboards o forms.
- Estados: focus visible con `ring`, hover sutil, disabled sin layout shift, destructive con token `destructive`.
- Accesibilidad: primitives label-driven para icon buttons; active navigation con `aria-current="page"`; alerts con `role="alert"`; controls nativos con labels reales.
- Responsive: grids deben degradar a una columna, sidebars no deben cubrir contenido de forma incoherente, labels deben truncar sin romper layout.

## Inventario de superficies

### Shell y navegacion

- Archivos principales: `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/components/ui/nav.tsx`, `frontend/src/components/ui/button.tsx`.
- Estado: parcialmente migrado con `IconButton` y `SidebarItem`.
- Riesgo: medio. CSS legacy del sidebar aun define muchas reglas especificas.
- Objetivo final: sidebar, project selector, primary nav, contextual nav y session rail deben usar primitives y tokens.

### Runtime Settings y Provider Connections

- Archivos principales: `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/lib/apiClient.ts`, `frontend/src/App.test.tsx`.
- Componentes locales: `RuntimeSettingsPanel`, `RuntimeConnectionsPanel`, `CapabilitySelector`, `RuntimeModelCatalogPanel`, `RuntimeGlobalDefaultsPanel`, `RuntimeProjectOverridesPanel`, `ConnectionSecretSummary`, `ConnectionCheckSummary`, `ConnectionSelect`, `ProviderModelSelect`, `ProviderModelCatalogView`, `RuntimeSlotList`, `ProjectRuntimeSettingsView`.
- Estado: funcional, con CSS legacy para forms, rows, destructive actions, capability tokens y connection status.
- Riesgo: medio-alto por muchos estados, pero es la mejor primera slice porque concentra la mayoria de patrones reusables.
- Objetivo final: crear primitives faltantes y aplicar UI tokens sin cambiar endpoints ni estado.

### Authoring

- Componentes locales: `AuthoringPanel`, `ProjectAccessPanel`, `UserAccessLists`, `KnowledgeReviewPanel`, `SourceList`, `IngestionJobsPanel`, `IngestionJobList`.
- Estado: comparte `authoring-*`, `compact-list`, `field`, `panel` y row styles legacy.
- Riesgo: medio por listas y forms con acciones.
- Objetivo final: reutilizar los patterns validados en Runtime.

### Chat y respuesta

- Componentes locales: `SpeechInputControl`, `ResponsePanel`, `ResponseContent`, `QuestionPrompt`, `ResponseDetailsPanel`, `ResponseDetailsContent`, `ResponseUsageStrip`, `KnowledgeDraftCard`.
- Componentes relacionados: `ChatPipelineSteps`.
- Estado: estilos densos y sensibles al responsive.
- Riesgo: alto por streaming, transcript scroll, sticky prompt, details y pipeline.
- Objetivo final: migrar despues de validar forms/lists porque aqui cualquier layout shift afecta el flujo principal.

### History, inspector y session detail

- Componentes locales: `SessionNavigationPanel`, `WorkspaceInspectorPanel`, `ConversationMinimap`, `SessionContextPanel`, `InternalActionStepper`, `SessionDetailPanel`, detail row renderers.
- Estado: mezcla navigation, lists, panels y overlay/inline inspector.
- Riesgo: alto por responsive y dock inline.
- Objetivo final: migrar despues del chat o junto con una slice de shell avanzada.

### Observability

- Componentes locales: `ObservabilityPanel`, `ObservabilityContent`, `ObservabilitySummaryContent`, `ObservabilitySummaryMetrics`, `ObservabilityCostsContent`, `ObservabilityErrorsContent`, `ObservabilityLatencyContent`, `ObservabilityBreakdowns`, `ProviderUsageTable`, `ProviderLatencyTable`, `MetricCard`.
- Estado: data-dense, tablas, metric cards y status breakdown.
- Riesgo: medio. Menos comportamiento interactivo que chat, pero necesita densidad y legibilidad.
- Objetivo final: migrar despues de Runtime para validar tables, metric cards y data lists.

### Appearance

- Componentes locales: `AppearanceSettingsPanel`.
- Estado: pequeno, pero depende del contrato de temas.
- Riesgo: bajo.
- Objetivo final: usarlo como smoke visual de light/dark/purple despues de cada slice.

## Primitives faltantes para el rollout

- `Input`, `Textarea`, `NativeSelect`: controles nativos tokenizados para reemplazar `.field input`, `.field select`, `.field textarea`.
- `SegmentedControl` o `Tabs`: para view switchers, inspector tabs, observability filters y session filters.
- `Badge` y `StatusBadge`: para status, capabilities, job status, connection type y scores.
- `DataList`, `DataListItem`, `ActionRow`: para authoring rows, connection rows, session rows y compact lists.
- `EmptyState` y `InlineFeedback`: para empty copy, errors, history errors y form feedback.
- `Surface` o `CardSection`: si `Panel` queda demasiado generico para nested dashboard sections.
- `Table` wrapper: para observability provider tables, con scroll container y density rules.

## Rollout order

1. Runtime Settings / Provider Connections.
2. Runtime Model Catalog / Global Defaults / Project Overrides.
3. Authoring forms and lists.
4. Observability metrics and tables.
5. Chat response surfaces and pipeline.
6. History, inspector and session detail.
7. Shell cleanup and CSS removal pass.

## Guardrails

- Cada slice debe borrar o reducir CSS legacy relacionado; no solo agregar classes nuevas encima.
- No mover business logic si no es necesario para la slice.
- Cuando se extraigan componentes desde `App.tsx`, empezar por presentational components con props explicitas; mantener handlers y state ownership en `App` hasta que haya una razon clara para moverlos.
- No introducir una libreria nueva en medio de una slice salvo que el componente lo justifique. Si se agrega Radix/shadcn para Select, Dialog, Tabs o Tooltip, debe ser en un PR pequeno y con tests de accesibilidad.
- Mantener `Button`/`IconButton` como contrato de acciones hasta que haya una razon concreta para reemplazarlos.
- Mantener `dark` y `purple` cubiertos: cualquier `dark:` utility debe funcionar con la clase `.dark`, no solo con `[data-theme='dark']`.

## Gates de verificacion

Cada slice debe correr:

```powershell
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
```

Cada slice visual debe incluir browser QA:

- Desktop: shell open/closed, active nav, forms, focus states, no overlapping text.
- Mobile cerca de 390px: sidebar, panel stacking, truncation, icon button sizing, form controls.
- Themes: light, dark, purple en la superficie migrada.
- Console: sin errores.

## Resultado esperado antes de empezar la implementacion completa

El equipo debe tener:

- Una primera slice recomendada: Runtime Settings / Provider Connections.
- Un inventario de superficies y riesgos.
- Una lista de primitives faltantes.
- Un orden de migracion por PRs.
- Un plan de ejecucion task-by-task para implementar la migracion completa.

# V1 Product Scope Reset Plan

## Objetivo

Cambiar la definicion de v1: deja de ser una release de portafolio recortada y
pasa a significar producto local-first terminado para un usuario. M21 queda
como evidencia de core/pre-v1, no como autorizacion para tag v1.0.

## Alcance

- Crear el change OpenSpec `m22-v1-product-scope-reset`.
- Definir la nueva capability `v1-product-completion`.
- Modificar el contrato de `v1-release-readiness` para bloquear tag/release v1
  hasta que `v1-product-completion` este satisfecha.
- Actualizar `docs/progress.md`, `docs/roadmap.md`,
  `docs/architecture/v1-design.md` y `README.md` para que no recomienden cortar
  v1.0 todavia.

## Pasos

1. Crear propuesta, diseno, tasks y deltas de spec para M22.
2. Reconciliar los docs de estado para declarar M22 como milestone activo.
3. Replantear `v1-design.md` y README con el nuevo significado de v1.
4. Validar OpenSpec y whitespace.
5. Commit, push y PR.

## Validacion

- `npx --yes @fission-ai/openspec validate m22-v1-product-scope-reset --strict`
- `npx --yes @fission-ai/openspec validate --specs --strict`
- `npx --yes @fission-ai/openspec list`
- `git diff --check`

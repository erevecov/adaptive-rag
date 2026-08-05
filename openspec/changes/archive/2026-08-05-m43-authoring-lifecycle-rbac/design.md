# Diseno M43

- Soft delete via `deleted_at` on projects/sources (Alembic migration).
- List/get ignore soft-deleted rows by default.
- Source soft-delete removes documents/versions/chunks/sparse embeddings for that source.
- Roles: project update admin; source update contributor; source/project delete admin/superadmin; membership delete admin; user deactivate + token revoke superadmin.

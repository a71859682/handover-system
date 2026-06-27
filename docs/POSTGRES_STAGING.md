# PostgreSQL Staging

## Purpose

Prepare a PostgreSQL staging environment for validation without changing the current production site.

## Render Setup Flow

1. Create a new PostgreSQL database in Render
2. Open the database dashboard in Render
3. Copy the Internal Database URL
4. Apply the URL only to a staging service such as `handover-system-dev` or another dedicated staging service

## Important Rules

- Use the Internal Database URL
- Do not apply the PostgreSQL URL to the production `handover-system` service yet
- Use PostgreSQL only for `handover-system-dev` or another staging environment
- The production site currently remains on SQLite

## Current Scope

- Validate connectivity
- Validate application configuration
- Do not switch the production runtime
- Do not run schema migration against the production SQLite database

# VMI EcoSystem Documentation Pack

This folder is a migration-oriented study of the current Flask application.
It is intended for an engineer or AI agent that needs to understand the
existing project and rebuild it as a Django application with equivalent
features.

## Recommended Reading Order

1. `01-project-study.md`
   - High-level purpose, app boundaries, user roles, and feature inventory.
2. `02-backend-architecture.md`
   - Flask app structure, blueprints, services, authentication, permissions,
     formula evaluation, file storage, and background assumptions.
3. `03-database-model-map.md`
   - SQLAlchemy model map with Django model suggestions, key fields,
     relationships, constraints, and migration notes.
4. `04-route-and-workflow-map.md`
   - Route inventory and how each user workflow behaves.
5. `05-frontend-guide.md`
   - Template layout, CSS system, JavaScript behavior, and frontend migration
     notes.
6. `06-django-migration-guide.md`
   - Practical rebuild plan for Django, suggested apps, data migration
     sequence, and parity checklist.

## Source App Summary

The active Flask app lives in:

```text
reporting_system/
  app/
    blueprints/
    models/
    services/
    static/
    templates/
  migrations/
  manage.py
  wsgi.py
```

The project also has root-level deployment files and a root
`database_schema.md` snapshot.

## Important Current Behavior

- Authentication uses Flask-Login and Werkzeug password hashes.
- Authorization is rank-based and page-based through `AccessPermission`.
- Core KPI reporting uses base metrics, derived metrics, formulas, reporting
  periods, metric values, and per-value targets.
- Metric targets support both single target and target range:
  - `target_type = single` uses `metric_values.target`.
  - `target_type = range` uses `metric_values.target_lower` and
    `metric_values.target_upper`.
- Derived metric formulas are safely parsed with Python AST. The app does not
  use raw `eval`.
- Documents and sales guideline files use Cloudflare R2 through a boto3
  S3-compatible client.
- Frontend is Jinja2 templates, one global CSS file, and vanilla JavaScript.

## Migration Goal

For a Django duplicate, preserve the existing database semantics first, then
improve structure after parity is proven. The highest-risk logic to port
faithfully is:

- Rank/page permission behavior.
- Metric scoping by team.
- Formula validation and evaluation.
- Weekly reporting period generation.
- Data entry target carry-forward.
- Single target versus target range evaluation.
- File upload/open/delete behavior with R2.
- Journal table save behavior.


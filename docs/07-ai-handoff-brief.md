# AI Handoff Brief for Django Rebuild

Use this file as the first prompt/context file for an AI agent that will
rebuild the current Flask app in Django.

## Objective

Rebuild the existing VMI internal reporting system as a Django application with
feature parity before doing any redesign or refactor. Preserve business logic,
permissions, database semantics, and user workflows.

## Existing App Location

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

## Read These Docs First

```text
docs/README.md
docs/01-project-study.md
docs/02-backend-architecture.md
docs/03-database-model-map.md
docs/04-route-and-workflow-map.md
docs/05-frontend-guide.md
docs/06-django-migration-guide.md
```

## Read These Source Files Next

Core:

```text
reporting_system/app/__init__.py
reporting_system/app/config.py
reporting_system/app/extensions.py
reporting_system/app/templates/base.html
```

Models:

```text
reporting_system/app/models/user.py
reporting_system/app/models/team.py
reporting_system/app/models/metric.py
reporting_system/app/models/access_permission.py
reporting_system/app/models/document.py
reporting_system/app/models/document_folder.py
reporting_system/app/models/sales_team.py
reporting_system/app/models/experience_team_deal.py
reporting_system/app/models/team_process.py
reporting_system/app/models/journal.py
reporting_system/app/models/graph_settings.py
```

Services:

```text
reporting_system/app/services/access_service.py
reporting_system/app/services/metrics_service.py
reporting_system/app/services/formula_service.py
reporting_system/app/services/r2_service.py
reporting_system/app/permissions.py
```

Critical routes:

```text
reporting_system/app/blueprints/auth/routes.py
reporting_system/app/blueprints/dashboard/routes.py
reporting_system/app/blueprints/reporting/routes.py
reporting_system/app/blueprints/settings/routes.py
reporting_system/app/blueprints/documents/routes.py
reporting_system/app/blueprints/sales_team/routes.py
reporting_system/app/blueprints/experience_team/routes.py
reporting_system/app/blueprints/team_processes/routes.py
reporting_system/app/blueprints/journal/routes.py
```

Frontend:

```text
reporting_system/app/static/css/main.css
reporting_system/app/static/js/main.js
reporting_system/app/blueprints/**/templates/**/*.html
```

Database:

```text
database_schema.md
reporting_system/migrations/versions/
```

## Non-Negotiable Parity Rules

1. Do not replace the permission model with generic Django permissions until
   page/rank behavior matches the Flask app.
2. Do not use Python `eval` for metric formulas. Port `FormulaService`.
3. Derived metrics must be calculated in layer order.
4. Preserve metric scoping:
   - global metrics
   - direct `team_id`
   - many-to-many `scoped_teams`
5. Preserve reporting period generation from ISO week 40 through next week.
6. Preserve data-entry availability: the two completed weeks before the latest
   generated week.
7. Preserve target behavior:
   - single target stored in `target`
   - range target stored in `target_lower` and `target_upper`
   - selected mode stored in `target_type`
8. Preserve range classification:
   - higher-is-better: above upper is still good
   - lower-is-better: below lower is still good
   - neutral: must be within range
9. Preserve range card visual severity:
   - lower-is-better: below lower is green; inside range moves yellow to red as
     it approaches upper; above upper is red
   - higher-is-better: above upper is green; inside range moves red to yellow as
     it approaches upper; below lower is red
10. Preserve R2 file lifecycle:
   - upload object
   - store DB metadata
   - open via presigned URL
   - delete object on delete
11. Preserve journal cell constraint: a cell stores either text or number, not
    both.
12. Preserve creator restrictions for team processes.
13. Keep templates and CSS visually close first; improve structure only after
    parity.

## Suggested Django Apps

```text
accounts
access_control
metrics
documents
guidelines
team_processes
experience
journal
```

## First Implementation Target

Build the Django app in this order:

1. Project setup and custom user model.
2. Team and access-control models/services.
3. Metrics models and FormulaService.
4. Login, base template, navigation.
5. Settings metric CRUD.
6. Reporting Data Entry and Results.
7. Dashboard.
8. Documents/R2.
9. Sales guidelines.
10. Experience deals.
11. Team processes.
12. Journal.

## Test Cases to Write Early

- Admin can access every page.
- Agent access follows `AccessPermission`.
- Formula validation rejects unknown metric keys and unsafe expressions.
- Derived metric layer 3 can depend on layer 2.
- Single target status works for all trend directions.
- Range target status works for all trend directions.
- Previous-week target carry-forward works.
- Metric visible to a team through many-to-many `scoped_teams`.
- Journal cell cannot have both text and numeric value.
- R2 delete is called when deleting a document/resource file.

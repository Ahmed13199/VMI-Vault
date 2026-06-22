# Project Study

## Product Purpose

This is an internal reporting and operations system for VMI Steel Buildings.
It combines KPI reporting, metric configuration, operational boards, knowledge
base pages, document storage, sales/team guideline resources, and journal
tables.

The main business feature is weekly KPI reporting:

- Admins or authorized users define metrics.
- Users enter base metric values for a team and reporting period.
- The system calculates derived metrics from formulas.
- Dashboard and Results pages show values, history, targets, and status.

## Technology Stack

Current app:

```text
Python 3.11
Flask
Flask-Login
Flask-SQLAlchemy
Flask-Migrate / Alembic
PostgreSQL
Jinja2 templates
Vanilla JavaScript
CSS
Cloudflare R2 via boto3
```

Potential Django equivalents:

```text
Django
Django ORM
Django auth
Django migrations
Django templates
Django messages framework
Django staticfiles
django-storages or boto3 wrapper for R2
```

## Major User Groups

Users have both a `role` and a `rank`.

`role` is closer to identity or department:

- `support`
- `sales`
- `engineering`
- `admin`
- Some real data appears to use team/dept names such as `experience`,
  `estimation`, etc.

`rank` is authority:

- `agent`
- `senior`
- `team_leader`
- `admin`

The code treats rank `admin` as the strongest permission. Legacy users with
role `admin` can still be treated as admin through `effective_rank()`.

## Feature Inventory

### Authentication

Blueprint: `app/blueprints/auth`

- Login by username and password.
- Passwords are stored as Werkzeug hashes.
- Flask-Login session handling.
- After login, user is redirected either to the requested page or the first
  accessible route from `AccessService`.

### Dashboard

Blueprint: `app/blueprints/dashboard`

- Shows KPI cards by team and reporting period.
- Admin can filter teams.
- Non-admin users see their team.
- Shows base and derived metrics.
- Uses target status to color cards green/red.

### Reporting

Blueprint: `app/blueprints/reporting`

- Data Entry page for base metrics.
- Results page for base and derived metrics.
- Weekly period window is generated automatically from ISO week 40 through next
  week.
- Data entry currently allows the two completed weeks before the latest
  generated week.
- Targets can be single or range.
- Previous-week targets are carried forward when appropriate.

### Settings

Blueprint: `app/blueprints/settings`

- Metric definitions CRUD.
- Metric categories and sub-categories.
- Formula validation API.
- Metric dependency graph settings.
- Access control matrix.
- User management.
- Team management.

### Framework

Blueprint: `app/blueprints/framework`

- Landing/overview page for knowledge-base areas.

### Team Processes

Blueprint: `app/blueprints/team_processes`

- Process library by team.
- Processes have sections.
- Sections support text alignment, title HTML, and content.
- HTML content is sanitized before storage/display.
- Creator ownership limits edit/delete operations in addition to page
  permissions.

### Documents

Blueprint: `app/blueprints/documents`

- Folder tree.
- Document upload to R2.
- View document through presigned URL.
- Delete folder recursively with contained documents.
- Delete individual documents and R2 objects.

### Sales / Team Guidelines

Blueprint: `app/blueprints/sales_team`

- Team-scoped guideline hierarchy:
  - partitions
  - sections
  - subsections
  - resources
- Resources are links or uploaded files.
- Uploaded files are stored in R2.
- Resource parent must be exactly one of partition, section, subsection.

### Experience Team

Blueprint: `app/blueprints/experience_team`

- Deal board with deal name, client, step type, paid amount, step cost,
  status, notes.
- Accept flow marks deal accepted and timestamps it.

### Journal

Blueprint: `app/blueprints/journal`

- User-created tables.
- Tables have dynamic rows and columns.
- Cells can store either text or numeric value.
- Rows and columns can be added after creation.

## Highest-Risk Business Logic

These are the pieces a Django duplicate must port carefully:

- `AccessService.PAGE_DEFINITIONS` and permission fallback rules.
- Metric scoping:
  - global metrics apply to all teams.
  - team metrics apply via `team_id` or many-to-many `scoped_teams`.
- Category team visibility.
- Formula parsing and validation.
- Derived metrics must be computed by layer order.
- Weekly period generation uses ISO week/year rules.
- Data entry target carry-forward.
- Single/range target classification:
  - higher-is-better: value at or above target is safe; for range, above upper
    remains safe.
  - lower-is-better: value at or below target is safe; for range, below lower
    remains safe.
  - neutral: single target behaves like an upper limit; range must stay inside.
- Document and guideline file lifecycle in R2.
- Journal cell type constraint: one cell cannot have both text and numeric
  values.


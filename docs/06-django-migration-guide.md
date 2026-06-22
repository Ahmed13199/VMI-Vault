# Django Migration Guide

This guide is a practical plan for rebuilding the Flask app as Django while
preserving behavior.

## Suggested Django App Layout

Use multiple Django apps so each domain remains understandable:

```text
vmi_project/
  config/
    settings.py
    urls.py
    wsgi.py
  accounts/
    models.py
    views.py
    decorators.py
  access_control/
    models.py
    services.py
  metrics/
    models.py
    services/
      metrics_service.py
      formula_service.py
    views_reporting.py
    views_dashboard.py
    views_settings.py
  documents/
    models.py
    services.py
    views.py
  guidelines/
    models.py
    views.py
  team_processes/
    models.py
    views.py
  experience/
    models.py
    views.py
  journal/
    models.py
    views.py
  templates/
  static/
```

Alternative: one `core` app is faster but will become large. The current Flask
blueprints map naturally to separate Django apps.

## Suggested Migration Phases

### Phase 1: Django foundation

- Create Django project.
- Configure PostgreSQL.
- Configure static files.
- Create custom user model before first migration.
- Add login/logout views.
- Add base template, navigation, and messages.

### Phase 2: Models

Port models in this order:

1. Team
2. User
3. AccessPermission
4. MetricCategory / MetricSubCategory
5. MetricDefinition
6. ReportingPeriod
7. MetricValue
8. GraphLayerSettings
9. Documents
10. Sales guidelines
11. ExperienceTeamDeal
12. TeamProcess / TeamProcessSection
13. Journal models

Preserve table names with `Meta.db_table` if you plan to reuse the existing
database. If creating a new database, keep table names close to the old ones to
simplify import scripts.

### Phase 3: Services

Port framework-independent logic:

- FormulaService
- MetricsService methods
- AccessService
- R2Service

Use Django ORM equivalents:

```text
SQLAlchemy query.filter_by(...) -> Django Model.objects.filter(...)
joinedload/selectinload -> select_related/prefetch_related
db.session.commit() -> save(), delete(), transaction.atomic()
```

### Phase 4: Permissions

Implement:

- `AccessPermission` model.
- Page registry equivalent to `AccessService.PAGE_DEFINITIONS`.
- `ensure_defaults_exist()` management command or data migration.
- Decorator:

```python
def page_permission_required(page_key, access_type="view"):
    ...
```

- Template helpers for nav visibility.

### Phase 5: Reporting and metrics

Port these first because they are the core product:

- Settings metric list/create/edit.
- Formula validation API.
- Data Entry.
- Results.
- Dashboard.

Pay special attention to:

- metric scoping by team
- active/inactive metrics
- derived metric layer order
- weekly period generation
- previous target carry-forward
- target range status rules

### Phase 6: Remaining modules

Port:

- Documents with R2 storage.
- Sales/team guidelines.
- Experience team deals.
- Team processes.
- Journal.

### Phase 7: Data migration

Recommended approach:

1. Freeze Flask database schema.
2. Create Django models matching the schema.
3. Run Django migrations on a staging database.
4. Import data table by table, or point Django at existing tables if table names
   and columns are preserved.
5. Validate counts and sample workflows.

Data count checklist:

```sql
select count(*) from teams;
select count(*) from users;
select count(*) from access_permissions;
select count(*) from metric_definitions;
select count(*) from metric_values;
select count(*) from reporting_periods;
select count(*) from document_folders;
select count(*) from documents;
select count(*) from journal_tables;
select count(*) from team_processes;
select count(*) from sales_guideline_partitions;
select count(*) from experience_team_deals;
```

## Django Model Conversion Notes

### SQLAlchemy `lazy='dynamic'`

In Django, related managers are lazy by default:

```python
team.users.all()
metric.values.filter(...)
```

### Many-to-many tables

Existing tables:

```text
metric_definition_teams
metric_category_teams
```

If preserving table names, set `db_table` on the `ManyToManyField` through
model or allow Django to create an equivalent explicit through model.

### Numeric fields

Map:

```text
numeric(18,4) -> DecimalField(max_digits=18, decimal_places=4)
numeric(12,2) -> DecimalField(max_digits=12, decimal_places=2)
```

Avoid floats in persistent Django models. The current app often converts to
float for calculations/display; for better precision, Django services can use
`Decimal` until formatting.

### Timestamps

SQLAlchemy uses both:

```python
server_default=db.func.now()
default=datetime.utcnow
onupdate=...
```

Django equivalents:

```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

If preserving existing DB defaults exactly, inspect migrations and use custom
migration SQL as needed.

## Password Migration

The Flask app stores Werkzeug hashes in `users.password_hash`.

Recommended options:

### Option A: Force reset

- Import users with unusable Django passwords.
- Send reset links.
- Simplest and safest.

### Option B: Custom hasher

- Implement a Django hasher that recognizes and verifies Werkzeug hashes.
- On successful login, Django can upgrade the password to a native hash.
- More work, smoother user experience.

### Option C: Parallel field

- Temporarily keep `password_hash`.
- Custom authentication backend checks Werkzeug hash.
- Remove once users have migrated.

## URL Naming Suggestions

Use names similar to Flask endpoints:

```text
dashboard:index
reporting:input
reporting:output
settings:index
settings:create_metric
documents:index
sales_team:index
experience:index
journal:index
team_processes:index
```

This makes template conversion easier.

## Template Conversion Pattern

Flask:

```jinja2
{{ url_for('reporting.input', period_id=selected_period.id) }}
{{ url_for('static', filename='css/main.css') }}
{% if current_user.can_edit_page('settings') %}
```

Django:

```django
{% url 'reporting:input' %}?period_id={{ selected_period.id }}
{% static 'css/main.css' %}
{% if request.user|can_edit_page:'settings' %}
```

## View Conversion Pattern

Flask:

```python
@reporting_bp.route('/input', methods=['GET', 'POST'])
@login_required
@require_page_permission('reporting_input')
def input():
    ...
```

Django:

```python
@login_required
@page_permission_required("reporting_input")
def input_view(request):
    if request.method == "POST":
        if not can_access_page(request.user, "reporting_input", "edit"):
            return deny_access(request, "edit")
    ...
```

## File Storage Migration

Current R2 behavior:

- Upload file object by key.
- Store key and metadata in DB.
- Generate presigned URL for view/open.
- Delete R2 object on DB delete.

Django options:

1. Keep a custom `R2Service`.
2. Use `django-storages` S3 backend with R2 endpoint.

If using `django-storages`, verify:

- endpoint URL
- signature version
- region
- bucket name
- custom domain/public URL if needed
- private media with presigned URLs

## Parity Checklist

Before considering the Django app equivalent, verify:

- Login and logout.
- Permission-hidden nav links.
- Access-control matrix save.
- User create/edit.
- Team create/edit/delete.
- Metric create/edit/deactivate/activate/permanent delete.
- Formula validation API.
- Graph settings API.
- Weekly period generation.
- Data Entry save for single target.
- Data Entry save for target range.
- Previous target carry-forward.
- Results table and cards.
- Dashboard team filters.
- Derived metrics across layers.
- Documents upload/open/delete.
- Folder recursive delete.
- Sales guideline partition/section/subsection/resource CRUD.
- Experience deal create/edit/accept/delete.
- Team process create/edit/section CRUD.
- Journal create/edit/add row/add column/delete.

## Known Cleanup Opportunities During Migration

These are improvement opportunities, not required for parity:

- Move duplicated target-status logic from dashboard/reporting routes into a
  shared service.
- Move page-specific JavaScript out of templates into static modules.
- Replace inline SVG icons with a consistent icon system.
- Add model-level constraints for enum-like fields.
- Add automated tests for formulas, target range classification, permissions,
  and metric scoping.
- Normalize `role` values so they consistently represent departments.
- Use Decimal for metric math where precision matters.


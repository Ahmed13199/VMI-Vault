# Frontend Guide

The frontend is server-rendered Jinja2 with vanilla JavaScript and a single
global CSS file.

## Template Layout

Global base template:

```text
app/templates/base.html
```

Responsibilities:

- HTML shell.
- Favicon.
- Global CSS include.
- Authenticated navigation.
- Flash messages.
- Main content block.
- Footer.
- Confirmation modal.
- Global JavaScript include.

Blocks:

```jinja2
{% block title %}{% endblock %}
{% block extra_css %}{% endblock %}
{% block content %}{% endblock %}
{% block extra_js %}{% endblock %}
```

Django migration:

- Convert `url_for('static', filename='...')` to `{% static '...' %}`.
- Convert `url_for('blueprint.endpoint')` to `{% url 'name' %}`.
- Replace Flask `current_user` with Django `request.user`.
- Provide `can_access_page` and `can_edit_page` either as template filters,
  model methods, or context variables.
- Replace Flask flash rendering with Django messages.

## Navigation

Navigation visibility is permission-driven:

```text
current_user.can_access_page('dashboard')
current_user.can_access_page('framework')
current_user.can_access_page('team_processes')
current_user.can_access_page('documents')
current_user.can_access_page('experience_team')
current_user.can_access_page('sales_team')
current_user.can_access_page('settings')
current_user.can_access_page('permissions')
current_user.can_access_page('reporting_input')
current_user.can_access_page('reporting_output')
current_user.can_access_page('journal')
```

Django equivalent:

- Add a context processor exposing `access_pages`.
- Add methods on the custom user object:
  - `can_access_page(page_key)`
  - `can_edit_page(page_key)`
- Or use template filters:
  - `{{ request.user|can_access:"dashboard" }}`

## CSS

Global stylesheet:

```text
app/static/css/main.css
```

Design traits:

- Dark theme.
- VMI orange primary color.
- CSS variables in `:root`.
- Global layout, nav, tables, forms, cards, results pages, dashboards, and
  feature-specific UI live in one file.

Important variables:

```css
--color-primary: #F26F2A;
--color-header: #141a22;
--color-background: #0e141b;
--color-surface: #1a2332;
--color-surface-light: #243044;
--color-success: #22c55e;
--color-error: #ef4444;
--font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
  Ubuntu, sans-serif;
```

Migration recommendation:

- Keep the CSS file initially to preserve pixel-level parity.
- Once Django parity is stable, split into modules:
  - `base.css`
  - `nav.css`
  - `forms.css`
  - `tables.css`
  - `dashboard.css`
  - `reporting.css`
  - `settings.css`
  - `knowledge.css`

## JavaScript

Global JS:

```text
app/static/js/main.js
```

Responsibilities:

- Auto-dismiss flash messages.
- Basic required-field validation.
- Styled confirmation dialog for forms/buttons with `data-confirm`.
- Prevent focused number inputs from changing on mouse wheel.
- Select number input contents on focus.
- `window.toggleElement`.
- `window.formatNumber`.
- `window.debounce`.

Migration recommendation:

- Keep vanilla JS initially.
- Replace only Flask-specific pieces in templates.
- Django's CSRF token handling will matter if AJAX endpoints are added or
  converted.

## Reporting Data Entry UI

Template:

```text
app/blueprints/reporting/templates/reporting/input.html
```

Key controls:

- Team selector for admins.
- Reporting period selector.
- Collapsible create-period form.
- Data-entry table.
- Numeric value fields named:
  - `metric_<metric.id>`
- Target controls named:
  - `target_type_<metric.id>`
  - `target_<metric.id>`
  - `target_lower_<metric.id>`
  - `target_upper_<metric.id>`

The target UI uses two icon radio options:

- single target
- target range

Client-side JS toggles panels:

```text
data-target-entry
data-target-mode
data-target-panel="single"
data-target-panel="range"
```

Backend validation still decides what is valid. Do not rely only on frontend
visibility.

## Reporting Output UI

Template:

```text
app/blueprints/reporting/templates/reporting/output.html
```

Major UI features:

- Summary KPI cards.
- Search box.
- Tabs:
  - Base
  - Derived
  - Graphs
- Base metric category tabs.
- Table/card view switch.
- Metric history details.
- Sparkline graphs rendered with inline SVG from JS.
- Tooltips for metric descriptions.

Migration notes:

- The template contains page-specific JavaScript in `{% block extra_js %}`.
- Preserve `data-*` attributes because JS relies on them.
- Graph data is embedded in `data-graph-series` JSON-like attributes.
  Escape carefully in Django templates.

## Dashboard UI

Template:

```text
app/blueprints/dashboard/templates/dashboard/index.html
```

Major UI features:

- Period select.
- Admin team multi-select.
- Team sections.
- Metric cards with SVG rings.
- Derived metric cards.

## Settings UI

Templates:

```text
settings/index.html
settings/metric_form.html
settings/graph.html
settings/categories.html
```

Major UI features:

- Metrics table.
- Metric create/edit forms.
- Derived metric formula editing.
- Categories/sub-categories management.
- Graph visual settings.
- Access-control permission matrix.
- User/team management.

## Knowledge/Operations UI

Templates:

```text
framework/index.html
team_processes/*.html
documents/index.html
sales_team/index.html
experience_team/*.html
journal/*.html
```

Notes:

- Several screens are form-heavy and rely on server redirects plus flash
  messages.
- Destructive actions use the global confirmation modal.
- File upload forms require `multipart/form-data`.

## Static Assets

Important files:

```text
app/static/logo_white.png
app/static/VMI Logo White.png
app/static/fav_icon.png
app/static/css/main.css
app/static/js/main.js
```

Django migration:

- Place under a Django app's `static/` folder or project-level static folder.
- Configure `STATIC_URL`, `STATIC_ROOT`, and static collection for deployment.


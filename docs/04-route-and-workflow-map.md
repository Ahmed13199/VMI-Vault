# Route and Workflow Map

This file lists important routes and what they do. In Django, these map to
URLconf entries plus function-based or class-based views.

## Auth

Blueprint prefix: `/auth`

Routes:

```text
GET/POST /auth/login
GET      /auth/logout
```

Workflow:

1. Login form accepts username, password, remember flag.
2. `AuthService.authenticate_user()` validates credentials.
3. On success, Flask-Login logs the user in.
4. Redirect target is `next` if supplied, otherwise
   `AccessService.first_accessible_route(user)`.
5. Logout clears session and redirects to login.

Django equivalent:

- Use `LoginView` or a custom view.
- If preserving Werkzeug hashes, use a custom password hasher or force reset.
- Use `next` handling and permissions-aware fallback.

## Dashboard

Blueprint prefix: `/dashboard`

Routes:

```text
GET /dashboard/
```

Permission:

```text
dashboard view
```

Inputs:

```text
period_id query parameter
team_id query parameters for admin multi-select
```

Workflow:

- Load recent periods.
- Choose selected period.
- Determine teams:
  - admin: all selected teams or all teams by default
  - non-admin: current user's team
- For each team:
  - load base metric values with targets
  - compute previous-period values
  - classify target/limit status
  - build card data
  - compute derived metrics from formulas

Important UI data:

- `within_limit_count`
- `limit_exceeded_count`
- `without_limit_count`
- `metrics_with_limits_count`
- `base_metrics`
- `derived_metrics`

## Reporting Data Entry

Blueprint prefix: `/reporting`

Routes:

```text
GET/POST /reporting/input
```

Permission:

```text
reporting_input view
reporting_input edit for POST saving
```

GET workflow:

1. Generate weekly period window from ISO week 40 through next week.
2. Only expose the two completed weeks before the latest generated week for
   data entry.
3. Determine selected team:
   - admin can use `team_id` query parameter
   - non-admin uses current user's team
4. Determine selected period from `period_id`.
5. Load base metrics for the selected team.
6. Load existing values and targets.
7. Load previous period values.
8. Carry previous targets forward into the current page when current target is
   missing.

POST actions:

```text
action=create_period
action=save_values
```

`create_period`:

- Parses period type, start date, end date.
- Validates end date after start date.
- Generates weekly or monthly label.
- Creates reporting period.

`save_values`:

- Iterates base metrics.
- Reads `metric_<metric.id>` numeric value.
- Reads target fields:
  - `target_type_<metric.id>` = single/range
  - `target_<metric.id>`
  - `target_lower_<metric.id>`
  - `target_upper_<metric.id>`
- Range mode requires both lower and upper if either is supplied.
- Range lower must be <= upper.
- Previous target config carries forward only when the current selected target
  mode matches and current target values are empty.
- Saves through `MetricsService.save_metric_value_with_target(...)`.

## Reporting Output

Routes:

```text
GET /reporting/output
```

Permission:

```text
reporting_output view
```

Workflow:

1. Results start from the previous completed week and go backward.
2. Select team and period.
3. Load current base values and targets.
4. Load previous values and last 3 historical periods.
5. Compute derived metrics from base values.
6. Build result data grouped by category and sub-category.
7. Compute:
   - previous-period delta
   - target status
   - target delta
   - ring progress
   - ratio labels
   - history rows

Target status rules:

```text
single + higher_is_better:
  good if value >= target

single + lower_is_better:
  good if value <= target

single + neutral:
  good if value <= target

range + higher_is_better:
  good if lower <= value <= upper
  good if value > upper
  bad if value < lower
  visual card color is green above upper, red below lower, and a red-to-yellow
  warning gradient inside the range as the value approaches the safe upper side

range + lower_is_better:
  good if lower <= value <= upper
  good if value < lower
  bad if value > upper
  visual card color is green below lower, red above upper, and a yellow-to-red
  warning gradient inside the range as the value approaches the bad upper side

range + neutral:
  good only if lower <= value <= upper
```

## Settings

Blueprint prefix: `/settings`

Core routes:

```text
GET      /settings/
GET      /settings/categories
POST     /settings/categories/<category_id>/rename
POST     /settings/sub-categories/<sub_category_id>/rename
POST     /settings/categories/<category_id>/delete
POST     /settings/sub-categories/<sub_category_id>/delete
GET      /settings/metrics/categories
GET      /settings/metrics/sub-categories
POST     /settings/metrics/categories
POST     /settings/metrics/sub-categories
GET/POST /settings/metrics/new
GET/POST /settings/metrics/<metric_id>/edit
POST     /settings/metrics/<metric_id>/delete
POST     /settings/metrics/<metric_id>/activate
POST     /settings/metrics/<metric_id>/deactivate
POST     /settings/metrics/<metric_id>/delete-permanent
POST     /settings/api/validate-formula
GET      /settings/graph
GET      /settings/api/graph-settings
POST     /settings/api/graph-settings/<layer>
GET/POST /settings/access-control
POST     /settings/users/new
POST     /settings/users/<user_id>/edit
POST     /settings/teams/new
POST     /settings/teams/<team_id>/edit
POST     /settings/teams/<team_id>/delete
```

Permissions:

```text
settings view/edit
permissions view/edit
user_management edit
team_management edit
```

Important metric create/edit validation:

- Key is required and unique.
- Display name is required.
- Unit, scope, trend direction, layer are validated against model constants.
- Derived metrics require formula.
- Formula references must be known active metrics.
- Team selection is limited by the current user's allowed teams.

## Documents

Blueprint prefix: `/documents`

Routes:

```text
GET  /documents/
GET  /documents/folder/<folder_id>
POST /documents/folder/<folder_id>/delete
POST /documents/folders/new
POST /documents/upload
GET  /documents/document/<document_id>/view
POST /documents/document/<document_id>/delete
```

Permissions:

```text
documents view
documents edit for create/upload/delete
```

Workflow:

- Folder listing shows folders and documents.
- Upload requires file and folder.
- Storage key uses timestamp/uuid-style uniqueness.
- File is uploaded to R2 before DB record is committed.
- Viewing redirects to a presigned R2 URL.
- Deleting removes R2 object and DB record.

## Sales Team / Team Guidelines

Blueprint prefix: `/sales-team`

Routes:

```text
GET  /sales-team/
GET  /sales-team/guidelines
POST /sales-team/guidelines/partitions/new
POST /sales-team/guidelines/partitions/<partition_id>/delete
POST /sales-team/guidelines/partitions/<partition_id>/sections/new
POST /sales-team/guidelines/sections/<section_id>/delete
POST /sales-team/guidelines/sections/<section_id>/subsections/new
POST /sales-team/guidelines/subsections/<subsection_id>/delete
POST /sales-team/guidelines/<level>/<parent_id>/resources/new
GET  /sales-team/guidelines/resources/<resource_id>/open
POST /sales-team/guidelines/resources/<resource_id>/delete
```

Permissions:

```text
sales_team view/edit
```

Workflow:

- Team selection defaults based on user's team or first available team.
- Editors can manage only teams they are allowed to access.
- Resources can be link or file.
- File resources upload to R2.
- Open resource redirects to external link or presigned R2 URL.

## Experience Team

Blueprint prefix: `/experience-team`

Routes:

```text
GET      /experience-team/
GET/POST /experience-team/deals/new
GET/POST /experience-team/deals/<deal_id>/edit
POST     /experience-team/deals/<deal_id>/delete
POST     /experience-team/deals/<deal_id>/accept
```

Permissions:

```text
experience_team view/edit
```

Workflow:

- List all deals by newest first.
- Create/edit validates money values and step type.
- Accept marks status accepted and sets `accepted_at`.

## Team Processes

Blueprint prefix: `/team-processes`

Routes:

```text
GET      /team-processes/
GET      /team-processes/team/<team_id>
GET/POST /team-processes/team/<team_id>/new
GET      /team-processes/team/<team_id>/process/<process_id>
GET/POST /team-processes/team/<team_id>/process/<process_id>/edit
POST     /team-processes/team/<team_id>/process/<process_id>/delete
POST     /team-processes/team/<team_id>/process/<process_id>/sections/new
POST     /team-processes/team/<team_id>/process/<process_id>/sections/<section_id>/delete
GET/POST /team-processes/team/<team_id>/process/<process_id>/sections/<section_id>/edit
```

Permissions:

```text
team_processes view/edit
```

Extra ownership rule:

- Only the creator can edit/delete their process or sections, unless the
  process/section has no creator and the current user is assigned.

Security:

- HTML content is sanitized. In Django, use `bleach` or an equivalent allowlist
  sanitizer before storing or rendering rich text.

## Journal

Blueprint prefix: `/journal`

Routes:

```text
GET      /journal/
GET/POST /journal/tables/new
GET/POST /journal/tables/<table_id>
POST     /journal/tables/<table_id>/delete
```

Permissions:

```text
journal view/edit
```

Workflow:

- Create table with requested rows and columns.
- Limits: rows <= 50, columns <= 20.
- Edit table can:
  - add row
  - add column
  - save table name, row names, column names, and cells
- Cell parsing stores numeric values in `value_number` when possible; otherwise
  stores raw text in `value_text`.

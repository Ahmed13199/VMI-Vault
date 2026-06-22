# Database and Model Map

This document maps the current SQLAlchemy models to suggested Django models.
Use `database_schema.md` at the repository root as the current database
snapshot, but treat model files as the source of truth for relationships and
behavior.

## Core Identity Models

### Team

Source:

```text
app/models/team.py
```

Table: `teams`

Fields:

```text
id integer primary key
name varchar(64) unique not null
type varchar(32) nullable
```

Relationships:

- One team has many users.
- One team has many direct metric definitions.
- Many-to-many with metric definitions through `metric_definition_teams`.
- Many-to-many with metric categories through `metric_category_teams`.
- One team has many metric values.

Django suggestion:

```python
class Team(models.Model):
    name = models.CharField(max_length=64, unique=True)
    type = models.CharField(max_length=32, blank=True, null=True)
```

### User

Source:

```text
app/models/user.py
```

Table: `users`

Fields:

```text
id integer primary key
first_name varchar(64) nullable
last_name varchar(64) nullable
username varchar(64) unique not null indexed
password_hash varchar(256) not null
role varchar(32) not null default support
rank varchar(32) not null default agent
team_id FK teams nullable
```

Important methods:

- `full_name`
- `set_password`
- `check_password`
- `is_admin`
- `effective_rank`
- `display_rank`
- `can_access_page`
- `can_edit_page`

Django suggestion:

Prefer a custom user model before first Django migration:

```python
class User(AbstractUser):
    role = models.CharField(max_length=32, default="support")
    rank = models.CharField(max_length=32, default="agent")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
```

If preserving existing table names, set `db_table = "users"`. Decide how to
handle existing Werkzeug password hashes before importing users.

## Access Control

### AccessPermission

Source:

```text
app/models/access_permission.py
```

Table: `access_permissions`

Fields:

```text
id integer primary key
page_key varchar(64) not null indexed
page_name varchar(128) not null
rank varchar(32) not null indexed
can_view boolean not null default false
can_edit boolean not null default false
```

Constraint:

```text
unique(page_key, rank)
```

Django suggestion:

```python
class AccessPermission(models.Model):
    page_key = models.CharField(max_length=64, db_index=True)
    page_name = models.CharField(max_length=128)
    rank = models.CharField(max_length=32, db_index=True)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = "access_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["page_key", "rank"],
                name="uq_access_permissions_page_rank",
            )
        ]
```

## Metrics and Reporting

### MetricCategory

Table: `metric_categories`

Fields:

```text
id integer primary key
name varchar(128) unique not null indexed
```

Relationships:

- Has many sub-categories.
- Has many metric definitions.
- Many-to-many with teams through `metric_category_teams`.

### MetricSubCategory

Table: `metric_sub_categories`

Fields:

```text
id integer primary key
category_id FK metric_categories not null indexed
name varchar(128) not null
```

Constraint:

```text
unique(category_id, name)
```

### MetricDefinition

Table: `metric_definitions`

Fields:

```text
id integer primary key
key varchar(64) unique not null indexed
display_name varchar(128) not null
description text nullable
trend_direction varchar(32) not null default neutral
unit varchar(32) not null default number
scope varchar(16) not null default global
team_id FK teams nullable
category_id FK metric_categories nullable indexed
sub_category_id FK metric_sub_categories nullable indexed
is_derived boolean not null default false
formula text nullable
active boolean not null default true
layer integer not null default 1
```

Many-to-many:

```text
metric_definition_teams(metric_definition_id, team_id)
```

Valid values:

```text
UNITS = number, percent, currency, mins, days, count
TREND_DIRECTIONS = neutral, higher_is_better, lower_is_better
SCOPES = global, team
```

Django suggestion:

```python
class MetricDefinition(models.Model):
    key = models.CharField(max_length=64, unique=True, db_index=True)
    display_name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    trend_direction = models.CharField(max_length=32, default="neutral")
    unit = models.CharField(max_length=32, default="number")
    scope = models.CharField(max_length=16, default="global")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    scoped_teams = models.ManyToManyField(Team, related_name="scoped_metrics", blank=True)
    category = models.ForeignKey(MetricCategory, null=True, blank=True, on_delete=models.SET_NULL)
    sub_category = models.ForeignKey(MetricSubCategory, null=True, blank=True, on_delete=models.SET_NULL)
    is_derived = models.BooleanField(default=False)
    formula = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    layer = models.IntegerField(default=1)
```

### ReportingPeriod

Table: `reporting_periods`

Fields:

```text
id integer primary key
period_type varchar(16) not null default weekly
start_date date not null
end_date date not null
label varchar(32) not null
```

Valid types:

```text
weekly, monthly, quarterly, yearly
```

Important behavior:

- Weekly labels are ISO week labels like `2026-W25`.
- Weekly period generation starts at ISO week 40 and continues through next
  week.

### MetricValue

Table: `metric_values`

Fields:

```text
id integer primary key
metric_id FK metric_definitions not null
team_id FK teams not null
reporting_period_id FK reporting_periods not null
value numeric(18,4) not null
target numeric(18,4) nullable
target_type varchar(16) not null default single
target_lower numeric(18,4) nullable
target_upper numeric(18,4) nullable
```

Constraint:

```text
unique(metric_id, team_id, reporting_period_id)
```

Target behavior:

- `target_type = single`: use `target`.
- `target_type = range`: use `target_lower` and `target_upper`.
- Empty targets are allowed.

Django suggestion:

```python
class MetricValue(models.Model):
    metric = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    reporting_period = models.ForeignKey(ReportingPeriod, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=18, decimal_places=4)
    target = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    target_type = models.CharField(max_length=16, default="single")
    target_lower = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    target_upper = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "team", "reporting_period"],
                name="uq_metric_team_period",
            )
        ]
```

## Graph Settings

### GraphLayerSettings

Table: `graph_layer_settings`

Fields:

```text
id integer primary key
layer integer unique not null indexed
color varchar(7) not null default #F26F2A
shape varchar(16) not null default circle
size integer not null default 30
```

Supported shapes:

```text
circle, rectangle, square, diamond, hexagon
```

## Documents

### DocumentFolder

Table: `document_folders`

Fields:

```text
id integer primary key
name varchar(200) not null
parent_id self FK nullable indexed
created_by_user_id FK users nullable indexed
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
```

### Document

Table: `documents`

Fields:

```text
id integer primary key
folder_id FK document_folders nullable indexed
created_by_user_id FK users nullable indexed
title varchar(200) not null
original_filename varchar(500) not null
content_type varchar(200) nullable
size_bytes bigint nullable
storage_key varchar(700) unique not null indexed
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
```

Storage:

- Actual file content is in Cloudflare R2.
- Database stores metadata and `storage_key`.

## Sales Guidelines

Tables:

```text
sales_guideline_partitions
sales_guideline_sections
sales_guideline_subsections
sales_guideline_resources
```

Hierarchy:

```text
Team
  Partition
    Section
      Subsection
```

Resources can belong to exactly one parent level:

- partition
- section
- subsection

`SalesGuidelineResource` has:

```text
title
resource_type file/link
url
storage_key
original_filename
content_type
size_bytes
created_by_user_id
created_at
updated_at
```

Constraints:

- `resource_type IN ('file', 'link')`
- exactly one parent FK must be non-null

## Experience Team Deals

### ExperienceTeamDeal

Table: `experience_team_deals`

Fields:

```text
id bigint primary key
deal_name varchar(255) not null
client_name varchar(255) nullable
step_type varchar(20) not null
client_paid_so_far numeric(12,2) not null default 0
step_cost numeric(12,2) not null default 0
acceptance_status varchar(20) not null default pending indexed
accepted_at timestamptz nullable
notes text nullable
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
```

Step types are validated in routes rather than with model constants. Current
accepted values:

```text
greenlight, concrete
```

## Team Processes

### TeamProcess

Table: `team_processes`

Fields:

```text
id integer primary key
team_id FK teams not null indexed
created_by_user_id FK users nullable indexed
title varchar(200) not null
slug varchar(200) not null
status varchar(32) not null default draft
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
```

Constraint:

```text
unique(team_id, slug)
```

### TeamProcessSection

Table: `team_process_sections`

Fields:

```text
id integer primary key
process_id FK team_processes not null indexed
created_by_user_id FK users nullable indexed
position integer not null default 0
section_type varchar(32) not null default paragraph
text_align varchar(16) not null default left
title varchar(200) nullable
title_html text nullable
content text nullable
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
```

Sections are ordered by `position`.

## Journal

Tables:

```text
journal_tables
journal_table_rows
journal_table_columns
journal_table_cells
```

Relationships:

- One table has many rows.
- One table has many columns.
- One table has many cells.
- One cell belongs to one row and one column.

Constraints:

```text
unique(table_id, row_id, column_id)
unique(table_id, position) on rows
unique(table_id, position) on columns
check value_text is null OR value_number is null
```

Django migration note:

Use `DecimalField(max_digits=18, decimal_places=4)` for `value_number`.
Implement the cell one-type check constraint if the target database remains
PostgreSQL.


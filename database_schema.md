# Database Schema

Schema: **public**

---

## public.alembic_version

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | version_num | character varying(32) | ✅ |  |

---

## public.document_folders

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('document_folders_id_seq'::regclass) |
| 2 | name | character varying(200) | ✅ |  |
| 3 | parent_id | integer | ❌ |  |
| 4 | created_by_user_id | integer | ❌ |  |
| 5 | created_at | timestamp with time zone | ✅ | now() |
| 6 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.documents

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('documents_id_seq'::regclass) |
| 2 | folder_id | integer | ❌ |  |
| 3 | created_by_user_id | integer | ❌ |  |
| 4 | title | character varying(200) | ✅ |  |
| 5 | original_filename | character varying(500) | ✅ |  |
| 6 | content_type | character varying(200) | ❌ |  |
| 7 | size_bytes | bigint | ❌ |  |
| 8 | storage_key | character varying(700) | ✅ |  |
| 9 | created_at | timestamp with time zone | ✅ | now() |
| 10 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.experience_team_deals

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | bigint | ✅ | nextval('experience_team_deals_id_seq'::regclass) |
| 2 | deal_name | character varying(255) | ✅ |  |
| 3 | client_name | character varying(255) | ❌ |  |
| 4 | step_type | character varying(20) | ✅ |  |
| 5 | client_paid_so_far | numeric(12,2) | ✅ | 0 |
| 7 | step_cost | numeric(12,2) | ✅ | 0 |
| 8 | acceptance_status | character varying(20) | ✅ | 'pending'::character varying |
| 9 | accepted_at | timestamp with time zone | ❌ |  |
| 10 | notes | text | ❌ |  |
| 11 | created_at | timestamp with time zone | ✅ | now() |
| 12 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.graph_layer_settings

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('graph_layer_settings_id_seq'::regclass) |
| 2 | layer | integer | ✅ |  |
| 3 | color | character varying(7) | ✅ |  |
| 4 | shape | character varying(16) | ✅ |  |
| 5 | size | integer | ✅ |  |

---

## public.graph_layer_styles

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('graph_layer_styles_id_seq'::regclass) |
| 2 | layer | integer | ✅ |  |
| 3 | node_color | character varying(16) | ✅ |  |
| 4 | border_color | character varying(16) | ✅ |  |
| 5 | shape | character varying(16) | ✅ |  |
| 6 | size | integer | ✅ |  |

---

## public.journal_table_cells

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('journal_table_cells_id_seq'::regclass) |
| 2 | table_id | integer | ✅ |  |
| 3 | row_id | integer | ✅ |  |
| 4 | column_id | integer | ✅ |  |
| 5 | value_text | text | ❌ |  |
| 6 | value_number | numeric(18,4) | ❌ |  |
| 7 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.journal_table_columns

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('journal_table_columns_id_seq'::regclass) |
| 2 | table_id | integer | ✅ |  |
| 3 | position | integer | ✅ |  |
| 4 | name | character varying(200) | ✅ |  |
| 5 | created_at | timestamp with time zone | ✅ | now() |
| 6 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.journal_table_rows

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('journal_table_rows_id_seq'::regclass) |
| 2 | table_id | integer | ✅ |  |
| 3 | position | integer | ✅ |  |
| 4 | name | character varying(200) | ✅ |  |
| 5 | created_at | timestamp with time zone | ✅ | now() |
| 6 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.journal_tables

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('journal_tables_id_seq'::regclass) |
| 2 | name | character varying(200) | ✅ |  |
| 3 | created_by_user_id | integer | ❌ |  |
| 4 | created_at | timestamp with time zone | ✅ | now() |
| 5 | updated_at | timestamp with time zone | ✅ | now() |

---

## public.metric_categories

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ |  |
| 2 | name | character varying(128) | ✅ |  |

---

## public.metric_category_teams

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | category_id | integer | ✅ |  |
| 2 | team_id | integer | ✅ |  |

---

## public.metric_definition_teams

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | metric_definition_id | integer | ✅ |  |
| 2 | team_id | integer | ✅ |  |

---

## public.metric_definitions

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('metric_definitions_id_seq'::regclass) |
| 2 | key | character varying(64) | ✅ |  |
| 3 | display_name | character varying(128) | ✅ |  |
| 4 | description | text | ❌ |  |
| 5 | unit | character varying(32) | ✅ |  |
| 6 | scope | character varying(16) | ✅ |  |
| 7 | team_id | integer | ❌ |  |
| 8 | is_derived | boolean | ✅ |  |
| 9 | formula | text | ❌ |  |
| 10 | active | boolean | ✅ |  |
| 11 | layer | integer | ✅ |  |
| 12 | trend_direction | character varying(32) | ✅ | 'neutral'::character varying |
| 13 | category_id | integer | ❌ |  |
| 14 | sub_category_id | integer | ❌ |  |

---

## public.metric_sub_categories

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ |  |
| 2 | category_id | integer | ✅ |  |
| 3 | name | character varying(128) | ✅ |  |

---

## public.metric_values

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('metric_values_id_seq'::regclass) |
| 2 | metric_id | integer | ✅ |  |
| 3 | team_id | integer | ✅ |  |
| 4 | reporting_period_id | integer | ✅ |  |
| 5 | value | numeric(18,4) | ✅ |  |
| 6 | target | numeric(18,4) | ❌ |  |

---

## public.reporting_periods

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('reporting_periods_id_seq'::regclass) |
| 2 | period_type | character varying(16) | ✅ |  |
| 3 | start_date | date | ✅ |  |
| 4 | end_date | date | ✅ |  |
| 5 | label | character varying(32) | ✅ |  |

---

## public.team_process_sections

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('team_process_sections_id_seq'::regclass) |
| 2 | process_id | integer | ✅ |  |
| 3 | position | integer | ✅ | 0 |
| 4 | section_type | character varying(32) | ✅ | 'paragraph'::character varying |
| 5 | title | character varying(200) | ❌ |  |
| 6 | content | text | ❌ |  |
| 7 | created_at | timestamp with time zone | ✅ | now() |
| 8 | updated_at | timestamp with time zone | ✅ | now() |
| 9 | created_by_user_id | integer | ❌ |  |
| 10 | text_align | character varying(16) | ✅ | 'left'::character varying |
| 11 | title_html | text | ❌ |  |

---

## public.team_processes

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('team_processes_id_seq'::regclass) |
| 2 | team_id | integer | ✅ |  |
| 3 | title | character varying(200) | ✅ |  |
| 4 | slug | character varying(200) | ✅ |  |
| 5 | status | character varying(32) | ✅ | 'draft'::character varying |
| 6 | created_at | timestamp with time zone | ✅ | now() |
| 7 | updated_at | timestamp with time zone | ✅ | now() |
| 8 | created_by_user_id | integer | ❌ |  |

---

## public.teams

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('teams_id_seq'::regclass) |
| 2 | name | character varying(64) | ✅ |  |
| 3 | type | character varying(32) | ❌ |  |

---

## public.users

| # | Column | Type | Not Null | Default |
|---:|---|---|:---:|---|
| 1 | id | integer | ✅ | nextval('users_id_seq'::regclass) |
| 2 | username | character varying(64) | ✅ |  |
| 3 | password_hash | character varying(256) | ✅ |  |
| 4 | role | character varying(32) | ✅ |  |
| 5 | team_id | integer | ❌ |  |

---

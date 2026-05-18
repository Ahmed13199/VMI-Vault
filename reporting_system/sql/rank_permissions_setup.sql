ALTER TABLE users
ADD COLUMN IF NOT EXISTS first_name VARCHAR(64);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_name VARCHAR(64);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS rank VARCHAR(32) NOT NULL DEFAULT 'agent';

CREATE INDEX IF NOT EXISTS ix_users_rank ON users (rank);

UPDATE users
SET rank = CASE
    WHEN role = 'admin' THEN 'admin'
    ELSE COALESCE(NULLIF(rank, ''), 'agent')
END;

CREATE TABLE IF NOT EXISTS access_permissions (
    id SERIAL PRIMARY KEY,
    page_key VARCHAR(64) NOT NULL,
    page_name VARCHAR(128) NOT NULL,
    rank VARCHAR(32) NOT NULL,
    can_view BOOLEAN NOT NULL DEFAULT FALSE,
    can_edit BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_access_permissions_page_rank UNIQUE (page_key, rank)
);

CREATE INDEX IF NOT EXISTS ix_access_permissions_page_key ON access_permissions (page_key);
CREATE INDEX IF NOT EXISTS ix_access_permissions_rank ON access_permissions (rank);

INSERT INTO access_permissions (page_key, page_name, rank, can_view, can_edit)
VALUES
    ('dashboard', 'Dashboard', 'team_leader', TRUE, FALSE),
    ('dashboard', 'Dashboard', 'senior', TRUE, FALSE),
    ('dashboard', 'Dashboard', 'agent', TRUE, FALSE),
    ('dashboard', 'Dashboard', 'admin', TRUE, TRUE),

    ('framework', 'Framework', 'team_leader', TRUE, FALSE),
    ('framework', 'Framework', 'senior', TRUE, FALSE),
    ('framework', 'Framework', 'agent', TRUE, FALSE),
    ('framework', 'Framework', 'admin', TRUE, TRUE),

    ('team_processes', 'Team Processes', 'team_leader', TRUE, TRUE),
    ('team_processes', 'Team Processes', 'senior', TRUE, TRUE),
    ('team_processes', 'Team Processes', 'agent', TRUE, TRUE),
    ('team_processes', 'Team Processes', 'admin', TRUE, TRUE),

    ('documents', 'Documents', 'team_leader', TRUE, TRUE),
    ('documents', 'Documents', 'senior', TRUE, TRUE),
    ('documents', 'Documents', 'agent', TRUE, TRUE),
    ('documents', 'Documents', 'admin', TRUE, TRUE),

    ('experience_team', 'Experience Team', 'team_leader', TRUE, TRUE),
    ('experience_team', 'Experience Team', 'senior', TRUE, TRUE),
    ('experience_team', 'Experience Team', 'agent', TRUE, TRUE),
    ('experience_team', 'Experience Team', 'admin', TRUE, TRUE),

    ('sales_team', 'Sales Team', 'team_leader', TRUE, TRUE),
    ('sales_team', 'Sales Team', 'senior', TRUE, TRUE),
    ('sales_team', 'Sales Team', 'agent', TRUE, TRUE),
    ('sales_team', 'Sales Team', 'admin', TRUE, TRUE),

    ('settings', 'Metric Settings', 'team_leader', TRUE, TRUE),
    ('settings', 'Metric Settings', 'senior', TRUE, TRUE),
    ('settings', 'Metric Settings', 'agent', TRUE, TRUE),
    ('settings', 'Metric Settings', 'admin', TRUE, TRUE),

    ('reporting_input', 'Data Entry', 'team_leader', TRUE, TRUE),
    ('reporting_input', 'Data Entry', 'senior', TRUE, TRUE),
    ('reporting_input', 'Data Entry', 'agent', TRUE, TRUE),
    ('reporting_input', 'Data Entry', 'admin', TRUE, TRUE),

    ('reporting_output', 'Results', 'team_leader', TRUE, FALSE),
    ('reporting_output', 'Results', 'senior', TRUE, FALSE),
    ('reporting_output', 'Results', 'agent', TRUE, FALSE),
    ('reporting_output', 'Results', 'admin', TRUE, TRUE),

    ('journal', 'Journal', 'team_leader', TRUE, TRUE),
    ('journal', 'Journal', 'senior', TRUE, TRUE),
    ('journal', 'Journal', 'agent', TRUE, TRUE),
    ('journal', 'Journal', 'admin', TRUE, TRUE),

    ('permissions', 'Access Control', 'team_leader', FALSE, FALSE),
    ('permissions', 'Access Control', 'senior', FALSE, FALSE),
    ('permissions', 'Access Control', 'agent', FALSE, FALSE),
    ('permissions', 'Access Control', 'admin', TRUE, TRUE),

    ('user_management', 'User Management', 'team_leader', FALSE, FALSE),
    ('user_management', 'User Management', 'senior', FALSE, FALSE),
    ('user_management', 'User Management', 'agent', FALSE, FALSE),
    ('user_management', 'User Management', 'admin', TRUE, TRUE),

    ('team_management', 'Team Management', 'team_leader', FALSE, FALSE),
    ('team_management', 'Team Management', 'senior', FALSE, FALSE),
    ('team_management', 'Team Management', 'agent', FALSE, FALSE),
    ('team_management', 'Team Management', 'admin', TRUE, TRUE)
ON CONFLICT (page_key, rank) DO UPDATE
SET
    page_name = EXCLUDED.page_name,
    can_view = EXCLUDED.can_view,
    can_edit = EXCLUDED.can_edit;

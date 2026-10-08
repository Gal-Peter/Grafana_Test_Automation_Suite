-- Test-data database for data-driven tests. Edit this file; the .db is rebuilt automatically
-- (or run:  python -m utils.db_seed --force).
-- Rule: every table/view used by load_cases(..., source="sqlite") must expose an `id` column.

CREATE TABLE dashboard_cases (
    id   TEXT PRIMARY KEY,
    tags TEXT NOT NULL DEFAULT ''            -- comma separated
);

CREATE TABLE dashboard_panels (
    case_id  TEXT    NOT NULL REFERENCES dashboard_cases(id),
    position INTEGER NOT NULL,
    title    TEXT    NOT NULL,
    type     TEXT    NOT NULL CHECK (type IN ('text', 'timeseries')),
    PRIMARY KEY (case_id, position)
);

INSERT INTO dashboard_cases (id, tags) VALUES
    ('single_text_panel', 'smoke'),
    ('two_panels',        'regression'),
    ('mixed_panel_types', 'regression');

INSERT INTO dashboard_panels (case_id, position, title, type) VALUES
    ('single_text_panel', 1, 'Only Panel',   'text'),
    ('two_panels',        1, 'First Panel',  'text'),
    ('two_panels',        2, 'Second Panel', 'text'),
    ('mixed_panel_types', 1, 'Notes',        'text'),
    ('mixed_panel_types', 2, 'Trend',        'timeseries');

-- One row per case, panels aggregated into a JSON array (parsed by load_cases via json_columns)
CREATE VIEW dashboards_view AS
SELECT c.id AS id,
       c.tags AS tags,
       json_group_array(json_object('title', p.title, 'type', p.type)) AS panels
FROM dashboard_cases c
JOIN (SELECT * FROM dashboard_panels ORDER BY case_id, position) p ON p.case_id = c.id
GROUP BY c.id;

CREATE TABLE api_negative_cases (
    id              TEXT PRIMARY KEY,
    method          TEXT    NOT NULL,
    path            TEXT    NOT NULL,
    body            TEXT,                    -- JSON text or NULL
    authenticated   INTEGER NOT NULL CHECK (authenticated IN (0, 1)),
    expected_status INTEGER NOT NULL
);

INSERT INTO api_negative_cases (id, method, path, body, authenticated, expected_status) VALUES
    ('empty_title_rejected',    'POST', '/api/dashboards/db',
        '{"dashboard": {"title": "", "panels": []}, "overwrite": false}', 1, 400),
    ('unknown_uid_not_found',   'GET',  '/api/dashboards/uid/this-uid-does-not-exist', NULL, 1, 404),
    ('unauthenticated_rejected','GET',  '/api/search', NULL, 0, 401);

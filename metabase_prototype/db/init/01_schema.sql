/* PostgreSQL schema for the JSON-first Metabase MVP */

CREATE TABLE IF NOT EXISTS test_run (
    run_id           BIGSERIAL PRIMARY KEY,
    subsystem        TEXT NOT NULL,
    profile          TEXT NOT NULL,
    target_platform  TEXT NOT NULL,
    os_version       TEXT NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL,
    ended_at         TIMESTAMPTZ,
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS raw_result (
    raw_id       BIGSERIAL PRIMARY KEY,
    run_id       BIGINT NOT NULL REFERENCES test_run(run_id) ON DELETE CASCADE,
    tool         TEXT NOT NULL,
    payload_kind TEXT NOT NULL CHECK (payload_kind IN ('scalar', 'vector')),
    payload      JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scalar_result (
    raw_id       BIGINT NOT NULL REFERENCES raw_result(raw_id) ON DELETE CASCADE,
    run_id       BIGINT NOT NULL REFERENCES test_run(run_id) ON DELETE CASCADE,
    benchmark    TEXT NOT NULL,
    measure      TEXT NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    lower_value  DOUBLE PRECISION,
    upper_value  DOUBLE PRECISION,
    unit         TEXT,
    PRIMARY KEY (raw_id, benchmark, measure)
);

CREATE TABLE IF NOT EXISTS vector_point (
    raw_id       BIGINT NOT NULL REFERENCES raw_result(raw_id) ON DELETE CASCADE,
    run_id       BIGINT NOT NULL REFERENCES test_run(run_id) ON DELETE CASCADE,
    benchmark    TEXT NOT NULL,
    measure      TEXT NOT NULL,
    series       TEXT NOT NULL,
    point_idx    INTEGER NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    lower_value  DOUBLE PRECISION,
    upper_value  DOUBLE PRECISION,
    unit         TEXT,
    PRIMARY KEY (raw_id, benchmark, measure, series, point_idx)
);

CREATE TABLE IF NOT EXISTS run_event (
    event_id    BIGSERIAL PRIMARY KEY,
    run_id      BIGINT NOT NULL REFERENCES test_run(run_id) ON DELETE CASCADE,
    event_ts    TIMESTAMPTZ NOT NULL,
    label       TEXT NOT NULL,
    severity    TEXT,
    payload     JSONB
);

CREATE INDEX IF NOT EXISTS idx_test_run_filters
    ON test_run (subsystem, profile, target_platform, os_version, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_result_lookup
    ON raw_result (run_id, tool, payload_kind);

CREATE INDEX IF NOT EXISTS idx_scalar_result_lookup
    ON scalar_result (run_id, benchmark, measure);

CREATE INDEX IF NOT EXISTS idx_vector_point_lookup
    ON vector_point (run_id, benchmark, measure, series, point_idx);

CREATE INDEX IF NOT EXISTS idx_run_event_lookup
    ON run_event (run_id, event_ts);

/* Helper extract view for scalar BMF-like JSON */

CREATE OR REPLACE VIEW v_scalar_raw_extract AS
SELECT
    rr.raw_id,
    rr.run_id,
    bench.benchmark AS benchmark,
    meas.measure AS measure,
    (meas.measure_obj->>'value')::double precision AS value,
    NULLIF(meas.measure_obj->>'lower_value', '')::double precision AS lower_value,
    NULLIF(meas.measure_obj->>'upper_value', '')::double precision AS upper_value,
    NULLIF(meas.measure_obj->>'unit', '') AS unit
FROM raw_result rr
CROSS JOIN LATERAL jsonb_each(rr.payload) AS bench(benchmark, benchmark_obj)
CROSS JOIN LATERAL jsonb_each(bench.benchmark_obj) AS meas(measure, measure_obj)
WHERE rr.payload_kind = 'scalar'
  AND jsonb_typeof(meas.measure_obj->'value') = 'number';

/* Helper extract view for vector JSON. */

CREATE OR REPLACE VIEW v_vector_raw_extract AS
SELECT
    rr.raw_id,
    rr.run_id,
    COALESCE(rr.payload->>'benchmark', rr.tool) AS benchmark,
    COALESCE(rr.payload->>'metric', rr.tool) AS measure,
    COALESCE(rr.payload->>'series', 'default') AS series,
    p.ordinality::integer AS point_idx,
    (p.point_obj->>'value')::double precision AS value,
    NULLIF(p.point_obj->>'lower_value', '')::double precision AS lower_value,
    NULLIF(p.point_obj->>'upper_value', '')::double precision AS upper_value,
    NULLIF(rr.payload->>'unit', '') AS unit
FROM raw_result rr
CROSS JOIN LATERAL jsonb_array_elements(rr.payload->'points') WITH ORDINALITY AS p(point_obj, ordinality)
WHERE rr.payload_kind = 'vector';

-- Views exposed to Metabase.
CREATE OR REPLACE VIEW v_scalar_metabase AS
SELECT
    r.run_id,
    r.started_at,
    r.ended_at,
    r.started_at::date AS run_date,
    r.subsystem,
    r.profile,
    r.target_platform,
    r.os_version,
    rr.tool,
    s.raw_id,
    s.benchmark,
    s.measure,
    (s.benchmark || '.' || s.measure) AS metric_key,
    s.value,
    s.lower_value,
    s.upper_value,
    s.unit,
    'scalar'::text AS metric_type
FROM scalar_result s
JOIN raw_result rr ON rr.raw_id = s.raw_id
JOIN test_run r ON r.run_id = s.run_id;

CREATE OR REPLACE VIEW v_vector_metabase AS
SELECT
    r.run_id,
    r.started_at,
    r.ended_at,
    r.started_at::date AS run_date,
    r.subsystem,
    r.profile,
    r.target_platform,
    r.os_version,
    rr.tool,
    v.raw_id,
    v.benchmark,
    v.measure,
    (v.benchmark || '.' || v.measure) AS metric_key,
    v.series,
    v.point_idx,
    (r.started_at + ((v.point_idx - 1) * COALESCE(NULLIF((rr.payload->>'sample_interval_sec'), '')::integer, 10) * INTERVAL '1 second')) AS point_ts,
    v.value,
    v.lower_value,
    v.upper_value,
    v.unit,
    'vector'::text AS metric_type
FROM vector_point v
JOIN raw_result rr ON rr.raw_id = v.raw_id
JOIN test_run r ON r.run_id = v.run_id;

CREATE OR REPLACE VIEW v_all_metrics AS
SELECT
    run_id,
    started_at,
    ended_at,
    run_date,
    subsystem,
    profile,
    target_platform,
    os_version,
    tool,
    raw_id,
    benchmark,
    measure,
    metric_key,
    NULL::text AS series,
    NULL::integer AS point_idx,
    NULL::timestamptz AS point_ts,
    value,
    lower_value,
    upper_value,
    unit,
    metric_type
FROM v_scalar_metabase
UNION ALL
SELECT
    run_id,
    started_at,
    ended_at,
    run_date,
    subsystem,
    profile,
    target_platform,
    os_version,
    tool,
    raw_id,
    benchmark,
    measure,
    metric_key,
    series,
    point_idx,
    point_ts,
    value,
    lower_value,
    upper_value,
    unit,
    metric_type
FROM v_vector_metabase;

CREATE OR REPLACE VIEW v_metric_catalog AS
SELECT DISTINCT
    run_date,
    subsystem,
    profile,
    target_platform,
    os_version,
    tool,
    metric_type,
    benchmark,
    measure,
    metric_key,
    unit
FROM v_all_metrics;

CREATE OR REPLACE VIEW v_scalar_boxplot AS
SELECT
    subsystem,
    profile,
    target_platform,
    os_version,
    run_date,
    tool,
    benchmark,
    measure,
    metric_key,
    unit,
    COUNT(*) AS n,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY value) AS q1,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY value) AS median,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY value) AS q3,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    AVG(value) AS avg_value,
    stddev_samp(value) AS stddev_value
FROM v_scalar_metabase
GROUP BY 1,2,3,4,5,6,7,8,9,10;

/* Synthetic performance and endurance data */

CREATE TABLE IF NOT EXISTS experiment (
    experiment_id integer NOT NULL,
    config_id integer NOT NULL,
    description character varying(100) NOT NULL,
    type character varying(20),
    started_at timestamp without time zone,
    ended_at timestamp without time zone,
    tests_total integer DEFAULT 0 NOT NULL,
    tests_passed integer DEFAULT 0 NOT NULL,
    tests_failed integer DEFAULT 0 NOT NULL,
    tests_broken integer DEFAULT 0 NOT NULL,
    tests_skipped integer DEFAULT 0 NOT NULL
);

CREATE TABLE IF NOT EXISTS configuration (
    config_id integer NOT NULL,
    os character varying(100) NOT NULL,
    packages json NOT NULL,
    core_info character varying(300) NOT NULL,
    core_config json NOT NULL,
    hardware json NOT NULL
);

CREATE TABLE IF NOT EXISTS loader (
    id integer NOT NULL,
    experiment_id integer NOT NULL,
    command character varying NOT NULL,
    result json NOT NULL,
    description character varying(100) NOT NULL,
    started_at timestamp without time zone,
    ended_at timestamp without time zone
);

CREATE TABLE IF NOT EXISTS observer (
    id integer NOT NULL,
    experiment_id integer NOT NULL,
    command character varying(300) NOT NULL,
    result json NOT NULL,
    description character varying(100) NOT NULL,
    started_at timestamp without time zone,
    ended_at timestamp without time zone
);

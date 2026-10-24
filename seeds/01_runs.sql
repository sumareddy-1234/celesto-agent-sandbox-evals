-- Create runs table
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    sandbox_name TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('created','ready','running','succeeded','failed','deleted')),
    execution_target TEXT NOT NULL DEFAULT 'celesto_sandbox',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed required demo run (idempotent)
INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
VALUES ('demo-seed-1', 'sbx-seeddemo1', 'problem-demo', 'deleted', 'celesto_sandbox')
ON CONFLICT (run_id) DO NOTHING;

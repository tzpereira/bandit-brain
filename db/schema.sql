-- Experiments and results table    
CREATE TABLE IF NOT EXISTS experiments (
    id SERIAL PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    variant_name TEXT NOT NULL,
    impressions INT NOT NULL CHECK (impressions >= 0),
    clicks INT NOT NULL CHECK (clicks >= 0),
    cost FLOAT NOT NULL CHECK (cost >= 0),
    event_date DATE NOT NULL,
    context JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for quick queries
CREATE INDEX IF NOT EXISTS idx_experiment_name ON experiments (experiment_name);
CREATE INDEX IF NOT EXISTS idx_variant_name ON experiments (variant_name);
CREATE INDEX IF NOT EXISTS idx_event_date ON experiments (event_date);
CREATE INDEX IF NOT EXISTS idx_context_jsonb ON experiments USING GIN (context);

-- Suggested allocations table
CREATE TABLE IF NOT EXISTS allocations (
    id SERIAL PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    variant_name TEXT NOT NULL,
    allocated_pct FLOAT NOT NULL CHECK (allocated_pct >= 0 AND allocated_pct <= 1),
    algorithm TEXT NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_alloc_variant_date UNIQUE (experiment_name, variant_name, algorithm, date)
);

-- Indexes for quick queries
CREATE INDEX IF NOT EXISTS idx_alloc_experiment_name ON allocations (experiment_name);
CREATE INDEX IF NOT EXISTS idx_alloc_variant_name ON allocations (variant_name);
CREATE INDEX IF NOT EXISTS idx_alloc_date ON allocations (date);

-- Comments for documentation
COMMENT ON TABLE experiments IS 'Stores data about Multi-Armed Bandit experiments, including context.';
COMMENT ON COLUMN experiments.context IS 'Additional context in JSONB format (e.g., device, location, etc.).';
COMMENT ON TABLE allocations IS 'Stores traffic allocation recommendations by variant and date.';

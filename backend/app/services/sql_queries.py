INSERT_EXPERIMENT = '''
INSERT INTO experiments (experiment_name, variant_name, impressions, clicks, event_date, context)
VALUES (%s, %s, %s, %s, %s, %s);
'''

SELECT_EXPERIMENTS = '''
SELECT id, experiment_name, variant_name, impressions, clicks, event_date, context, created_at
FROM experiments
ORDER BY event_date DESC, created_at DESC
LIMIT %s;
'''

INSERT_ALLOCATION = '''
INSERT INTO allocations (experiment_name, variant_name, allocated_pct, date)
VALUES (%s, %s, %s, %s)
ON CONFLICT (experiment_name, variant_name, date) DO NOTHING;
'''

SELECT_ALLOCATIONS = '''
SELECT id, experiment_name, variant_name, allocated_pct, date, created_at
FROM allocations
ORDER BY date DESC, created_at DESC
LIMIT %s;
'''

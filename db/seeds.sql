-- Sample experiments for homepage_test
INSERT INTO experiments (experiment_name, variant_name, impressions, clicks, event_date, context)
VALUES
  ('homepage_test', 'A', 1000, 120, '2025-08-18', '{"device": "mobile"}'),
  ('homepage_test', 'B', 950, 150, '2025-08-18', '{"device": "mobile"}'),
  ('homepage_test', 'A', 1100, 130, '2025-08-19', '{"device": "desktop"}'),
  ('homepage_test', 'B', 1050, 160, '2025-08-19', '{"device": "desktop"}'),
  ('homepage_test', 'A', 1200, 140, '2025-08-20', '{"device": "mobile"}'),
  ('homepage_test', 'B', 1150, 170, '2025-08-20', '{"device": "mobile"}');

-- Sample experiments for checkout_test
INSERT INTO experiments (experiment_name, variant_name, impressions, clicks, event_date, context)
VALUES
  ('checkout_test', 'A', 800, 90, '2025-08-18', '{"device": "desktop"}'),
  ('checkout_test', 'B', 850, 110, '2025-08-18', '{"device": "desktop"}'),
  ('checkout_test', 'A', 900, 100, '2025-08-19', '{"device": "mobile"}'),
  ('checkout_test', 'B', 950, 120, '2025-08-19', '{"device": "mobile"}');

-- Sample suggested allocations
INSERT INTO allocations (experiment_name, variant_name, allocated_pct, date)
VALUES
  ('homepage_test', 'A', 0.45, '2025-08-21'),
  ('homepage_test', 'B', 0.55, '2025-08-21'),
  ('checkout_test', 'A', 0.50, '2025-08-20'),
  ('checkout_test', 'B', 0.50, '2025-08-20');

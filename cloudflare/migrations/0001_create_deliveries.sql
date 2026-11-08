CREATE TABLE IF NOT EXISTS deliveries (
  purchase_id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  license_key TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'sent')),
  created_at TEXT NOT NULL
);

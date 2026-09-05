-- ============================================================
-- TNG OS EVENT TICKETING - PRODUCTION POSTGRES MIGRATION
-- ============================================================

ALTER TABLE ticket_orders
ADD COLUMN IF NOT EXISTS clover_checkout_id VARCHAR(255);

ALTER TABLE ticket_orders
ADD COLUMN IF NOT EXISTS items_json TEXT;

ALTER TABLE issued_tickets
ADD COLUMN IF NOT EXISTS qr_token_encrypted TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS
ix_ticket_orders_clover_checkout_id
ON ticket_orders (clover_checkout_id)
WHERE clover_checkout_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS
ix_ticket_orders_event_id
ON ticket_orders (event_id);

CREATE INDEX IF NOT EXISTS
ix_issued_tickets_event_id
ON issued_tickets (event_id);

CREATE INDEX IF NOT EXISTS
ix_issued_tickets_ticket_number
ON issued_tickets (ticket_number);

CREATE INDEX IF NOT EXISTS
ix_issued_tickets_qr_token_hash
ON issued_tickets (qr_token_hash);

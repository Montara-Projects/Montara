-- D1 European-jurisdiction pilot; schema is deployed as montara-r2-pilot-quotas-eu.
-- This migration contains NO Google identities, passwords or R2 credentials.
-- Clients MUST NOT set tenant_key; backend derives tenant only after verified OAuth.
CREATE TABLE IF NOT EXISTS pilot_tenants (
 tenant_key TEXT PRIMARY KEY CHECK(tenant_key IN ('fergardel','amehc','t4t')),
 plan TEXT NOT NULL CHECK(plan IN ('basic','plus','premium')),
 quota_bytes INTEGER NOT NULL CHECK(quota_bytes>0),
 used_bytes INTEGER NOT NULL DEFAULT 0 CHECK(used_bytes>=0),
 reserved_bytes INTEGER NOT NULL DEFAULT 0 CHECK(reserved_bytes>=0),
 oauth_issuer TEXT,
 oauth_subject TEXT UNIQUE,
 state TEXT NOT NULL DEFAULT 'pending_identity' CHECK(state IN ('pending_identity','pilot_active','suspended')),
 CHECK(used_bytes + reserved_bytes <= quota_bytes),
 CHECK((oauth_issuer IS NULL AND oauth_subject IS NULL AND state!='pilot_active')
    OR (oauth_issuer IS NOT NULL AND oauth_subject IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS quota_reservations (
 reservation_id TEXT PRIMARY KEY,
 tenant_key TEXT NOT NULL REFERENCES pilot_tenants(tenant_key),
 asset_id TEXT NOT NULL,
 bytes INTEGER NOT NULL CHECK(bytes>0),
 state TEXT NOT NULL CHECK(state IN ('reserved','committed','cancelled')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 expires_at TEXT NOT NULL,
 UNIQUE(tenant_key,asset_id)
);
INSERT INTO pilot_tenants(tenant_key,plan,quota_bytes) VALUES
 ('fergardel','basic',100000000000),
 ('amehc','plus',250000000000),
 ('t4t','premium',500000000000)
 ON CONFLICT(tenant_key) DO NOTHING;

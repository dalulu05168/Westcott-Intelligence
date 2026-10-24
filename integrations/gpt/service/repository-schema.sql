-- Additive tables; existing source and progress records stay intact.
CREATE TABLE IF NOT EXISTS repository_exports (
 export_hash TEXT PRIMARY KEY, commit_sha TEXT NOT NULL,
 payload TEXT NOT NULL, stored_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS repository_export_chunks (
 export_hash TEXT NOT NULL, part INTEGER NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(export_hash,part)
);

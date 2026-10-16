# Automatic review draft adapter

Imported and repaired from the user-provided files.zip, 2026-10-16. Only news/pending drafts are supported. This module is not scheduled and does not send Telegram, write approved ledgers, or self-confirm claims. The original five paused tasks remain unchanged.

Requires OPENAI_API_KEY and explicit OPENAI_NEWS_MODEL for actual model calls. No credentials or paid service were created. All candidates are assessed for each country; current original bodies must match snapshot hashes. Snapshot selection uses timestamps, COMPLETE coverage and the existing 20-minute boundary. Numeric literals must be nonempty and contain the stated source number; numeric normalization and semantic meaning still need external review.

Automatic attest/promote is disabled. Submit a separately verified ledger through the existing reviewed publisher only after full factual, semantic, country-specific and deduplication review. Tests exercise numeric mismatch, cross-country assessment, source changes, freshness and disabled self-confirmation. Tests do not prove real model quality or live delivery.

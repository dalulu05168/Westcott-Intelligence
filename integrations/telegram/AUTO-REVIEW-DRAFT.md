# Free news review strategy

User instruction confirmed 2026-10-16: no additional paid API service. Official public-source intake remains active. The hourly ChatGPT review task reads complete current editions, independently verifies original bodies, compares all candidates for RO and FR, and submits only verified eligible ledgers to the existing GitHub release gate. No qualifying story means no publication. Delivery must be confirmed from actual audit receipts.

The newly added API draft-review workflow steps have been removed. auto_review.call_llm is disabled before any network request, even when API credentials exist. OPENAI_API_KEY and OPENAI_NEWS_MODEL are not required for this strategy. Telegram credentials and the original five paused tasks are unchanged. Real-time market data remains held until a suitable verified free source is actually available; delayed data must not be labelled real-time.

Existing GitHub account usage quotas and ChatGPT availability still apply; this change does not guarantee uninterrupted or unlimited service.

#!/usr/bin/env python3
"""Validate SNN 2026-10-21 adopted-story member state. No live trading claims."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
v1=json.loads((ROOT/"memory/member-stock/ledger-v1.json").read_text(encoding="utf-8"))
v2=json.loads((ROOT/"memory/member-stock/ledger-v2.json").read_text(encoding="utf-8"))
assert v2["schema"]=="westcott-member-stock-participation-ledger-v2"
assert v2["timezone"]=="Europe/Bucharest"
assert v2["records"][:len(v1["records"])]==v1["records"],"legacy events mutated"
expected_ids={f"{i:02d}" for i in range(1,66)}
assert set(v2["by_member"])==expected_ids
events=v2["records"]
assert len(events)==len({e["id"] for e in events})
idx={i:[] for i in expected_ids}
for e in events:
    assert e["member_id"] in idx
    idx[e["member_id"]].append(e["id"])
assert idx==v2["by_member"],"index mismatch"
new=[e for e in events if e.get("story_date")=="2026-10-21" and e.get("symbol")=="SNN"]
assert len(new)==7
follow={e["member_id"] for e in new if e["action"]=="FOLLOW_RECOMMENDATION_EDITOR_ANNOTATED_UNVERIFIED_EXECUTION"}
assert follow=={"01","14","24","25","27","28"}
watch={e["member_id"] for e in new if e["action"]=="WATCH_ONLY"}
assert watch=={"17"}
assert all(e["source_document_id"]=="1frtoFvohP3u2HfRzBPRZVLOzMfvnO-8Vi9iX3r5rmiM" and
           e["source_tab_id"]=="t.toc19bjz91ue" and e["source_revision_at_review"] and
           isinstance(e["source_paragraph_number"],int) for e in new)
assert all("跟推荐买票" in e["source_speech"] and e["editor_annotation"]=="（跟推荐买票）" for e in new if e["member_id"] in follow)
assert all(e["story_participation_confirmed"] is (e["member_id"] in follow) for e in new)
assert all(e["real_trade_verified"] is False and e["order_filled_verified"] is False and
           e["actual_execution_time"] is None and e["reported_quantity"] is None and
           e["reported_price"] is None and e["outcome_or_position_estimate"] is None for e in new)
print(json.dumps({"status":"PASS_STORY_PROVENANCE_STATIC","legacy_records":len(v1["records"]),
                  "snn_follow_story_members":sorted(follow),"snn_watch_members":sorted(watch),
                  "indexed_members":len(idx),"real_broker_executions_verified":0},ensure_ascii=False))

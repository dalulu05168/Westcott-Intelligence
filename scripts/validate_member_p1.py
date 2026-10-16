#!/usr/bin/env python3
"""P1 identity, draft-voice and adopted-history audit. Read-only; never creates persona history."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("id","name","nick","gender","age","occupation","investment_years",
          "capital_scale","student_seniority","location","background_note")
def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))
def audit():
    people = load("skills/p004-chat-suite/characters/final-identity-65.json")["people"]
    roster = {p["id"]:p for p in people}
    errors, warnings, rows = [], [], []
    if len(people)!=65 or len(roster)!=65 or set(roster)!={f"{n:02}" for n in range(1,66)}:
        errors.append("CANONICAL_ID_SET_NOT_65")
    adopted = {}
    for path in sorted((ROOT/"memory/daily").glob("*/day-memory.json")):
        day=load(path.relative_to(ROOT))
        date=day.get("story_date",path.parent.name)
        adopted[date]={m["id"]:m for m in day.get("messages",[])
                       if m.get("status") in ("ADOPTED_IN_SUBMITTED_TRANSCRIPT","ADOPTED_IN_USER_SUBMITTED_STORY")}
    for pid in sorted(roster):
        canonical=roster[pid]
        profile_path=f"skills/p004-chat-suite/characters/profiles/{pid}.json"
        mem_path=f"memory/long-term/members/{pid}.json"
        entry={"id":pid,"identity":"PASS","voice":"UNAPPROVED_CREATIVE_DRAFT",
               "long_term":"NO_ADOPTED_HISTORY_IN_SEPARATE_FILE","evidence_count":0,"warnings":[]}
        try:
            profile=load(profile_path)
            for field in FIELDS:
                if canonical.get(field)!=profile.get(field):
                    errors.append(f"IDENTITY_MISMATCH:{pid}:{field}")
                    entry["identity"]="FAIL"
            voice=profile.get("voice")
            if not isinstance(voice,dict) or not voice.get("voice_status"):
                errors.append(f"VOICE_STATUS_MISSING:{pid}")
                entry["voice"]="FAIL"
            elif voice["voice_status"]!="CREATIVE_DRAFT_NOT_USER_APPROVED":
                entry["voice"]=voice["voice_status"]
                if not profile.get("approved_by_user"):
                    errors.append(f"UNAPPROVED_VOICE_PROMOTED:{pid}")
        except (ValueError, OSError, KeyError) as e:
            errors.append(f"PROFILE_UNREADABLE:{pid}:{type(e).__name__}")
            entry["identity"]="FAIL"
        mem_file=ROOT/mem_path
        if mem_file.exists():
            try:
                mem=load(mem_path)
                entry["long_term"]="REVIEWED_EVIDENCE_FILE"
                if mem.get("id")!=pid or mem.get("name")!=canonical["name"]:
                    errors.append(f"MEMORY_IDENTITY_MISMATCH:{pid}")
                observed=mem.get("observed_in_submitted_story",[])
                if not isinstance(observed,list):
                    errors.append(f"INVALID_OBSERVED_RECORDS:{pid}")
                    observed=[]
                entry["evidence_count"]=len(observed)
                if mem.get("message_count") is not None and mem["message_count"]!=sum(e.get("kind","message")=="message" for e in observed):
                    warnings.append(f"MEMORY_COUNT_DIFF:{pid}")
                for i,evt in enumerate(observed):
                    mid=evt.get("message_id"); day=evt.get("source_date")
                    evidence=adopted.get(day,{}).get(mid)
                    if evidence is None:
                        entry["warnings"].append(f"ARCHIVE_ID_NOT_MATCHED:{day}:{mid}")
                    elif evidence.get("speaker_id")!=pid or evidence.get("text","").strip()!=evt.get("text","").strip():
                        errors.append(f"MEMORY_EVIDENCE_CONFLICT:{pid}:{mid}")
                if not observed:
                    entry["long_term"]="EMPTY_EVIDENCE_FILE"
            except (ValueError,OSError,KeyError) as e:
                errors.append(f"MEMORY_UNREADABLE:{pid}:{type(e).__name__}")
                entry["long_term"]="FAIL"
        rows.append(entry)
    return {"schema":"westcott-p1-member-audit-v1","count":len(rows),
            "profiles_checked":sum(x["identity"]=="PASS" for x in rows),
            "memory_files_checked":sum(x["long_term"] not in ("NO_ADOPTED_HISTORY_IN_SEPARATE_FILE","FAIL") for x in rows),
            "no_separate_memory_ids":[x["id"] for x in rows if x["long_term"]=="NO_ADOPTED_HISTORY_IN_SEPARATE_FILE"],
            "errors":errors,"warnings":warnings,"members":rows,
            "note":"Unmatched archive message IDs are review flags, not proof of fabricated history. Voice drafts are not approved history."}
def main():
    result=audit()
    out=ROOT/"audit/member-p1-validation.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("P1_AUDIT_SUMMARY="+json.dumps({k:result[k] for k in ("count","profiles_checked","memory_files_checked","no_separate_memory_ids","errors","warnings")},ensure_ascii=False))
    print("P1_AUDIT_REPORT="+str(out.relative_to(ROOT)))
    return 1 if result["errors"] else 0
if __name__=="__main__":
    sys.exit(main())

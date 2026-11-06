from __future__ import annotations
import json
from .models import Bundle,CheckResult
def inspect_data(b:Bundle):return {"path":b.path,"before_sha256":b.before_sha256,"after_sha256":b.after_sha256,"replacement_bytes":len(b.after_text.encode("utf-8")),"content_changes":b.before_sha256!=b.after_sha256}
def inspect_report(b:Bundle,fmt:str)->str:
 d=inspect_data(b)
 if fmt=="json":return json.dumps(d,ensure_ascii=False,indent=2)+"\n"
 return f"Target path: {d['path']}\nExpected original SHA-256: {d['before_sha256']}\nReplacement SHA-256: {d['after_sha256']}\nReplacement bytes: {d['replacement_bytes']}\nContent changes: {'yes' if d['content_changes'] else 'no'}\n"
def status_report(r:CheckResult,fmt:str)->str:
 d={"status":r.status,"target":r.target,"actual_sha256":r.actual_sha256,"message":r.message}
 if r.diff is not None:d["diff"]=r.diff
 if fmt=="json":return json.dumps(d,ensure_ascii=False,indent=2)+"\n"
 out=f"Status: {r.status}\nTarget: {r.target}\n{r.message}\n"
 if r.diff is not None:out+="\n"+r.diff
 return out

from __future__ import annotations
import difflib,os,stat,tempfile
from pathlib import Path
from .bundles import hash_bytes
from .models import Bundle,CheckResult
from .paths import safe_target

def check_target(bundle:Bundle,root:Path)->CheckResult:
 target=safe_target(root,bundle.path)
 if not target.exists():return CheckResult("conflict",str(target),None,"target is missing")
 if not target.is_file():return CheckResult("conflict",str(target),None,"target is not a regular file")
 try:data=target.read_bytes()
 except OSError as e:return CheckResult("conflict",str(target),None,f"cannot read target: {e}")
 actual=hash_bytes(data)
 if actual==bundle.before_sha256:return CheckResult("ready",str(target),actual,"target matches expected original hash")
 if actual==bundle.after_sha256:return CheckResult("already_applied",str(target),actual,"replacement content is already present")
 return CheckResult("conflict",str(target),actual,"target hash matches neither baseline nor replacement")
def unified_preview(target:Path,bundle:Bundle)->str:
 before=target.read_bytes().decode("utf-8");after=bundle.after_text
 diff="\n".join(difflib.unified_diff(before.splitlines(),after.splitlines(),fromfile=bundle.path+" (current)",tofile=bundle.path+" (replacement)",lineterm=""))+"\n"
 if before and not before.endswith(("\n","\r")):diff+="\\ No newline at end of current file\n"
 if after and not after.endswith(("\n","\r")):diff+="\\ No newline at end of replacement file\n"
 return diff
def _write_temp(target:Path,data:bytes,mode:int)->Path:
 fd,name=tempfile.mkstemp(prefix=".patchport-",suffix=".tmp",dir=target.parent)
 try:
  with os.fdopen(fd,"wb") as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(name,mode);return Path(name)
 except BaseException:
  try:os.close(fd)
  except OSError:pass
  Path(name).unlink(missing_ok=True);raise
def apply_bundle(bundle:Bundle,root:Path,dry_run:bool=False)->CheckResult:
 status=check_target(bundle,root);target=Path(status.target)
 if status.status!="ready":return status
 if dry_run:return CheckResult("ready",status.target,status.actual_sha256,status.message,unified_preview(target,bundle))
 mode=stat.S_IMODE(target.stat().st_mode);temp=_write_temp(target,bundle.after_text.encode("utf-8"),mode)
 try:
  final=check_target(bundle,root)
  if final.status!="ready":return final
  os.replace(temp,target);temp=None
  return CheckResult("applied",str(target),bundle.after_sha256,"replacement applied successfully")
 finally:
  if temp is not None:temp.unlink(missing_ok=True)

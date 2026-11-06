from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from typing import Any
from .models import Bundle
from .paths import PathError,validate_bundle_path
_FIELDS={"schema_version","path","before_sha256","after_sha256","after_text"};_HASH=re.compile(r"\A[0-9a-f]{64}\Z")
class BundleError(Exception):pass
class _Duplicate(ValueError):pass
def _strict(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise _Duplicate(f"duplicate JSON key {k!r}")
  out[k]=v
 return out
def hash_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def read_text_bytes(path:Path)->tuple[bytes,str]:
 try:data=path.read_bytes()
 except OSError as e:raise BundleError(f"cannot read text file {path}: {e}") from e
 try:text=data.decode("utf-8")
 except UnicodeDecodeError as e:raise BundleError(f"file is not valid UTF-8: {path}") from e
 if "\x00" in text:raise BundleError(f"text contains NUL bytes: {path}")
 return data,text
def bundle_from_data(data:Any)->Bundle:
 if not isinstance(data,dict):raise BundleError("bundle root must be an object")
 if set(data)!=_FIELDS:
  missing=sorted(_FIELDS-set(data));unknown=sorted(set(data)-_FIELDS);parts=[]
  if missing:parts.append("missing field(s): "+", ".join(missing))
  if unknown:parts.append("unknown field(s): "+", ".join(unknown))
  raise BundleError("; ".join(parts))
 if not isinstance(data["schema_version"],int) or isinstance(data["schema_version"],bool) or data["schema_version"]!=1:raise BundleError("unsupported schema_version; expected integer 1")
 try:validate_bundle_path(data["path"])
 except PathError as e:raise BundleError(str(e)) from e
 for name in ("before_sha256","after_sha256"):
  if not isinstance(data[name],str) or not _HASH.fullmatch(data[name]):raise BundleError(f"{name} must be 64 lowercase hexadecimal characters")
 text=data["after_text"]
 if not isinstance(text,str):raise BundleError("after_text must be a string")
 if "\x00" in text:raise BundleError("after_text must not contain NUL bytes")
 encoded=text.encode("utf-8")
 if hash_bytes(encoded)!=data["after_sha256"]:raise BundleError("after_sha256 does not match UTF-8 replacement content")
 return Bundle(data["path"],data["before_sha256"],data["after_sha256"],text)
def create_bundle(before:Path,after:Path,target_path:str)->Bundle:
 validate_bundle_path(target_path);before_bytes,_=read_text_bytes(before);after_bytes,after_text=read_text_bytes(after);return Bundle(target_path,hash_bytes(before_bytes),hash_bytes(after_bytes),after_text)
def serialize_bundle(bundle:Bundle)->bytes:
 data={"schema_version":1,"path":bundle.path,"before_sha256":bundle.before_sha256,"after_sha256":bundle.after_sha256,"after_text":bundle.after_text};bundle_from_data(data);return (json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
def save_bundle(path:Path,bundle:Bundle):
 payload=serialize_bundle(bundle);path.parent.mkdir(parents=True,exist_ok=True);created=False
 try:
  with path.open("xb") as f:created=True;f.write(payload)
 except BaseException:
  if created:
   try:path.unlink(missing_ok=True)
   except OSError:pass
  raise
def load_bundle(path:Path)->Bundle:
 try:text=path.read_text(encoding="utf-8")
 except (OSError,UnicodeError) as e:raise BundleError(f"cannot read bundle {path}: {e}") from e
 try:data=json.loads(text,object_pairs_hook=_strict)
 except _Duplicate as e:raise BundleError(str(e)) from e
 except json.JSONDecodeError as e:raise BundleError(f"malformed bundle JSON at line {e.lineno}, column {e.colno}: {e.msg}") from e
 return bundle_from_data(data)

from __future__ import annotations
import argparse,sys
from collections.abc import Sequence
from pathlib import Path
from . import __version__
from .apply import apply_bundle,check_target
from .bundles import BundleError,create_bundle,load_bundle,save_bundle
from .paths import PathError
from .reports import inspect_report,status_report
def _parser():
 p=argparse.ArgumentParser(prog="patchport",description="Create and apply guarded one-file UTF-8 replacement bundles.");p.add_argument("--version",action="version",version=f"%(prog)s {__version__}");s=p.add_subparsers(dest="command",required=True)
 m=s.add_parser("make");m.add_argument("before",type=Path);m.add_argument("after",type=Path);m.add_argument("--path",required=True);m.add_argument("--output",required=True,type=Path)
 i=s.add_parser("inspect");i.add_argument("bundle",type=Path);i.add_argument("--format",choices=("text","json"),default="text")
 c=s.add_parser("check");c.add_argument("bundle",type=Path);c.add_argument("--root",type=Path,required=True);c.add_argument("--format",choices=("text","json"),default="text")
 a=s.add_parser("apply");a.add_argument("bundle",type=Path);a.add_argument("--root",type=Path,required=True);a.add_argument("--dry-run",action="store_true");a.add_argument("--format",choices=("text","json"),default="text")
 return p
def main(argv:Sequence[str]|None=None)->int:
 a=_parser().parse_args(argv)
 try:
  if a.command=="make":
   if a.output.exists():raise FileExistsError(f"bundle output already exists: {a.output}")
   b=create_bundle(a.before,a.after,a.path);save_bundle(a.output,b);print(f"Wrote bundle: {a.output.resolve()}");return 0
  b=load_bundle(a.bundle)
  if a.command=="inspect":sys.stdout.write(inspect_report(b,a.format));return 0
  result=check_target(b,a.root) if a.command=="check" else apply_bundle(b,a.root,a.dry_run);sys.stdout.write(status_report(result,a.format));return 1 if result.status=="conflict" else 0
 except (BundleError,PathError,OSError,UnicodeError,ValueError) as e:print(f"error: {e}",file=sys.stderr);return 2
 return 2

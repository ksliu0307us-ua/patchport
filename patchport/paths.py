from __future__ import annotations
import os,stat
from pathlib import Path,PurePosixPath,PureWindowsPath

class PathError(Exception):pass
def validate_bundle_path(value):
    if not isinstance(value,str) or not value:raise PathError("target path must be a nonempty string")
    if "\\" in value:raise PathError("target path must use POSIX forward slashes")
    p=PurePosixPath(value);w=PureWindowsPath(value)
    if p.is_absolute() or w.is_absolute() or w.drive:raise PathError("target path must be relative")
    if str(p)!=value or any(x in (".","..") for x in p.parts):raise PathError("target path must be canonical without traversal")
    if any(x.lower()==".git" for x in p.parts):raise PathError("targets inside .git metadata are forbidden")
    return value
def safe_target(root:Path,relative:str)->Path:
    validate_bundle_path(relative)
    if root.is_symlink():raise PathError("selected root must not be a symbolic link")
    resolved=root.resolve()
    if not resolved.is_dir():raise PathError(f"selected root is not a directory: {root}")
    target=resolved.joinpath(*PurePosixPath(relative).parts)
    if not target.resolve(strict=False).is_relative_to(resolved):raise PathError("target escapes selected root")
    current=resolved
    for part in PurePosixPath(relative).parts[:-1]:
        current=current/part
        if not current.exists():break
        metadata=current.lstat()
        if stat.S_ISLNK(metadata.st_mode):raise PathError(f"symbolic-link parent is forbidden: {current}")
        if not stat.S_ISDIR(metadata.st_mode):break
    if target.exists() or target.is_symlink():
        if stat.S_ISLNK(target.lstat().st_mode):raise PathError(f"symbolic-link target is forbidden: {target}")
    return target

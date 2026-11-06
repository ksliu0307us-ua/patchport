from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Bundle:
    path:str
    before_sha256:str
    after_sha256:str
    after_text:str
    schema_version:int=1
@dataclass(frozen=True, slots=True)
class CheckResult:
    status:str
    target:str
    actual_sha256:str|None
    message:str
    diff:str|None=None

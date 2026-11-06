# PatchPort roadmap

All items are proposed and unimplemented. Total estimate: **30 engineering hours**.

## Recoverable multi-file application with a journal — 9 hours
Add an explicit transaction journal and rollback for multiple files.
Acceptance: interruption tests at every phase, durable journal flushing, collision
refusal, and deterministic recovery without touching unrelated files.

## Apply receipts and user-invoked restoration — 5 hours
Persist opt-in receipts and exact prior bytes for deliberate restore commands.
Acceptance: receipts are versioned, restoration validates current hashes, and no
automatic rollback overwrites later user work.

## Creation, deletion, and rename operations — 7 hours
Extend bundles with explicit operation kinds.
Acceptance: every operation has baseline/precondition checks, containment and
symlink defenses remain enforced, and partial output is cleaned safely.

## Bounded unified-diff interoperability — 5 hours
Import/export a documented subset of single-file unified diffs.
Acceptance: unsupported headers/features fail clearly, path safety is reused, and
round-trip fixtures preserve newline semantics.

## Cross-platform metadata verification — 4 hours
Expand Windows/macOS/Linux tests for permission and replacement semantics.
Acceptance: documentation states verified guarantees per platform and never claims
ownership, ACL, xattr, or timestamp preservation without tests.

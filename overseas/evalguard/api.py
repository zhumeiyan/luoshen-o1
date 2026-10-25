"""evalguard public API — the stable surface other code may depend on.

Why this file exists
--------------------
Before this file, the only entry point was `cli.scan()`, which took a
filesystem path, read the file itself, and returned a list of raw dicts
whose shape was whatever the gate happened to leave behind. That is fine
for a terminal and unusable for an integration: you cannot scan a string,
you cannot tell which keys are guaranteed, and every consumer re-implements
severity ordering.

So this module fixes three things:

  1. `scan_source()` — scan code you already have in memory. Needed by any
     editor plugin, CI hook or agent that never wrote the file to disk.
  2. `Finding` / `ScanResult` — declared, stable, total. Every field always
     exists, with a documented type. Raw dicts stay available via
     `.to_dict()` so nothing that works today breaks.
  3. `to_sarif()` — the SARIF 2.1.0 output GitHub Code Scanning consumes.
     This is what makes the tool a *repository* interface rather than a
     local script: upload the file and findings appear inline on the PR.

Design rule enforced here: **this module must never raise on bad input.**
A scanner that crashes on the file it was pointed at is worse than one
that reports nothing, because it fails the pipeline at the wrong place.
Malformed input comes back as a SyntaxError finding (EG000), same as the
CLI does.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

from . import cli

__all__ = [
    "Finding", "ScanResult",
    "scan_source", "scan_file", "scan_paths", "scan_dir",
    "SEVERITIES",
]

SEVERITIES = ("blocker", "warn", "info")
_ORDER = {s: i for i, s in enumerate(SEVERITIES)}

_VERSION = "0.5.1"
_TOOL_NAME = "evalguard"


# --------------------------------------------------------------------------
# Finding
# --------------------------------------------------------------------------
@dataclass
class Finding:
    """One canon-backed failure mode, located in one place.

    `line` is None when the claim is about the whole file. That is not a
    missing value to be patched over: rules of kind `absent` accuse a thing
    that does NOT exist (no baseline was ever reported), and there is
    literally no line that can exhibit an absence. exp133 measured those
    findings at 0/9 "true" when a line was forced onto them. So None is the
    honest answer and `scope` says so.
    """
    eg_id: str
    severity: str
    title: str
    file: str
    line: int | None = None
    hit: str = ""
    why: str = ""
    fix: str = ""
    canon: list = field(default_factory=list)
    scope: str = "line"
    kind: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def location(self) -> str:
        return f"{self.file}:{self.line}" if self.line is not None else self.file

    def __str__(self) -> str:
        return f"[{self.severity.upper():7s}] {self.eg_id} {self.location} — {self.title}"


def _mk(rule: dict, fpath: str) -> list[Finding]:
    """Flatten one raw rule dict into one Finding per evidence hit."""
    hits = rule.get("hits") or [{}]
    out = []
    for h in hits:
        out.append(Finding(
            eg_id=rule.get("eg_id", "EG???"),
            severity=rule.get("severity", "info"),
            title=rule.get("title", ""),
            file=fpath,
            line=h.get("line"),
            hit=(h.get("hit") or "")[:400],
            why=rule.get("why", ""),
            fix=rule.get("fix", ""),
            canon=list(rule.get("canon", [])),
            scope=h.get("scope", "file" if h.get("line") is None else "line"),
            kind=h.get("kind", ""),
        ))
    return out


# --------------------------------------------------------------------------
# ScanResult
# --------------------------------------------------------------------------
@dataclass
class ScanResult:
    """Everything a scan produced, plus the counts a CI gate needs."""
    findings: list = field(default_factory=list)
    files: list = field(default_factory=list)
    pro: bool = False
    #: gate bookkeeping, not findings. Kept so the drop rate stays auditable.
    audits: list = field(default_factory=list)

    # ---- counts ---------------------------------------------------------
    @property
    def counts(self) -> dict:
        c = {s: 0 for s in SEVERITIES}
        for f in self.findings:
            c[f.severity] = c.get(f.severity, 0) + 1
        return c

    @property
    def blockers(self) -> list:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def warns(self) -> list:
        return [f for f in self.findings if f.severity == "warn"]

    @property
    def infos(self) -> list:
        return [f for f in self.findings if f.severity == "info"]

    @property
    def ok(self) -> bool:
        """True when nothing blocking was found. This is the CI predicate."""
        return not self.blockers

    def limit(self, min_severity: str = "info") -> "ScanResult":
        ceil = _ORDER.get(min_severity, 2)
        return ScanResult(
            findings=[f for f in self.findings if _ORDER.get(f.severity, 2) <= ceil],
            files=list(self.files), pro=self.pro, audits=list(self.audits))

    def sorted(self) -> "ScanResult":
        return ScanResult(
            findings=sorted(self.findings,
                            key=lambda f: (_ORDER.get(f.severity, 2),
                                           f.file, f.line or 0, f.eg_id)),
            files=list(self.files), pro=self.pro, audits=list(self.audits))

    # ---- serialisation --------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "tool": _TOOL_NAME, "version": _VERSION, "pro": self.pro,
            "files": list(self.files), "counts": self.counts,
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
            "audits": [a.to_dict() for a in self.audits],
        }

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_text(self) -> str:
        if not self.findings:
            return f"clean — no canon-backed failure mode detected ({len(self.files)} file(s))"
        lines = [str(f) for f in self.sorted().findings]
        c = self.counts
        lines.append("-" * 64)
        lines.append(f"{c['blocker']} blocker · {c['warn']} warn · {c['info']} info "
                     f"across {len(self.files)} file(s)")
        return "\n".join(lines)

    def to_sarif(self) -> dict:
        """SARIF 2.1.0 — the shape GitHub Code Scanning ingests.

        Producing this is what turns evalguard from a script you run into a
        check that shows up on a pull request. Rules are emitted as a
        `rules` array so the GitHub UI can render each failure mode with
        its own help text instead of one blob.
        """
        rules_seen = {}
        results = []
        for f in self.findings:
            rules_seen.setdefault(f.eg_id, {
                "id": f.eg_id,
                "name": f.eg_id,
                "shortDescription": {"text": f.title},
                "fullDescription": {"text": (f.why or f.title)[:800]},
                "help": {"text": (f.fix or f.why or f.title)[:800]},
                "properties": {"tags": ["evaluation-integrity"],
                               "canon": f.canon},
            })
            level = {"blocker": "error", "warn": "warning",
                     "info": "note"}.get(f.severity, "note")
            # SARIF requires line >= 1. A file-level claim has no line; we
            # use 1 and say so in the message rather than inventing one.
            ln = f.line if isinstance(f.line, int) and f.line > 0 else 1
            results.append({
                "ruleId": f.eg_id,
                "level": level,
                "message": {"text": (
                    (f.hit or f.title) +
                    ("" if f.line else "  [file-level claim: no single line "
                                       "can exhibit an absence]"))},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.file},
                        "region": {"startLine": ln},
                    }}],
            })
        return {
            "$schema": ("https://raw.githubusercontent.com/oasis-tcs/"
                        "sarif-spec/master/Schemata/sarif-schema-2.1.0.json"),
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": _TOOL_NAME,
                        "version": _VERSION,
                        "informationUri": "https://github.com/zhumeiyan/luoshen-o1",
                        "rules": list(rules_seen.values()),
                    }},
                "results": results,
            }],
        }

    def __len__(self):
        return len(self.findings)

    def __iter__(self):
        return iter(self.findings)


# --------------------------------------------------------------------------
# entry points
# --------------------------------------------------------------------------
def _scan_tree(src: str, fpath: str, pro: bool):
    """Run the gate and split real findings from gate audit rows.

    Returns (findings, audits).

    The gate emits EG000 rows that are not findings at all -- they are its
    own bookkeeping ("N findings dropped for having no evidence line").
    Left in the stream they made every scan look dirty: the clean sample
    above reported 1 finding when the answer is 0. Separating them keeps
    the count honest without deleting the information, and `ScanResult.
    audits` exposes it to anyone who wants the gate's drop rate.
    """
    cli.PRO_ON[0] = bool(pro)
    try:
        raw = cli.scan(fpath)
    except Exception as e:                      # never let a scan raise
        return ([Finding(eg_id="EG000", severity="info", title="scan error",
                         file=fpath, hit=f"{type(e).__name__}: {e}")], [])
    findings, audits = [], []
    for r in raw or []:
        row = _mk(r, fpath)
        if r.get("eg_id") == "EG000" and str(r.get("title", "")).startswith("audit:"):
            audits.extend(row)
        else:
            findings.extend(row)
    return findings, audits


def scan_source(src: str, *, path: str = "<string>", pro: bool = False) -> ScanResult:
    """Scan Python source held in memory.

    This is the entry point for anything that does not have a file: an
    editor buffer, a notebook cell, a CI job that already read the diff, an
    agent that generated code and wants to check it before writing it.
    """
    # cli.scan() reads from disk by contract. Rather than fork its logic, we
    # hand it a real temp file so all of its path-based policy still applies.
    #
    # The temp file keeps the caller's *relative path*, not just a suffix.
    # This matters: `examples/foo.py` is demoted by G-ROLE because a file
    # that exists to demonstrate an API shape is held to a different
    # standard. A random /tmp/xxxx.py name silently disabled that policy,
    # so scanning an in-memory example scored stricter than the same file
    # on disk. Preserving the path is what makes scan_source() and
    # scan_file() agree.
    import tempfile, os
    rel = pathlib.PurePosixPath(str(path).replace("\\", "/"))
    tmpdir = tempfile.mkdtemp(prefix="evalguard_")
    tmp = os.path.join(tmpdir, *rel.parts) if rel.parts else os.path.join(tmpdir, "x.py")
    try:
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(src)
        findings, audits = _scan_tree(src, tmp, pro)
        for f in findings + audits:
            f.file = path          # report the name the caller knows
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    return ScanResult(findings=findings, files=[path], pro=pro, audits=audits)


def scan_file(path: str, *, pro: bool = False) -> ScanResult:
    p = pathlib.Path(path)
    src = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    findings, audits = _scan_tree(src, str(p), pro)
    return ScanResult(findings=findings, files=[str(p)], pro=pro, audits=audits)


def scan_paths(paths: Iterable[str], *, pro: bool = False) -> ScanResult:
    """Scan a mixed list of files and directories (directories recurse *.py)."""
    files = []
    for t in paths:
        pth = pathlib.Path(t)
        if pth.is_dir():
            files += sorted(str(x) for x in pth.rglob("*.py"))
        elif pth.exists():
            files.append(str(pth))
        else:
            # reported back as EG000, not silently skipped: a caller who
            # typos a path must see zero files scanned, not zero findings
            files.append(str(pth))
    findings, audits = [], []
    for f in files:
        r = scan_file(f, pro=pro)
        findings.extend(r.findings)
        audits.extend(r.audits)
    return ScanResult(findings=findings, files=files, pro=pro, audits=audits)


def scan_dir(path: str, *, pro: bool = False) -> ScanResult:
    return scan_paths([path], pro=pro)

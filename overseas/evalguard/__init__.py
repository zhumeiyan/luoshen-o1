"""evalguard — static checks for evaluation code that fails silently.

The failure mode this tool exists for: an AI evaluation script that runs
to completion, exits 0, prints a confident number, and is wrong. Nothing
crashes. Nothing warns. The number goes into a paper, a dashboard, or a
model release decision.

    from evalguard import scan_source
    r = scan_source(open("eval.py").read(), path="eval.py")
    if not r.ok:
        print(r.to_text())

Also usable as a repository check: `to_sarif()` emits SARIF 2.1.0, which
GitHub Code Scanning renders inline on a pull request.
"""
from .api import (Finding, ScanResult, scan_source, scan_file, scan_paths,
                  scan_dir, SEVERITIES)
from .rules import RULES

__version__ = "0.5.1"
__all__ = ["scan_source", "scan_file", "scan_paths", "scan_dir",
           "Finding", "ScanResult", "SEVERITIES", "RULES", "__version__"]

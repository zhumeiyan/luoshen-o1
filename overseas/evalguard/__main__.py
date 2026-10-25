import sys
from .cli import main

USAGE = """evalguard — static checks for evaluation code that fails silently

  python3 -m evalguard <path> [<path> ...]     scan files or directories
  python3 -m evalguard serve [--port 8787]     start the local HTTP API

scan options
  --format text|json|sarif     sarif uploads to GitHub Code Scanning
  --severity blocker|warn|info minimum severity to report
  --pro                        enable the 10 PRO rules
  --report OUT.html            write a standalone HTML report

serve options
  --port N      default 8787
  --host ADDR   default 127.0.0.1 (this is a local service; it parses the
                code you send it and never executes it)

examples
  python3 -m evalguard eval.py
  python3 -m evalguard . --format sarif > results.sarif
  python3 -m evalguard serve
  curl -s localhost:8787/scan -H 'Content-Type: application/json' \\
       -d '{"source":"acc=1/0\\n","path":"x.py"}'
"""

if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "serve":
        import argparse
        p = argparse.ArgumentParser(prog="evalguard serve")
        p.add_argument("--port", type=int, default=8787)
        p.add_argument("--host", default="127.0.0.1",
                       help="0.0.0.0 exposes the API to your network; this "
                            "service is not hardened for that")
        a = p.parse_args(argv[1:])
        from .server import serve
        print(f"evalguard API on http://{a.host}:{a.port}  "
              f"(GET /rules, POST /scan)", flush=True)
        try:
            serve(a.host, a.port)
        except KeyboardInterrupt:
            pass
        sys.exit(0)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)
    sys.exit(main())

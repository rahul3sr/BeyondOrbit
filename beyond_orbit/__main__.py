import argparse
from pathlib import Path
from .engine import read, render, check_approval

p = argparse.ArgumentParser(description="Beyond Orbit offline production; never uploads")
s = p.add_subparsers(dest="command", required=True)
d = s.add_parser("technical-fixture")
d.add_argument("--out", default="artifacts/first-experiment")
r = s.add_parser("render")
r.add_argument("spec")
r.add_argument("--out", required=True)
a = s.add_parser("verify-approval")
a.add_argument("artifact")
a.add_argument("record")
args = p.parse_args()
if args.command == "verify-approval":
    check_approval(args.artifact, args.record)
    print("Exact-version local approval record valid. No upload performed.")
else:
    spec = Path(__file__).resolve().parents[1]/"examples"/"original.json" if args.command == "technical-fixture" else args.spec
    result = render(read(spec), args.out, fixture=args.command == "technical-fixture")
    print(result)

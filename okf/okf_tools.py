#!/usr/bin/env python3
"""
okf_tools.py -- minimal, dependency-free helpers for Open Knowledge Format (OKF v0.1) bundles.

In keeping with OKF's own philosophy ("if you can cat a file, you can read OKF"), this uses
only the Python standard library -- no PyYAML, no third-party packages required.

Subcommands:
  validate <bundle>          Check OKF v0.1 Sec.9 conformance (non-empty `type` field in every
                              non-reserved .md file, parseable frontmatter everywhere).
  index <bundle>             (Re)generate index.md at every directory level of the bundle, listing
                              child concepts/subdirectories with their descriptions, for progressive
                              disclosure.
  graph <bundle> [--dot]     Print the cross-link graph derived from markdown links in concept
                              bodies. Use --dot for Graphviz DOT output.

Examples:
  python3 okf_tools.py validate ./sales
  python3 okf_tools.py index ./sales
  python3 okf_tools.py graph ./sales --dot | dot -Tsvg > graph.svg
"""
import argparse
import json
import re
import sys
from pathlib import Path

RESERVED = {"index.md", "log.md"}


def parse_frontmatter(text):
    """Return (frontmatter_dict_or_None, body_str).

    Implements a small YAML subset sufficient for OKF frontmatter: flat `key: value` pairs and
    inline lists `[a, b, c]`. This is deliberately not a general YAML parser -- OKF frontmatter
    is specified to be simple scalars/lists, and a full parser would add a dependency the format
    itself doesn't require.
    """
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    _, fm_block, body = parts
    fm = {}
    for line in fm_block.strip("\n").splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            fm[key] = items
        else:
            fm[key] = value.strip('"').strip("'")
    return fm, body.lstrip("\n")


def iter_md_files(bundle):
    for path in sorted(Path(bundle).rglob("*.md")):
        yield path


def cmd_validate(args):
    bundle = Path(args.bundle)
    if not bundle.is_dir():
        print(f"error: {bundle} is not a directory", file=sys.stderr)
        sys.exit(2)

    errors, warnings = [], []
    concept_count = 0
    type_counts = {}

    for path in iter_md_files(bundle):
        rel = path.relative_to(bundle)
        text = path.read_text(encoding="utf-8")
        fm, _body = parse_frontmatter(text)

        if path.name in RESERVED:
            continue

        concept_count += 1
        if fm is None:
            errors.append(f"{rel}: missing or unparseable YAML frontmatter")
            continue

        type_value = fm.get("type")
        if not type_value:
            errors.append(f"{rel}: missing required 'type' field (the one thing OKF requires)")
        else:
            type_counts[type_value] = type_counts.get(type_value, 0) + 1

        for soft_field in ("title", "description", "timestamp"):
            if not fm.get(soft_field):
                warnings.append(f"{rel}: no '{soft_field}' (optional, but recommended)")

    print(f"Scanned {concept_count} concept document(s) under {bundle}")
    if type_counts:
        print("\nType distribution:")
        for t, n in sorted(type_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>3}  {t}")

    if warnings and args.verbose:
        print(f"\n{len(warnings)} soft warning(s) (not spec violations, just good-practice gaps):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\n{len(errors)} conformance error(s):")
        for e in errors:
            print(f"  - {e}")
        print("\nNOT CONFORMANT with OKF v0.1 Sec.9")
        sys.exit(1)

    print("\nCONFORMANT with OKF v0.1 Sec.9")
    print("(every concept has parseable frontmatter and a non-empty 'type' field)")


def cmd_index(args):
    bundle = Path(args.bundle).resolve()
    all_dirs = {p.parent for p in iter_md_files(bundle)} | {bundle}

    written = []
    for d in sorted(all_dirs):
        try:
            entries = list(d.iterdir())
        except FileNotFoundError:
            continue
        child_files = sorted(
            p for p in entries if p.is_file() and p.suffix == ".md" and p.name not in RESERVED
        )
        child_dirs = sorted(
            p for p in entries if p.is_dir() and any(p.rglob("*.md"))
        )
        if not child_files and not child_dirs:
            continue

        label = d.name if d != bundle else bundle.name
        lines = [
            f"# {label}",
            "",
        ]
        if child_dirs:
            lines.append("## Subdirectories")
            for cd in child_dirs:
                lines.append(f"- [{cd.name}/]({cd.name}/index.md)")
            lines.append("")
        if child_files:
            lines.append("## Concepts")
            for cf in child_files:
                fm, _ = parse_frontmatter(cf.read_text(encoding="utf-8"))
                fm = fm or {}
                desc = fm.get("description") or fm.get("title") or ""
                suffix = f" - {desc}" if desc else ""
                lines.append(f"- [{cf.stem}]({cf.name}){suffix}")
            lines.append("")

        index_path = d / "index.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")
        written.append(index_path)

    for p in written:
        print(f"wrote {p}")
    print(f"\n{len(written)} index.md file(s) generated/refreshed")


def cmd_graph(args):
    bundle = Path(args.bundle)
    link_re = re.compile(r"\]\(((?:/|\./|\.\./)[^)]+?\.md)\)")
    graph = {}

    for path in iter_md_files(bundle):
        if path.name in RESERVED:
            continue
        rel = str(path.relative_to(bundle))
        _fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        targets = sorted(set(link_re.findall(body)))
        graph[rel] = targets

    if args.dot:
        print("digraph okf {")
        for src, targets in graph.items():
            for t in targets:
                print(f'  "{src}" -> "{t}";')
        print("}")
    else:
        print(json.dumps(graph, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Minimal OKF v0.1 bundle tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Check OKF v0.1 Sec.9 conformance")
    p_validate.add_argument("bundle")
    p_validate.add_argument("--verbose", action="store_true")
    p_validate.set_defaults(func=cmd_validate)

    p_index = sub.add_parser("index", help="(Re)generate index.md at every directory level")
    p_index.add_argument("bundle")
    p_index.set_defaults(func=cmd_index)

    p_graph = sub.add_parser("graph", help="Print the cross-link graph")
    p_graph.add_argument("bundle")
    p_graph.add_argument("--dot", action="store_true")
    p_graph.set_defaults(func=cmd_graph)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

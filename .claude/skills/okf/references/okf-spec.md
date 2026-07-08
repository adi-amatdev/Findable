# OKF v0.1 — condensed spec reference

Source of truth: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
Announcement: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing

Read this file when you need the exact rules. SKILL.md has the workflow; this has the ground truth.

## What OKF is, in one paragraph

Open Knowledge Format (OKF) is a vendor-neutral spec that formalizes the "LLM-wiki" pattern
(Obsidian vaults, AGENTS.md/CLAUDE.md files, metadata-as-code repos) into something interoperable:
a directory of markdown files with YAML frontmatter, no SDK or runtime required. It's a **format**,
not a service — anyone can produce it (by hand, by script, by agent) and anyone can consume it
(an LLM loading files into context, a static viewer, a search index). It complements MCP rather
than competing with it: MCP governs an agent's access to tools/data, OKF describes the knowledge
itself. It doesn't replace domain schemas (Avro, Protobuf, OpenAPI) — it references them.

## Terminology

- **Bundle** — a self-contained, hierarchical directory of knowledge documents. The unit of distribution.
- **Concept** — one unit of knowledge, represented as exactly one markdown file. Can describe a
  tangible asset (table, API, service) or an abstract idea (metric, process, decision).
- **Concept ID** — the concept's file path with the `.md` suffix removed. `tables/orders.md` → `tables/orders`.
- **Frontmatter** — the YAML block delimited by `---` at the top of a file.
- **Body** — everything after the frontmatter.
- **Link** — a normal markdown link from one concept to another, expressing a relationship
  beyond the implicit parent/child hierarchy of the directory tree.

## Bundle structure

```
sales/
├── index.md               # optional — directory listing, progressive disclosure
├── log.md                 # optional — chronological change history
├── some_concept.md        # a concept at the bundle root
└── tables/                # subdirectories group concepts into domains
    ├── index.md
    ├── orders.md
    └── customers.md
```

A bundle can be shipped as a git repo (recommended — history, blame, diffs, PR review), a
tarball/zip, or a subdirectory inside a larger repo (e.g. `docs/catalog/` next to the code it describes).

**Reserved filenames** — `index.md` and `log.md` have defined meaning at *any* level of the
hierarchy and MUST NOT be used as concept documents. Every other `.md` file is a concept document.

## Concept document format

```markdown
---
type: BigQuery Table          # REQUIRED — the only mandatory field
title: Orders                 # optional — display name
description: One row per completed customer order.   # optional — one-line summary
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders  # optional — canonical URI of the underlying asset
tags: [sales, revenue]        # optional — YAML list, short strings
timestamp: 2026-05-28T14:30:00Z  # optional — ISO 8601, last significant change
# ...producers may add any other key/value pairs; consumers must preserve them
---

# Schema

| Column | Type | Description |
|---|---|---|
| `order_id` | STRING | Globally unique order identifier. |
| `customer_id` | STRING | FK to [customers](/tables/customers.md). |

# Joins

Joined with [customers](/tables/customers.md) on `customer_id`.
```

- `type` is the **only required field**, and it's a free string the producer defines
  (`Service`, `Metric`, `API Endpoint`, `Runbook`, `Decision`, `BigQuery Table`, ...). Two teams
  drifting into `Table` vs. `BigQuery Table` for the same thing is a governance problem, not a
  format violation — agree on a type taxonomy up front within one bundle.
- `description` is used by index generators, search snippets, and previews — write it as one
  plain sentence, not a heading.
- `resource` is the canonical URI of the real-world thing the concept describes (a console link,
  a repo path, a dashboard). Omit it for concepts describing abstract ideas (a metric, a policy).
- Extension fields are explicitly welcomed (`owner:`, `freshness_sla:`, etc.) — consumers must not
  reject a document for unrecognized keys.

## Cross-linking

Concepts link to each other with ordinary markdown links — absolute bundle-relative paths
(`/tables/customers.md`), or relative paths (`./customers.md`). This turns the directory into a
**graph** that's richer than the parent/child links implied by the filesystem alone. There is no
special link syntax; a plain `[label](path.md)` is what makes the graph edge.

## Citations

When a concept's body makes claims sourced from external material, list them under a `# Citations`
heading at the bottom, numbered:

```markdown
# Citations
[1] [BigQuery public dataset announcement](https://cloud.google.com/blog/products/data-analytics/...)
[2] [Internal data quality runbook](https://wiki.acme.internal/data/quality)
```

Citation links may be absolute URLs, bundle-relative paths, or paths into a `references/`
subdirectory that mirrors external material as first-class OKF concepts (useful when you want an
external doc to itself be linkable and taggable).

## index.md — directory listings

Optional at any directory level. Purpose: let an agent walk the hierarchy one level at a time
(progressive disclosure) instead of loading an entire bundle into context. In practice this is a
short listing of the concepts and subdirectories at that level, each with a one-line description
pulled from the child's frontmatter. Treat the exact internal layout as convention rather than a
strict wire format — the spec's conformance rules (below) never fail a bundle for a missing
index.md, and a permissive consumer must tolerate one that's stale or absent.

## log.md — change history

Optional, one per bundle (or per directory, if that's more useful for your team). Chronological,
prose entries; a leading bold word (`**Creation**`, `**Update**`, `**Deprecation**`) is a common
convention, not a requirement.

## Conformance (§9) — what a validator actually checks

A conformant OKF v0.1 bundle satisfies exactly these:

1. Every non-reserved `.md` file in the tree contains a parseable YAML frontmatter block.
2. Every frontmatter block contains a non-empty `type` field.
3. Every reserved filename (`index.md`, `log.md`), when present, follows the loose structure above.

And — just as important — consumers **must not** reject a bundle for:
- Missing optional frontmatter fields
- Unknown `type` values
- Unknown additional frontmatter keys
- Broken cross-links
- Missing `index.md` files

This permissive-consumption model is deliberate: bundles grow, get refactored, and get partially
generated by agents over time, so strict validation would break constantly. When in doubt, prefer
producing a bundle that's *useful and readable* over one that's maximally strict — the format only
truly requires `type`.

## Three design principles worth keeping in mind while producing a bundle

1. **Minimally opinionated** — OKF requires exactly one thing (`type`). Everything else — what
   types exist, what other fields to include, what sections a body has — is left to you as producer.
2. **Producer/consumer independence** — a bundle you hand-write can be consumed by an agent; one
   generated by a script can be browsed by a human in a viewer. Don't couple the content to any
   particular consumer's needs.
3. **Format, not platform** — no proprietary account, SDK, or runtime should ever be required to
   read, write, or serve a bundle you produce.

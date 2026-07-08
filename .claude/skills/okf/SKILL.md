---
name: okf
description: Converts an architecture doc, design doc, README, or system-overview markdown file into an Open Knowledge Format (OKF v0.1) knowledge bundle — a directory of small, cross-linked markdown concept files with YAML frontmatter that both humans and AI agents can navigate without any SDK. Use whenever the user has an architecture.md (or similar design/system doc) and wants it turned into OKF, a "knowledge bundle", an "agent-readable wiki", or context agents can consume directly — the pattern behind AGENTS.md/CLAUDE.md files, Obsidian vaults wired to agents, and Google Cloud's OKF announcement. Also trigger on explicit mentions of OKF, Open Knowledge Format, or Knowledge Catalog ingestion, and on requests to decompose a doc into linked concept files, generate index.md/log.md files, or validate a bundle for OKF conformance. Handles concept extraction, directory layout, frontmatter authoring, cross-linking, index/log generation, and conformance validation end to end.
---

# OKF bundle builder

Turn one architecture/design markdown document into a conformant OKF v0.1 knowledge bundle: a
directory of small, focused concept files (YAML frontmatter + markdown body) that link to each
other, organized so an agent can walk the hierarchy instead of loading everything into context at
once. Background on the format, if useful context for the person you're helping: it formalizes the
"LLM-wiki" pattern (Obsidian vaults, AGENTS.md/CLAUDE.md conventions) into something interoperable —
no schema registry, no required tooling, just files. `references/okf-spec.md` has the full spec;
read it whenever you need an exact rule instead of guessing. This file is the workflow.

## Why decompose at all, rather than just copying the doc in

A single architecture.md is written for a person to read start to finish. An agent answering "what
does the `orders` table join to?" shouldn't have to load the whole document to find one paragraph —
and the doc can't easily say "this component was deprecated last month" without a rewrite. Splitting
into one concept per addressable thing, cross-linked and independently timestamped, is what makes
the knowledge both agent-navigable and incrementally updatable. That's the whole point of the
exercise — keep it in mind when you're deciding how finely to split things up.

## Workflow

### 1. Read the source document in full

Find it in `/mnt/user-data/uploads` if it was uploaded, or use the content already in the
conversation. Read the entire thing before splitting anything — you need the whole picture to spot
which entities recur, get referenced from multiple places, or clearly have their own lifecycle,
which is exactly the signal you need for step 2.

### 2. Identify concepts

Walk the document and list every distinct, nameable thing it describes: services, components, data
stores/tables, APIs, models, pipelines, metrics, external dependencies, decisions, runbooks. For
each candidate, ask: **would something else want to link to this, or could it change/be updated on
its own timeline, independent of its neighbors?** If yes, it earns its own concept file. If it's
just a supporting detail — one step in someone else's process, a single config value, a throwaway
aside — it stays as body content inside the concept it belongs to, rather than becoming its own
one-line file.

Getting this granularity right is the main judgment call in this whole skill, more than any
mechanical step. Err toward fewer, more substantial concepts over fragmenting every sentence — a
bundle of fifty near-empty files is harder to navigate than the original document was, not easier.
A useful gut check: could you write a real paragraph or two about this thing on its own, or would
you just be restating its name?

### 3. Choose a directory layout

Group concepts into subdirectories that reflect the domain, usually mirroring the sections already
in the source document (`services/`, `models/`, `data/`, `apis/`, `decisions/`). Directory structure
is not part of the OKF spec itself — it's your call as producer — but it's the first thing a
progressive-disclosure consumer sees, so make it map to how someone would actually think about the
system. Concept filenames become part of the concept's identity (the concept ID is the path with
`.md` removed), so keep them short, lowercase, and hyphen/underscore-separated — they'll appear
literally in every link that points at them.

### 4. Write each concept file

Every concept file needs frontmatter with at least `type` — that's the only field OKF actually
requires. Use this shape:

```yaml
---
type: <short, producer-defined string — Service, Model, Table, API Endpoint, Metric, Decision, ...>
title: <display name>
description: <one plain sentence — this feeds index.md listings and search previews>
resource: <canonical URI, e.g. a repo path or dashboard link, if the source doc names one>
tags: [<short tags for cross-cutting grouping>]
timestamp: <today's date in ISO 8601, unless the source doc gives a more specific one>
---
```

Pick a small, consistent set of `type` values for this bundle and stick to them — two concepts that
are really the same kind of thing (e.g. one tagged `Table` and another `BigQuery Table`) will look
unrelated to a consumer scanning by type. There's no fixed vocabulary to follow; use whatever
taxonomy fits the system being documented.

Below the frontmatter, write the body in your own words, pulling in the substance from the source
document. If the concept's claims trace back to something outside the bundle (a spec, an external
doc, a blog post), add a `# Citations` section at the bottom with a numbered list — see
`references/okf-spec.md` for the exact format.

### 5. Cross-link

Wherever the source document implies a relationship between two things you've split into separate
concepts — calls, depends on, joins with, feeds into, deprecates, is owned by — add a normal
markdown link in the body pointing at the other concept's path (e.g.
``joined with [customers](/tables/customers.md)``). This is what turns a directory of files into a
graph. Don't force links that aren't there in the source material, and don't worry about a link
target that doesn't exist yet — OKF explicitly tolerates broken cross-links, so it's fine to link
forward to a concept you'll fill in on a later pass.

### 6. Generate the index files

Run the bundled script to (re)generate an `index.md` at every directory level — don't hand-write
these, they're purely mechanical listings and the script keeps them consistent as the bundle grows:

```bash
python3 scripts/okf_tools.py index <bundle-path>
```

### 7. Write or update log.md

Add a `log.md` at the bundle root with a short, dated, prose entry describing what just happened —
conventionally starting with a bold word like `**Creation**` for a first pass, or `**Update**` if
you're revising an existing bundle from a changed source document. This is free text, not a script's
job — one or two sentences is plenty.

### 8. Validate

```bash
python3 scripts/okf_tools.py validate <bundle-path> --verbose
```

This checks the two hard requirements from the spec's conformance section (§9): every concept
parses as valid frontmatter, and every concept has a non-empty `type`. It also prints soft warnings
for missing `title`/`description`/`timestamp` — worth a glance, but not something to chase to zero;
OKF is explicit that consumers must not reject a bundle over missing optional fields.

### 9. Deliver the bundle

Copy the finished bundle into `/mnt/user-data/outputs/`, zip it (present_files needs a file, not a
folder — `zip -r <bundle-name>.zip <bundle-name>/` works well), and present the archive. Mention
in passing that it's a plain directory tree they can also unzip straight into a git repo, since that
portability is the actual point of the format.

## Worked example

A fragment of source doc:

> The ingestion service polls Kafka, writes events into the `raw_events` BigQuery table, and a
> nightly job aggregates that into `daily_metrics`, which powers our churn dashboard.

Split into three concepts (`services/ingestion.md`, `tables/raw_events.md`, `tables/daily_metrics.md`),
with `daily_metrics.md` looking roughly like:

```markdown
---
type: BigQuery Table
title: Daily Metrics
description: Nightly aggregation of raw events, used by the churn dashboard.
tags: [metrics, churn]
timestamp: 2026-07-08T00:00:00Z
---

# Daily Metrics

Aggregated nightly from [raw_events](/tables/raw_events.md) by the aggregation job described in
[ingestion](/services/ingestion.md). Powers the churn dashboard.
```

Notice the one-sentence description, the two cross-links back to sibling concepts, and that nothing
here restates information better left in `raw_events.md` or `ingestion.md` — each concept says only
what's actually about itself.

## Reference

- `references/okf-spec.md` — full OKF v0.1 spec details: frontmatter schema, reserved filenames,
  index.md/log.md conventions, and the exact conformance rules. Read this whenever a rule matters
  and you're not sure of it, rather than guessing.
- `scripts/okf_tools.py` — zero-dependency helper with three subcommands: `validate`, `index`, and
  `graph` (prints the cross-link graph as JSON, or `--dot` for Graphviz). Run with `-h` on any
  subcommand for details.

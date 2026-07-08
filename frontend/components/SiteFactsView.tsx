import type { SiteFacts } from "../lib/types";
import { AI_BOTS } from "../lib/types";
import { Bool, Card, Chip, Chips, Meter, Stat } from "./ui";

function truncate(s: string, n = 90): string {
  if (!s) return "—";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function jsTone(ratio: number): "good" | "warn" | "bad" {
  if (ratio <= 0.2) return "good";
  if (ratio <= 0.5) return "warn";
  return "bad";
}

export default function SiteFactsView({ facts }: { facts: SiteFacts }) {
  const f = facts;
  const h1Count = f.html.outline.filter((o) => o.level === 1).length;
  const blockedBots = AI_BOTS.filter((b) => f.robots.allows[b] === false);

  return (
    <div>
      <div className="summary animate-in">
        <span className="u">{f.final_url || f.url}</span>
        <span className="m">HTTP {f.http.status || "—"}</span>
        <span className="m">{f.http.content_type?.split(";")[0] || "—"}</span>
        <span className="m">{f.http.latency_ms} ms</span>
      </div>

      <div className="grid">
        <Card
          title="AI crawler access"
          hint={
            blockedBots.length
              ? `${blockedBots.length} AI bot(s) blocked by robots.txt`
              : "All tracked AI bots allowed"
          }
        >
          <Chips>
            {AI_BOTS.map((bot) => (
              <Chip key={bot} tone={f.robots.allows[bot] === false ? "bad" : "good"}>
                {bot}
              </Chip>
            ))}
          </Chips>
        </Card>

        <Card
          title="JavaScript dependency"
          hint="Share of content injected by JS — invisible to AI crawlers that don't run it"
        >
          <Meter
            value={f.render.js_dependency_ratio}
            tone={jsTone(f.render.js_dependency_ratio)}
            caption="JS-gated content"
          />
          <div style={{ marginTop: 12 }}>
            <Stat
              k="Content visible without JS"
              v={<Bool value={f.render.content_visible_without_js} />}
            />
            <Stat k="Rendered / raw text" v={`${f.render.rendered_text_len} / ${f.render.raw_text_len}`} />
          </div>
        </Card>

        <Card title="Structured data" hint="schema.org markup an answer engine can parse">
          <div style={{ marginBottom: 10 }}>
            <Stat k="Valid JSON-LD" v={<Bool value={f.structured_data.jsonld_valid} />} />
          </div>
          {f.structured_data.schema_types.length ? (
            <Chips>
              {f.structured_data.schema_types.map((t) => (
                <Chip key={t}>{t}</Chip>
              ))}
            </Chips>
          ) : (
            <span className="m" style={{ color: "var(--muted)" }}>No schema types found</span>
          )}
        </Card>

        <Card title="Content &amp; meta">
          <Stat k="Title" v={<span title={f.html.title}>{truncate(f.html.title, 60)}</span>} />
          <Stat
            k="Meta description"
            v={<span title={f.html.meta_description}>{truncate(f.html.meta_description, 60)}</span>}
          />
          <Stat k="Canonical" v={<Bool value={!!f.html.canonical} yes="set" no="none" />} />
          <Stat k="Language" v={f.html.lang || "—"} />
          <Stat k="Word count" v={f.html.word_count} />
          <Stat k="Headings" v={`${f.html.outline.length} (${h1Count}× H1)`} />
          <Stat
            k="Social tags"
            v={
              <Chips>
                <Chip tone={Object.keys(f.html.og).length ? "good" : "bad"}>OG</Chip>
                <Chip tone={Object.keys(f.html.twitter).length ? "good" : "bad"}>Twitter</Chip>
              </Chips>
            }
          />
        </Card>

        <Card title="Links">
          <Stat k="Internal" v={f.links.internal} />
          <Stat k="External" v={f.links.external} />
          <Stat k="Outbound citations" v={f.links.outbound_citations} />
        </Card>

        <Card title="Authorship &amp; freshness" hint="E-E-A-T signals answer engines favour">
          <Stat k="Byline present" v={<Bool value={f.authorship.byline_present} />} />
          <Stat k="Author schema" v={<Bool value={f.authorship.author_schema} />} />
          <Stat k="Published" v={f.authorship.dates.published || "—"} />
          <Stat k="Modified" v={f.authorship.dates.modified || "—"} />
        </Card>

        <Card title="Sitemap &amp; llms.txt">
          <Stat k="Sitemap" v={<Bool value={f.sitemap.exists && f.sitemap.valid} yes="valid" no="missing" />} />
          <Stat k="Sitemap URLs" v={f.sitemap.url_count} />
          <Stat k="llms.txt" v={<Bool value={f.llms_txt.exists} yes="present" no="none" />} />
          <Stat k="llms.txt summary" v={<Bool value={f.llms_txt.has_summary} />} />
          <Stat k="llms.txt links" v={f.llms_txt.link_count} />
        </Card>

        <Card title="Entities" hint="Candidate topic entities on the page">
          {f.entities_raw.length ? (
            <Chips>
              {f.entities_raw.map((e, i) => (
                <Chip key={`${e.text}-${i}`}>{e.text}</Chip>
              ))}
            </Chips>
          ) : (
            <span className="m" style={{ color: "var(--muted)" }}>No entities detected</span>
          )}
        </Card>
      </div>
    </div>
  );
}

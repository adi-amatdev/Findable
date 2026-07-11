import type { SiteFacts } from "../lib/types";
import { AI_BOTS } from "../lib/types";

// One dense line of ground truth - the deterministic SiteFacts, compressed.

export default function FactsStrip({ facts }: { facts: SiteFacts }) {
  const blocked = AI_BOTS.filter((b) => facts.robots.allows[b] === false);
  const js = Math.round(facts.render.js_dependency_ratio * 100);

  const items: Array<[string, string, "good" | "bad" | "plain"]> = [
    ["HTTP", facts.http.status ? `${facts.http.status}${facts.http.latency_ms ? ` · ${facts.http.latency_ms}ms` : ""}` : "-", facts.http.status === 200 ? "good" : "bad"],
    ["robots.txt", facts.robots.exists ? "present" : "missing", facts.robots.exists ? "good" : "bad"],
    ["AI bots", blocked.length ? `${blocked.length} blocked` : "all allowed", blocked.length ? "bad" : "good"],
    ["JS gap", `${js}%`, js > 50 ? "bad" : "good"],
    ["Schema", facts.structured_data.schema_types.length ? facts.structured_data.schema_types.slice(0, 3).join(", ") : "none", facts.structured_data.schema_types.length ? "good" : "bad"],
    ["Words", String(facts.html.word_count), "plain"],
    ["Sitemap", facts.sitemap.exists ? `${facts.sitemap.url_count} URLs` : "missing", facts.sitemap.exists ? "good" : "bad"],
    ["llms.txt", facts.llms_txt.exists ? "present" : "missing", facts.llms_txt.exists ? "good" : "bad"],
  ];

  return (
    <div className="facts-strip">
      <span className="facts-url">
        <span className="fk">Audited URL</span>
        <span className="facts-url-value" title={facts.final_url || facts.url}>{facts.final_url || facts.url}</span>
      </span>
      {items.map(([k, v, tone]) => (
        <span key={k} className={`fact ${tone}`}>
          <span className="fk">{k}</span>
          <span className="fact-value" title={v}>{v}</span>
        </span>
      ))}
    </div>
  );
}

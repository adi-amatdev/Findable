"use client";

import { FormEvent, useState } from "react";
import SiteFactsView from "../components/SiteFactsView";
import { API_BASE, getSiteFacts } from "../lib/api";
import type { SiteFacts } from "../lib/types";

export default function Home() {
  const [url, setUrl] = useState("");
  const [refresh, setRefresh] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facts, setFacts] = useState<SiteFacts | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = url.trim();
    if (!value || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getSiteFacts(value, refresh);
      setFacts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setFacts(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <div className="hero">
        <h1>Findable</h1>
        <p>See exactly how AI crawlers read a page. Enter a URL — get its SiteFacts.</p>

        <form className="form" onSubmit={onSubmit}>
          <input
            className="input"
            type="url"
            inputMode="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Auditing…" : "Audit"}
          </button>
        </form>
        <label className="form-row checkbox">
          <input
            type="checkbox"
            checked={refresh}
            onChange={(e) => setRefresh(e.target.checked)}
          />
          Bypass cache (re-crawl)
        </label>
      </div>

      {loading && (
        <div className="notice">
          <span className="spinner" /> &nbsp; Crawling and extracting SiteFacts…
        </div>
      )}

      {error && !loading && (
        <div className="notice error">
          <strong>Couldn&apos;t audit that URL.</strong>
          <div style={{ marginTop: 4 }}>{error}</div>
        </div>
      )}

      {facts && !loading && <SiteFactsView facts={facts} />}

      <div className="footer">
        Backend: <span className="mono">{API_BASE}</span> ·{" "}
        <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
          API docs
        </a>
      </div>
    </main>
  );
}

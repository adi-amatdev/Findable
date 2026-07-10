// The four judges - ids match the agents-api (okf/agents/).

export interface AgentMeta {
  id: string;
  name: string;
  role: string; // one-line story of what this judge reads
  weight: string;
}

export const AGENTS: AgentMeta[] = [
  {
    id: "crawlability",
    name: "Crawlability",
    role: "Can AI bots even reach the page? robots.txt, sitemaps, JS-gated content.",
    weight: "30%",
  },
  {
    id: "content_signal",
    name: "Content Signal",
    role: "Is it worth citing? Experience, expertise, authority, trust.",
    weight: "35%",
  },
  {
    id: "structured_data",
    name: "Structured Data",
    role: "Can a machine extract the facts? schema.org, llms.txt, meta.",
    weight: "15%",
  },
  {
    id: "entity_topic",
    name: "Entity & Topic",
    role: "Does the page know what it's about? Entities, disambiguation, links.",
    weight: "20%",
  },
];

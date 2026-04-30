export interface AgentToolsClientOptions {
  baseUrl: string;
  token: string;
}

export class AgentToolsClient {
  private baseUrl: string;
  private token: string;

  constructor(opts: AgentToolsClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.token = opts.token;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        ...(init.headers ?? {}),
        authorization: `Bearer ${this.token}`,
        "content-type": "application/json",
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`SciVerse API ${res.status}: ${body}`);
    }
    return (await res.json()) as T;
  }

  async searchPapers(body: Record<string, unknown>): Promise<unknown> {
    const cleaned = Object.fromEntries(Object.entries(body).filter(([, v]) => v !== undefined));
    return this.request("/meta-search", { method: "POST", body: JSON.stringify(cleaned) });
  }

  async semanticSearch(body: { query: string } & Record<string, unknown>): Promise<unknown> {
    const cleaned = Object.fromEntries(Object.entries(body).filter(([, v]) => v !== undefined));
    return this.request("/agentic-search", { method: "POST", body: JSON.stringify(cleaned) });
  }

  async readContent(params: { doc_id: string; offset?: number; limit?: number }): Promise<unknown> {
    const qs = new URLSearchParams();
    qs.set("doc_id", params.doc_id);
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    return this.request(`/content?${qs.toString()}`, { method: "GET" });
  }
}

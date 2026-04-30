/**
 * 端到端示例：TypeScript + LangChain + SciVerse。
 *
 * 把 SciVerse client 包装成 DynamicStructuredTool 给 LangGraph / Agent 使用。
 *
 * 运行：
 *   npm install @langchain/openai @langchain/core zod sciverse-agent-tools tsx
 *   SCIVERSE_API_TOKEN=... OPENAI_API_KEY=... npx tsx examples/ts_langchain_agent.ts
 */
import { ChatOpenAI } from "@langchain/openai";
import { DynamicStructuredTool } from "@langchain/core/tools";
import { z } from "zod";
import { AgentToolsClient } from "sciverse-agent-tools";

const sv = new AgentToolsClient({
  baseUrl: process.env.SCIVERSE_BASE_URL ?? "https://sciverse.space/api",
  token: process.env.SCIVERSE_API_TOKEN!,
});

const tools = [
  new DynamicStructuredTool({
    name: "semantic_search",
    description: "自然语言语义检索 SciVerse 文献片段。",
    schema: z.object({
      query: z.string(),
      top_k: z.number().int().min(1).max(30).optional(),
      mode: z.enum(["fast", "balanced", "quality"]).optional(),
    }),
    func: async (args) => JSON.stringify(await sv.semanticSearch(args)).slice(0, 8000),
  }),
  new DynamicStructuredTool({
    name: "read_content",
    description: "按字节区间读取文献原文片段。",
    schema: z.object({
      doc_id: z.string(),
      offset: z.number().int().optional(),
      limit: z.number().int().optional(),
    }),
    func: async (args) => JSON.stringify(await sv.readContent(args)),
  }),
];

const llm = new ChatOpenAI({ model: "gpt-4o" }).bindTools(tools);

async function main(question: string) {
  const resp = await llm.invoke([{ role: "user", content: question }]);
  console.log(resp.content);
}

main("Transformer 注意力机制是怎么工作的？").catch(console.error);

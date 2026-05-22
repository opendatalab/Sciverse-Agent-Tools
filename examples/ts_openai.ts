/**
 * 端到端示例：TypeScript + OpenAI function calling + Sciverse 五个 tool。
 *
 * `OPENAI_TOOLS` 包含全部 5 个 schema；dispatch 表必须全覆盖，否则模型
 * 调到没接的 tool 时返回 undefined。
 *
 * 运行：
 *   npm install openai sciverse tsx
 *   SCIVERSE_API_TOKEN=... OPENAI_API_KEY=... npx tsx examples/ts_openai.ts
 */
import OpenAI from "openai";
import { AgentToolsClient, OPENAI_TOOLS } from "sciverse";

const sv = new AgentToolsClient({
  baseUrl: process.env.SCIVERSE_BASE_URL ?? "https://api.sciverse.space",
  token: process.env.SCIVERSE_API_TOKEN!,
});
const openai = new OpenAI();

const dispatch: Record<string, (args: any) => Promise<any>> = {
  list_catalog: (a) => sv.listCatalog(a),
  search_papers: (a) => sv.searchPapers(a),
  semantic_search: (a) => sv.semanticSearch(a),
  read_content: (a) => sv.readContent(a),
  get_resource: async (a) => {
    const { bytes, mimeType } = await sv.getResource(a);
    return { data: Buffer.from(bytes).toString("base64"), mime_type: mimeType };
  },
};

async function main(question: string) {
  const messages: any[] = [{ role: "user", content: question }];
  for (let i = 0; i < 5; i++) {
    const resp = await openai.chat.completions.create({
      model: "gpt-4o",
      tools: OPENAI_TOOLS as any,
      messages,
    });
    const msg = resp.choices[0].message;
    messages.push(msg);
    if (!msg.tool_calls?.length) {
      console.log("\n=== 回答 ===\n", msg.content);
      return;
    }
    for (const call of msg.tool_calls) {
      const args = JSON.parse(call.function.arguments);
      const out = await dispatch[call.function.name](args);
      messages.push({
        role: "tool",
        tool_call_id: call.id,
        content: JSON.stringify(out).slice(0, 8000),
      });
    }
  }
}

main("最近三年关于蛋白质结构预测有哪些重要论文？").catch(console.error);

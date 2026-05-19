// Token / endpoint 解析顺序：env → ~/.sciverse/credentials.json → 默认值。
// BASE_URL 仅允许 *.sciverse.space 与 sciverse.space，防止 token 被泄漏到
// 任意域名（与 ClawHub skill 的 _common.mjs 一致）。
import { resolveEndpoint, resolveToken } from "./credentials.js";

export interface Config {
  token: string;
  baseUrl: string;
}

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const token = resolveToken(undefined, env);
  if (!token) {
    throw new ConfigError(
      "未找到 Sciverse API Token。请设 SCIVERSE_API_TOKEN 环境变量，或运行 " +
        "`pip install sciverse && sciverse auth login` 保存凭据到 ~/.sciverse/credentials.json。",
    );
  }
  const baseUrl = resolveEndpoint(undefined, env).replace(/\/$/, "");
  let parsed: URL;
  try {
    parsed = new URL(baseUrl);
  } catch {
    throw new ConfigError(`SCIVERSE_BASE_URL is not a valid URL: ${baseUrl}`);
  }
  const host = parsed.hostname;
  if (host !== "sciverse.space" && !host.endsWith(".sciverse.space")) {
    throw new ConfigError(
      `SCIVERSE_BASE_URL must point to a *.sciverse.space domain (got: ${host}). This guards against accidental token leakage.`,
    );
  }
  return { token, baseUrl };
}

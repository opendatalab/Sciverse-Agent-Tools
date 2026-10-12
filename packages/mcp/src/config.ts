// Token / endpoint 解析顺序：env → ~/.sciverse/credentials.json → 默认值。
// BASE_URL 仅允许 *.sciverse.space 与 sciverse.space，防止 token 被泄漏到
// 任意域名（与 ClawHub skill 的 _common.mjs 一致）。
import { resolveEndpoint, resolveToken, DEFAULT_ENDPOINT } from "./credentials.js";

export interface Config {
  token: string;
  baseUrl: string;
  /**
   * 调用方标识，拼入下游 X-Sciverse-Source 头部（`{platform}-{channel}`），
   * 用于 SLS 日志归因；X-Request-Id 仅承载 uuid。默认 "mcp"（stdio 入口）；
   * cli-http.ts 启动时覆盖为 "scp"，也可由环境变量 SCIVERSE_MCP_CHANNEL 显式指定。
   */
  channel: string;
}

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

const DEFAULT_CHANNEL = "mcp";

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
  const channel = env.SCIVERSE_MCP_CHANNEL?.trim() || DEFAULT_CHANNEL;
  return { token, baseUrl, channel };
}

// HTTP 服务禁止隐式读取运维用户的个人凭据；Bearer 直连和 Hub 通道无需固定 token。
export function loadHttpConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const config = loadConfig({ ...env, SCIVERSE_API_TOKEN: env.SCIVERSE_API_TOKEN?.trim() || "http-no-fixed-token",
    SCIVERSE_BASE_URL: env.SCIVERSE_BASE_URL || DEFAULT_ENDPOINT });
  const url = new URL(config.baseUrl);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new ConfigError("HTTP 服务的 API 地址必须是无路径、无凭据的 HTTPS 地址");
  }
  return { ...config, token: env.SCIVERSE_API_TOKEN?.trim() || "" };
}

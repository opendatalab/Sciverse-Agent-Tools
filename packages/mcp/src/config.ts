// 读取环境变量并校验。BASE_URL 仅允许 *.sciverse.space 与 sciverse.space，
// 防止 token 被泄漏到任意域名（与 ClawHub skill 的 _common.mjs 一致）。

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

const DEFAULT_BASE_URL = "https://api.sciverse.space";

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const token = env.SCIVERSE_API_TOKEN;
  if (!token) {
    throw new ConfigError(
      "SCIVERSE_API_TOKEN is not set. Obtain a Bearer token from https://sciverse.space and export it.",
    );
  }
  const baseUrl = (env.SCIVERSE_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/$/, "");
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

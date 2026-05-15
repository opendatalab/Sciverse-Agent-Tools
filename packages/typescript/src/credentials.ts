// 共享凭据文件读取（与 packages/mcp/src/credentials.ts + Python
// sciverse.credentials 同源契约）。
//
// 文件 `~/.sciverse/credentials.json` 由 Python CLI `sciverse auth login` 写入；
// 这里只读不写，让"装一次 Python CLI 后所有客户端形态都免传 token"链路成立。
import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export interface StoredCredentials {
  token?: string;
  endpoint?: string;
  saved_at?: string;
}

export const DEFAULT_ENDPOINT = "https://api.sciverse.space";

/** 返回用户 home 目录。优先读环境变量 HOME/USERPROFILE 以便测试 override，
 *  否则 fallback 到 os.homedir()（Node 内置）。 */
function getHomeDir(): string {
  return process.env.HOME ?? process.env.USERPROFILE ?? homedir();
}

export function credentialsPath(): string {
  return join(getHomeDir(), ".sciverse", "credentials.json");
}

export function loadStoredCredentials(): StoredCredentials | null {
  const path = credentialsPath();
  if (!existsSync(path)) return null;
  try {
    const raw = readFileSync(path, "utf8");
    const data = JSON.parse(raw);
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return data as StoredCredentials;
    }
    return null;
  } catch {
    return null;
  }
}

export function resolveToken(
  explicit?: string,
  env: NodeJS.ProcessEnv = process.env,
): string | null {
  if (explicit) return explicit;
  if (env.SCIVERSE_API_TOKEN) return env.SCIVERSE_API_TOKEN;
  const creds = loadStoredCredentials();
  if (creds?.token) return creds.token;
  return null;
}

export function resolveEndpoint(
  explicit?: string,
  env: NodeJS.ProcessEnv = process.env,
): string {
  if (explicit) return explicit;
  if (env.SCIVERSE_BASE_URL) return env.SCIVERSE_BASE_URL;
  const creds = loadStoredCredentials();
  if (creds?.endpoint) return creds.endpoint;
  return DEFAULT_ENDPOINT;
}

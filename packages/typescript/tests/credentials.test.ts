// 凭据 fallback + AgentToolsClient 构造逻辑测试。
//
// 测试隔离：用 HOMEDIR + os.homedir 重定向到 tmp 目录，避免污染真实
// 用户凭据文件；同时 vi.stubEnv 清掉 SCIVERSE_* 环境变量。
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { AgentToolsClient } from "../src/client";
import { credentialsPath, resolveEndpoint, resolveToken } from "../src/credentials";

let tmpHome: string;

beforeEach(() => {
  tmpHome = join(tmpdir(), `sciverse-test-${Date.now()}-${Math.random()}`);
  mkdirSync(tmpHome, { recursive: true });
  // Node os.homedir() 在 POSIX 下优先读 $HOME，Windows 下读 %USERPROFILE%
  vi.stubEnv("HOME", tmpHome);
  vi.stubEnv("USERPROFILE", tmpHome);
  vi.stubEnv("SCIVERSE_API_TOKEN", "");
  vi.stubEnv("SCIVERSE_BASE_URL", "");
});

afterEach(() => {
  if (existsSync(tmpHome)) rmSync(tmpHome, { recursive: true, force: true });
  vi.unstubAllEnvs();
});

function writeCreds(token: string, endpoint?: string) {
  const dir = join(tmpHome, ".sciverse");
  mkdirSync(dir, { recursive: true });
  writeFileSync(
    join(dir, "credentials.json"),
    JSON.stringify({ token, ...(endpoint ? { endpoint } : {}) }),
  );
}

describe("resolveToken", () => {
  it("returns explicit when given", () => {
    vi.stubEnv("SCIVERSE_API_TOKEN", "sv-env");
    writeCreds("sv-file");
    expect(resolveToken("sv-explicit")).toBe("sv-explicit");
  });

  it("env beats file", () => {
    vi.stubEnv("SCIVERSE_API_TOKEN", "sv-env");
    writeCreds("sv-file");
    expect(resolveToken()).toBe("sv-env");
  });

  it("falls back to file when no env", () => {
    writeCreds("sv-file");
    expect(resolveToken()).toBe("sv-file");
  });

  it("returns null when no source", () => {
    expect(resolveToken()).toBeNull();
  });
});

describe("resolveEndpoint", () => {
  it("returns default when no source", () => {
    expect(resolveEndpoint()).toBe("https://api.sciverse.space");
  });

  it("env beats file", () => {
    vi.stubEnv("SCIVERSE_BASE_URL", "https://api.sciverse.space");
    writeCreds("sv-x", "https://api-dev.sciverse.space");
    expect(resolveEndpoint()).toBe("https://api.sciverse.space");
  });

  it("falls back to file when no env", () => {
    writeCreds("sv-x", "https://api-dev.sciverse.space");
    expect(resolveEndpoint()).toBe("https://api-dev.sciverse.space");
  });
});

describe("credentialsPath", () => {
  it("points to ~/.sciverse/credentials.json", () => {
    expect(credentialsPath()).toBe(join(tmpHome, ".sciverse", "credentials.json"));
  });
});

describe("AgentToolsClient fallback", () => {
  it("uses credentials file when token not passed", () => {
    writeCreds("sv-from-file", "https://api.sciverse.space");
    // 不传 token / baseUrl，应该 fallback 成功
    const c = new AgentToolsClient();
    // 私有字段通过 any 访问做测试断言
    expect((c as any).token).toBe("sv-from-file");
    expect((c as any).baseUrl).toBe("https://api.sciverse.space");
  });

  it("throws when no token anywhere", () => {
    expect(() => new AgentToolsClient()).toThrow(/未找到 Sciverse API Token/);
  });

  it("explicit token still works after fallback added", () => {
    const c = new AgentToolsClient({ baseUrl: "https://api.sciverse.space", token: "sv-explicit" });
    expect((c as any).token).toBe("sv-explicit");
  });
});

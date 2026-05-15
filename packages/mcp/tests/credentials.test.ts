// 凭据 fallback + loadConfig 测试，跟 TS SDK 测试同结构。
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { loadConfig, ConfigError } from "../src/config";
import { credentialsPath, resolveToken, resolveEndpoint } from "../src/credentials";

let tmpHome: string;

beforeEach(() => {
  tmpHome = join(tmpdir(), `sciverse-mcp-test-${Date.now()}-${Math.random()}`);
  mkdirSync(tmpHome, { recursive: true });
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

describe("MCP credentials fallback", () => {
  it("resolveToken: env beats file", () => {
    vi.stubEnv("SCIVERSE_API_TOKEN", "sv-env");
    writeCreds("sv-file");
    expect(resolveToken()).toBe("sv-env");
  });

  it("resolveToken: file used when no env", () => {
    writeCreds("sv-file");
    expect(resolveToken()).toBe("sv-file");
  });

  it("resolveToken: returns null when no source", () => {
    expect(resolveToken()).toBeNull();
  });

  it("resolveEndpoint: default when no source", () => {
    expect(resolveEndpoint()).toBe("https://api.sciverse.space");
  });

  it("resolveEndpoint: file used when no env", () => {
    writeCreds("sv-x", "https://api-dev.sciverse.space");
    expect(resolveEndpoint()).toBe("https://api-dev.sciverse.space");
  });

  it("credentialsPath: under HOME/.sciverse/", () => {
    expect(credentialsPath()).toBe(join(tmpHome, ".sciverse", "credentials.json"));
  });
});

describe("loadConfig with fallback", () => {
  it("uses credentials file when env not set", () => {
    writeCreds("sv-from-file", "https://api.sciverse.space");
    // 注意：loadConfig 不接受 env 参数 override HOME，只接受 process.env 全局
    // 这里 vi.stubEnv 已设好，直接传 process.env
    const cfg = loadConfig(process.env);
    expect(cfg.token).toBe("sv-from-file");
    expect(cfg.baseUrl).toBe("https://api.sciverse.space");
  });

  it("throws ConfigError with helpful message when no token anywhere", () => {
    expect(() => loadConfig(process.env)).toThrow(/未找到 SciVerse API Token/);
  });

  it("env-passed token wins over file", () => {
    writeCreds("sv-from-file");
    vi.stubEnv("SCIVERSE_API_TOKEN", "sv-from-env");
    const cfg = loadConfig(process.env);
    expect(cfg.token).toBe("sv-from-env");
  });

  it("rejects non *.sciverse.space endpoint from file", () => {
    writeCreds("sv-x", "https://evil.example.com");
    expect(() => loadConfig(process.env)).toThrow(/sciverse\.space/);
  });
});

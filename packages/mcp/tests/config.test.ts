import { describe, expect, it } from "vitest";
import { ConfigError, loadConfig } from "../src/config.js";

describe("loadConfig", () => {
  it("returns token + default baseUrl when only token is set", () => {
    const cfg = loadConfig({ SCIVERSE_API_TOKEN: "sv-test" } as NodeJS.ProcessEnv);
    expect(cfg.token).toBe("sv-test");
    expect(cfg.baseUrl).toBe("https://api.sciverse.space");
  });

  it("throws when token is missing", () => {
    expect(() => loadConfig({} as NodeJS.ProcessEnv)).toThrow(ConfigError);
  });

  it("accepts api.sciverse.space and sciverse.space", () => {
    expect(
      loadConfig({
        SCIVERSE_API_TOKEN: "sv-x",
        SCIVERSE_BASE_URL: "https://api.sciverse.space",
      } as NodeJS.ProcessEnv).baseUrl,
    ).toBe("https://api.sciverse.space");
    expect(
      loadConfig({
        SCIVERSE_API_TOKEN: "sv-x",
        SCIVERSE_BASE_URL: "https://sciverse.space/api",
      } as NodeJS.ProcessEnv).baseUrl,
    ).toBe("https://sciverse.space/api");
  });

  it("rejects non-sciverse.space domain (anti-leak guard)", () => {
    expect(() =>
      loadConfig({
        SCIVERSE_API_TOKEN: "sv-x",
        SCIVERSE_BASE_URL: "https://evil.example.com",
      } as NodeJS.ProcessEnv),
    ).toThrow(/sciverse\.space/);
  });

  it("rejects malformed url", () => {
    expect(() =>
      loadConfig({
        SCIVERSE_API_TOKEN: "sv-x",
        SCIVERSE_BASE_URL: "not-a-url",
      } as NodeJS.ProcessEnv),
    ).toThrow(ConfigError);
  });

  it("strips trailing slash from baseUrl", () => {
    const cfg = loadConfig({
      SCIVERSE_API_TOKEN: "sv-x",
      SCIVERSE_BASE_URL: "https://api.sciverse.space/",
    } as NodeJS.ProcessEnv);
    expect(cfg.baseUrl).toBe("https://api.sciverse.space");
  });

  it("defaults channel to 'mcp' when SCIVERSE_MCP_CHANNEL unset", () => {
    const cfg = loadConfig({ SCIVERSE_API_TOKEN: "sv-x" } as NodeJS.ProcessEnv);
    expect(cfg.channel).toBe("mcp");
  });

  it("reads channel from SCIVERSE_MCP_CHANNEL env", () => {
    const cfg = loadConfig({
      SCIVERSE_API_TOKEN: "sv-x",
      SCIVERSE_MCP_CHANNEL: "scp",
    } as NodeJS.ProcessEnv);
    expect(cfg.channel).toBe("scp");
  });

  it("falls back to default when channel env is whitespace only", () => {
    const cfg = loadConfig({
      SCIVERSE_API_TOKEN: "sv-x",
      SCIVERSE_MCP_CHANNEL: "   ",
    } as NodeJS.ProcessEnv);
    expect(cfg.channel).toBe("mcp");
  });
});

// 双通道鉴权判定器（sciverse-console: docs/plans/2026-05-19-scp-mcp-http-transport.md §8.2）：
//   direct 通道：Authorization: Bearer <token> → 原样透传下游，channel = "remote"
//   hub 通道：来源 IP ∈ SCP_HUB_IPS（信任跳 XFF 判定）→ 使用部署内置 token 代调
//   两者皆无 → 调用方返回 401
//
// Authorization 优先于 IP：自带 token 是比来源 IP 更明确的身份声明，且计费归属
// 到调用方自己；Hub 将来若支持配转发 header，可无缝升级为自带 token。
// 判定器刻意独立成模块：替换 hub 分支即可切换判定策略，透传通道不动。
import type { IncomingMessage } from "node:http";

import type { Config } from "./config.js";

export type Lane = "hub" | "direct";

export interface LaneDecision {
  lane: Lane;
  token: string;
  channel: string;
}

export interface AuthOptions {
  /** SCP Hub 出口 IP（精确匹配，已归一化）。空集 = hub 通道关闭。 */
  hubIps: Set<string>;
  /** 本进程前的信任代理跳数：0 = 直连取 socket 地址；N ≥ 1 = 取 XFF 右起第 N 个。 */
  trustedHops: number;
}

const DIRECT_CHANNEL = "remote";
const DEFAULT_TRUSTED_HOPS = 1;

/** 统一小写；去掉 IPv4-mapped IPv6 前缀与 /32 后缀。 */
function normalizeIp(raw: string): string {
  let ip = raw.trim().toLowerCase();
  if (ip.startsWith("::ffff:")) ip = ip.slice("::ffff:".length);
  if (ip.endsWith("/32")) ip = ip.slice(0, -"/32".length);
  return ip;
}

export function loadAuthOptions(env: NodeJS.ProcessEnv = process.env): AuthOptions {
  const hubIps = new Set(
    (env.SCP_HUB_IPS ?? "")
      .split(/[\s,]+/)
      .map(normalizeIp)
      .filter((s) => s.length > 0),
  );
  const hopsRaw = env.TRUSTED_PROXY_HOPS?.trim();
  const parsed = hopsRaw ? Number.parseInt(hopsRaw, 10) : DEFAULT_TRUSTED_HOPS;
  const trustedHops = Number.isFinite(parsed) && parsed >= 0 ? parsed : DEFAULT_TRUSTED_HOPS;
  return { hubIps, trustedHops };
}

/**
 * 取真实客户端 IP。XFF 形如 "client, proxy1, proxy2"：右侧 trustedHops 个条目
 * 是我方信任设施（MSE 网关等）逐跳追加的，右起第 trustedHops 个即最后一个
 * 可信来源地址；更左的条目均为客户端可伪造前缀，绝不采信。
 */
export function clientIp(req: IncomingMessage, trustedHops: number): string | null {
  if (trustedHops <= 0) {
    const addr = req.socket.remoteAddress;
    return addr ? normalizeIp(addr) : null;
  }
  const header = req.headers["x-forwarded-for"];
  const joined = Array.isArray(header) ? header.join(",") : (header ?? "");
  const entries = joined
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  // 信任链不完整（XFF 条目数少于应有的信任跳数）：判 null，走 401。
  if (entries.length < trustedHops) return null;
  return normalizeIp(entries[entries.length - trustedHops]);
}

/** 判定请求走哪条通道；null = 无法鉴权（调用方应返回 401）。 */
export function resolveLane(
  req: IncomingMessage,
  config: Config,
  opts: AuthOptions,
): LaneDecision | null {
  const m = req.headers.authorization?.match(/^Bearer\s+(.+)$/i);
  if (m) {
    return { lane: "direct", token: m[1].trim(), channel: DIRECT_CHANNEL };
  }
  const ip = clientIp(req, opts.trustedHops);
  if (ip && opts.hubIps.has(ip)) {
    return { lane: "hub", token: config.token, channel: config.channel };
  }
  return null;
}

// HTTP 入口鉴权判定器（通用机制，不含部署方专有概念；SciVerse 托管部署的
// 具体取值见 sciverse-console: docs/plans/2026-05-19-scp-mcp-http-transport.md §8）：
//   direct 通道：Authorization: Bearer <token> → 原样透传下游，channel = "remote"
//   trusted 通道：来源 IP ∈ SCIVERSE_MCP_TRUSTED_IPS → 使用进程内置 token 代调
//   两者皆无 → 调用方返回 401
//
// Authorization 优先于 IP：自带 token 是比来源 IP 更明确的身份声明，且计费归属
// 到调用方自己；可信通道的调用方将来若能自带 token，可无缝迁移，判定器不动。
//
// 来源 IP 的取得遵循「先验对端，再信转发头」：仅当 TCP 对端 ∈
// SCIVERSE_MCP_TRUSTED_PROXIES（CIDR 列表）时才解析 X-Forwarded-For（取右起第
// SCIVERSE_MCP_TRUSTED_PROXY_HOPS 个条目——右侧条目由信任设施逐跳追加，更左的
// 均为客户端可伪造前缀）。默认不信任任何代理：不显式声明代理网段，转发头
// 永不采信，绕过网关直连（如集群内工作负载）伪造 XFF 只会以自身地址参与判定。
import type { IncomingMessage } from "node:http";

import type { Config } from "./config.js";

export type Lane = "trusted" | "direct";

export interface LaneDecision {
  lane: Lane;
  token: string;
  channel: string;
}

/** 信任代理集合：IPv4 支持 CIDR；其余条目（IPv6 等）精确匹配。 */
export interface TrustedProxies {
  v4: { base: number; bits: number }[];
  exact: Set<string>;
}

export interface AuthOptions {
  /** 可信来源 IP（精确匹配，已归一化）。空集 = trusted 通道关闭。 */
  trustedIps: Set<string>;
  /** 信任代理网段：TCP 对端命中才解析 XFF。空 = 转发头永不采信。 */
  trustedProxies: TrustedProxies;
  /** 解析 XFF 时取右起第几个条目（≥1）；需与代理真实跳数一致。 */
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

function ipv4ToInt(ip: string): number | null {
  const parts = ip.split(".");
  if (parts.length !== 4) return null;
  let v = 0;
  for (const p of parts) {
    if (!/^\d{1,3}$/.test(p)) return null;
    const n = Number(p);
    if (n > 255) return null;
    v = ((v << 8) | n) >>> 0;
  }
  return v;
}

/** 解析逗号/空白分隔的代理列表；IPv4 条目可带 /bits，非法 bits 的条目降级为精确匹配。 */
export function parseTrustedProxies(raw: string | undefined): TrustedProxies {
  const out: TrustedProxies = { v4: [], exact: new Set() };
  for (const entry of (raw ?? "").split(/[\s,]+/)) {
    if (!entry.trim()) continue;
    const [ipPart, bitsPart] = entry.trim().toLowerCase().split("/");
    const ip = normalizeIp(ipPart);
    const asV4 = ipv4ToInt(ip);
    if (asV4 !== null) {
      const bits = bitsPart === undefined ? 32 : Number.parseInt(bitsPart, 10);
      if (Number.isFinite(bits) && bits >= 0 && bits <= 32) {
        out.v4.push({ base: asV4, bits });
        continue;
      }
    }
    out.exact.add(ip);
  }
  return out;
}

function isTrustedProxy(ip: string, proxies: TrustedProxies): boolean {
  if (proxies.exact.has(ip)) return true;
  const v4 = ipv4ToInt(ip);
  if (v4 === null) return false;
  // bits=0（0.0.0.0/0）需特判：JS 位移量按 mod 32 取，>>> 32 等价 >>> 0。
  return proxies.v4.some(({ base, bits }) => (bits === 0 ? true : ((v4 ^ base) >>> (32 - bits)) === 0));
}

/** 取参与鉴权判定的来源 IP；null = 信任链不完整（调用方应 401，fail-closed）。 */
export function clientIp(req: IncomingMessage, opts: AuthOptions): string | null {
  const peer = req.socket.remoteAddress ? normalizeIp(req.socket.remoteAddress) : null;
  if (!peer) return null;
  // 对端不是信任代理：XFF 一律不采信，直接用 socket 地址。
  if (!isTrustedProxy(peer, opts.trustedProxies)) return peer;
  const hops = Math.max(1, Math.floor(opts.trustedHops));
  const header = req.headers["x-forwarded-for"];
  const joined = Array.isArray(header) ? header.join(",") : (header ?? "");
  const entries = joined
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (entries.length < hops) return null;
  return normalizeIp(entries[entries.length - hops]);
}

export function loadAuthOptions(env: NodeJS.ProcessEnv = process.env): AuthOptions {
  const trustedIps = new Set(
    (env.SCIVERSE_MCP_TRUSTED_IPS ?? "")
      .split(/[\s,]+/)
      .map(normalizeIp)
      .filter((s) => s.length > 0),
  );
  const trustedProxies = parseTrustedProxies(env.SCIVERSE_MCP_TRUSTED_PROXIES);
  const hopsRaw = env.SCIVERSE_MCP_TRUSTED_PROXY_HOPS?.trim();
  const parsed = hopsRaw ? Number.parseInt(hopsRaw, 10) : DEFAULT_TRUSTED_HOPS;
  const trustedHops = Number.isFinite(parsed) && parsed >= 1 ? parsed : DEFAULT_TRUSTED_HOPS;
  return { trustedIps, trustedProxies, trustedHops };
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
  const ip = clientIp(req, opts);
  if (ip && opts.trustedIps.has(ip)) {
    return { lane: "trusted", token: config.token, channel: config.channel };
  }
  return null;
}

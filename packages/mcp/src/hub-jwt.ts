import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { decodeProtectedHeader, importSPKI, importPKCS8, jwtVerify, SignJWT } from 'jose';
import type { CredentialProvider } from './tools.js';

type CryptoKey = Awaited<ReturnType<typeof importSPKI>>;

export interface HubConfig {
  issuer: string;
  audience: string;
  algorithm: string;
  maxTtl: number;
  publicKeys: Map<string, CryptoKey>;
  singleKey?: CryptoKey;
  signingKey: CryptoKey;
  signingKeyId: string;
  syncSubjects: Set<string>;
}
export interface HubIdentity { sub: string; iat: number; exp: number }
const ALGORITHMS = new Set(['RS256', 'ES256', 'EdDSA']);
const ROUTES = new Set(['POST /meta-search','POST /agentic-search','GET /meta-catalog','GET /content','GET /resource']);

export async function loadHubConfig(env: NodeJS.ProcessEnv = process.env): Promise<HubConfig | undefined> {
  if (env.SCIVERSE_MCP_HUB_JWT_ENABLED !== 'true') return undefined;
  const required = (name: string) => {
    const value = env[name]?.trim();
    if (!value) throw new Error(`Missing configuration: ${name}`);
    return value;
  };
  const algorithm = required('SCIVERSE_MCP_HUB_JWT_ALGORITHM');
  if (!ALGORITHMS.has(algorithm)) throw new Error('Unsupported Hub signing algorithm');
  const issuer = required('SCIVERSE_MCP_HUB_JWT_ISSUER');
  if (issuer !== 'scp-hub') throw new Error('Unexpected Hub issuer');
  const maxTtl = Number(env.SCIVERSE_MCP_HUB_JWT_MAX_TTL_SECONDS ?? 900);
  if (!Number.isSafeInteger(maxTtl) || maxTtl < 1 || maxTtl > 900) throw new Error('Invalid Hub maximum TTL');
  const keys: unknown = JSON.parse(await readFile(required('SCIVERSE_MCP_HUB_JWT_PUBLIC_KEYS_FILE'), 'utf8'));
  if (!keys || typeof keys !== 'object' || Array.isArray(keys)) throw new Error('Invalid public key set');
  const publicKeys = new Map<string, CryptoKey>();
  for (const [kid, pem] of Object.entries(keys)) {
    if (!kid || typeof pem !== 'string') throw new Error('Invalid public key entry');
    publicKeys.set(kid, await importSPKI(pem, algorithm));
  }
  if (!publicKeys.size) throw new Error('Empty Hub key set');
  const singleMode = env.SCIVERSE_MCP_HUB_JWT_ALLOW_MISSING_KID === 'true';
  if (singleMode && publicKeys.size !== 1) throw new Error('Missing kid requires exactly one configured key');
  return { issuer, audience: required('SCIVERSE_MCP_HUB_JWT_AUDIENCE'), algorithm, maxTtl, publicKeys,
    singleKey: singleMode ? publicKeys.values().next().value : undefined,
    signingKey: await importPKCS8(await readFile(required('SCIVERSE_MCP_DELEGATION_PRIVATE_KEY_FILE'), 'utf8'), 'RS256'),
    signingKeyId: required('SCIVERSE_MCP_DELEGATION_KEY_ID'),
    syncSubjects: new Set((env.SCIVERSE_MCP_HUB_SYNC_SUBJECTS ?? '').split(',').filter(Boolean)) };
}

export async function verifyHubJwt(token: string, config: HubConfig): Promise<HubIdentity> {
  if (!token || token.length > 16384) throw new Error('Invalid Hub credential');
  const header = decodeProtectedHeader(token);
  if (header.alg !== config.algorithm || header.jku || header.x5u) throw new Error('Invalid Hub header');
  const key = header.kid === undefined ? config.singleKey : config.publicKeys.get(header.kid);
  if (!key) throw new Error('Unknown Hub key');
  const {payload} = await jwtVerify(token, key, { algorithms:[config.algorithm], issuer:config.issuer,
    audience:config.audience, requiredClaims:['sub','iat','exp'], clockTolerance:0 });
  const {sub,iat,exp} = payload;
  const now = Math.floor(Date.now()/1000);
  if (payload.aud !== config.audience || typeof sub !== 'string' || !sub.trim() || sub.length > 191 ||
    !Number.isSafeInteger(iat) || !Number.isSafeInteger(exp) || iat! > now+30 ||
    exp! <= iat! || exp!-iat! > config.maxTtl) throw new Error('Invalid Hub claims');
  return {sub,iat:iat!,exp:exp!};
}

export function delegationProvider(identity: HubIdentity, config: HubConfig): CredentialProvider {
  return async (method, path) => {
    const now = Math.floor(Date.now()/1000);
    if (identity.exp <= now || config.syncSubjects.has(identity.sub) || !ROUTES.has(`${method} ${path}`)) {
      throw new Error('Delegation not allowed');
    }
    const token = await new SignJWT({ auth_method:'scp_hub_jwt', auth_source:'scp',
      hub_iat:identity.iat, hub_exp:identity.exp, http_method:method, http_path:path })
      .setProtectedHeader({alg:'RS256',kid:config.signingKeyId}).setIssuer('sciverse-mcp')
      .setAudience('sciverse-api').setSubject(identity.sub).setIssuedAt(now)
      .setExpirationTime(Math.min(now+60,identity.exp)).setJti(randomUUID()).sign(config.signingKey);
    return {authorization:`Bearer ${token}`,source:'scp'};
  };
}

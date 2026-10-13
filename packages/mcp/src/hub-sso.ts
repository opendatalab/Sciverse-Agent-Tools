import { readFile } from 'node:fs/promises';
import { createHash, randomUUID } from 'node:crypto';
import { request } from 'node:https';
import { importPKCS8, SignJWT } from 'jose';
import type { HubIdentity } from './hub-jwt.js';
import { createDelegationProvider, type SigningConfig } from './delegation.js';

export interface HubSsoConfig extends SigningConfig {
  mode: 'hub_sso'; clientId: string; maxTtl: number;
  validate: (body: string, authorization: string) => Promise<unknown>;
}
export class SsoAuthError extends Error {
  constructor(public readonly status: number, public readonly code: string) { super(code); }
}
const PATH = '/api/internal/identity/validate-sso';
/** 不使用全局代理、不跟随重定向、不关闭 CA/SAN 验证。 */
export function validatorTransport(url: URL, ca: string, client?: { cert: string; key: string }): HubSsoConfig['validate'] {
  return (body, authorization) => new Promise((resolve, reject) => {
    const fail = () => reject(new SsoAuthError(503, 'SSO_VALIDATION_UNAVAILABLE'));
    const req = request(url, { method:'POST', ca, ...client, rejectUnauthorized:true,
      headers:{authorization,'content-type':'application/json','content-length':Buffer.byteLength(body)},
      signal:AbortSignal.timeout(10000) }, res => {
      const chunks: Buffer[] = []; let size = 0;
      res.on('data', chunk => { size += chunk.length; if(size > 16384) {res.destroy();fail();} else chunks.push(Buffer.from(chunk)); });
      res.on('error', fail);
      res.on('end', () => {
        if(res.statusCode !== 200) {reject(new SsoAuthError(res.statusCode === 401 ? 401 : 503, res.statusCode === 401 ? 'INVALID_SSO_TOKEN' : 'SSO_VALIDATION_UNAVAILABLE'));return;}
        try {resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));} catch {fail();}
      });
    });
    req.on('error', fail);req.end(body);
  });
}
export async function loadHubSsoConfig(env: NodeJS.ProcessEnv = process.env): Promise<HubSsoConfig | undefined> {
  const mode = env.SCIVERSE_MCP_SCP_AUTH_MODE ?? 'disabled';
  if(mode === 'disabled') return undefined;
  if(mode !== 'hub_sso' || env.SCIVERSE_MCP_HUB_JWT_ENABLED === 'true') throw new Error('Invalid SCP auth mode');
  if(env.SCIVERSE_MCP_SCP_SOURCE_VERIFIED !== 'true') throw new Error('Hub source restriction not verified');
  const required = (key:string) => { const value=env[key]?.trim();if(!value) throw new Error(`Missing configuration: ${key}`);return value; };
  const url = new URL(required('SCIVERSE_MCP_SSO_VALIDATION_URL'));
  if(url.protocol !== 'https:' || url.hostname !== 'sciverse-platform-fe.sciverse.svc.cluster.local' || url.pathname !== PATH || url.username || url.password || url.search || url.hash) throw new Error('Invalid SSO validator URL');
  const maxTtl = Number(required('SCIVERSE_MCP_SSO_MAX_TTL_SECONDS'));
  if(!Number.isSafeInteger(maxTtl) || maxTtl < 1 || maxTtl > 86400) throw new Error('Invalid SSO TTL');
  return {mode, maxTtl,clientId:required('SCIVERSE_MCP_SSO_CLIENT_ID'),
    signingKey:await importPKCS8(await readFile(required('SCIVERSE_MCP_DELEGATION_PRIVATE_KEY_FILE'),'utf8'),'RS256'),
    signingKeyId:required('SCIVERSE_MCP_DELEGATION_KEY_ID'),
    syncSubjects:new Set((env.SCIVERSE_MCP_HUB_SYNC_SUBJECTS ?? '').split(',').map(s=>s.trim()).filter(Boolean)),
    validate:validatorTransport(url,await readFile(required('SCIVERSE_MCP_SSO_VALIDATION_CA_FILE'),'utf8'), {
      cert:await readFile(required('SCIVERSE_MCP_SSO_VALIDATION_CLIENT_CERT_FILE'),'utf8'),
      key:await readFile(required('SCIVERSE_MCP_SSO_VALIDATION_CLIENT_KEY_FILE'),'utf8')})};
}
export async function verifyHubSso(token:string, config:HubSsoConfig): Promise<HubIdentity> {
  if(!token || token.length > 12000 || /\s/.test(token)) throw new SsoAuthError(401,'INVALID_SSO_TOKEN');
  const body=JSON.stringify({token,requestId:randomUUID()});const now=Math.floor(Date.now()/1000);
  const serviceToken=await new SignJWT({action:'validate_sso',http_method:'POST',http_path:PATH,
    body_sha256:createHash('sha256').update(body).digest('hex')})
    .setProtectedHeader({alg:'RS256',kid:config.signingKeyId}).setIssuer('sciverse-mcp')
    .setAudience('sciverse-sso-validator').setIssuedAt(now).setExpirationTime(now+30).setJti(randomUUID()).sign(config.signingKey);
  let value:unknown;
  try {value=await config.validate(body,`Bearer ${serviceToken}`);} catch(e) {
    if(e instanceof SsoAuthError) throw e;
    throw new SsoAuthError(503,'SSO_VALIDATION_UNAVAILABLE');
  }
  const p=value as Record<string,unknown>;const checkedAt=Math.floor(Date.now()/1000);
  if(!p || typeof p!=='object' || p.clientId!==config.clientId || typeof p.ssoUid!=='string' || !p.ssoUid.trim() || p.ssoUid.length>191 ||
    typeof p.issuedAt!=='number' || typeof p.expiresAt!=='number' || typeof p.verifiedAt!=='number' ||
    !Number.isSafeInteger(p.issuedAt) || !Number.isSafeInteger(p.expiresAt) || !Number.isSafeInteger(p.verifiedAt) ||
    p.issuedAt<=0 || p.issuedAt>checkedAt || p.expiresAt<=checkedAt || p.expiresAt<=p.issuedAt || p.expiresAt-p.issuedAt>config.maxTtl ||
    p.verifiedAt>checkedAt || checkedAt-p.verifiedAt>10) throw new SsoAuthError(401,'INVALID_SSO_IDENTITY');
  return {sub:p.ssoUid,iat:p.issuedAt,exp:p.expiresAt};
}
export function ssoDelegationProvider(identity:HubIdentity, config:HubSsoConfig) {
  return createDelegationProvider(identity,config,{ver:2,auth_method:'scp_hub_sso',external_iat:identity.iat,external_exp:identity.exp});
}

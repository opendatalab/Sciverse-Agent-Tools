import { randomUUID } from 'node:crypto';
import { SignJWT, type JWTPayload } from 'jose';
import type { CredentialProvider } from './tools.js';
import type { HubConfig, HubIdentity } from './hub-jwt.js';
export type SigningConfig = Pick<HubConfig, 'signingKey' | 'signingKeyId' | 'syncSubjects'>;
const ROUTES = new Set(['POST /meta-search','POST /agentic-search','GET /meta-catalog','GET /content','GET /resource']);
export function createDelegationProvider(identity: HubIdentity, config: SigningConfig, claims: JWTPayload): CredentialProvider {
  return async (method, path) => {
    const now = Math.floor(Date.now()/1000);
    if (identity.exp <= now || config.syncSubjects.has(identity.sub) || !ROUTES.has(`${method} ${path}`)) throw new Error('Delegation not allowed');
    const token = await new SignJWT({...claims, auth_source:'scp', http_method:method, http_path:path})
      .setProtectedHeader({alg:'RS256',kid:config.signingKeyId}).setIssuer('sciverse-mcp')
      .setAudience('sciverse-api').setSubject(identity.sub).setIssuedAt(now)
      .setExpirationTime(Math.min(now+60,identity.exp)).setJti(randomUUID()).sign(config.signingKey);
    return {authorization:`Bearer ${token}`,source:'scp'};
  };
}

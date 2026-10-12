import type { IncomingMessage, ServerResponse } from 'node:http';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import type { Config } from './config.js';
import { createServer } from './server.js';
import { verifyHubJwt, delegationProvider, type HubConfig } from './hub-jwt.js';

function reject(res: ServerResponse, status: number, code: string): void {
  res.statusCode = status;
  res.setHeader('content-type','application/json');
  res.setHeader('cache-control','no-store');
  if (status === 401) res.setHeader('www-authenticate','Bearer');
  res.end(JSON.stringify({error:{code}}));
}
export async function handleScp(req: IncomingMessage, res: ServerResponse, config: Config, hub: HubConfig): Promise<void> {
  const started = Date.now();
  let sub: string | undefined;
  let rpc: string | undefined;
  res.once('close', () => process.stdout.write(JSON.stringify({event:'scp_request',auth_source:'scp',
    user_sso_uid:sub,rpc,status:res.statusCode,duration_ms:Date.now()-started})+'\n'));
  const bearer = req.headers.authorization?.match(/^Bearer ([^\s]+)$/i)?.[1];
  let identity;
  try { identity = await verifyHubJwt(bearer ?? '',hub); }
  catch { reject(res,401,'INVALID_HUB_JWT'); return; }
  sub = identity.sub;
  if (req.method !== 'POST') { res.setHeader('allow','POST'); reject(res,405,'METHOD_NOT_ALLOWED'); return; }
  // Hub 通道逐请求鉴权，不接收跨请求 session。
  if (req.headers['mcp-session-id']) { reject(res,400,'STATELESS_ENDPOINT'); return; }
  let body: unknown;
  try {
    const chunks: Buffer[] = []; let size = 0;
    for await (const chunk of req) {
      size += chunk.length;
      if (size > 1024*1024) { reject(res,413,'BODY_TOO_LARGE'); return; }
      chunks.push(Buffer.from(chunk));
    }
    body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch { if (!res.destroyed) reject(res,400,'INVALID_JSON'); return; }
  if (Array.isArray(body) || !body || typeof body !== 'object') { reject(res,400,'INVALID_REQUEST'); return; }
  const method = (body as {method?:unknown}).method;
  rpc = typeof method === 'string' ? method.slice(0,128) : undefined;
  if (hub.syncSubjects.has(identity.sub) && method !== 'initialize' && method !== 'tools/list' && method !== 'notifications/initialized') {
    reject(res,403,'SYNC_SUBJECT_FORBIDDEN'); return;
  }
  const transport = new StreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
  const server = createServer(config, delegationProvider(identity,hub));
  const cleanup = () => { void server.close().catch(() => undefined); };
  res.once('close',cleanup);
  try { await server.connect(transport); await transport.handleRequest(req,res,body); }
  catch { if (!res.headersSent) reject(res,500,'INTERNAL_ERROR'); else res.end(); }
  finally { if (res.writableEnded || res.destroyed) await server.close().catch(() => undefined); }
}

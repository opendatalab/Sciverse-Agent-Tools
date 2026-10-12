import { afterAll, beforeAll, expect, it, vi } from 'vitest';
import { generateKeyPair, SignJWT, jwtVerify } from 'jose';
import { startHttpServer, type HttpServerHandle } from '../src/cli-http.js';
import { loadAuthOptions } from '../src/http-auth.js';
import type { HubConfig } from '../src/hub-jwt.js';
let server: HttpServerHandle;
let cfg: HubConfig;
let hubKey: CryptoKey;
let internalKey: CryptoKey;
const realFetch = globalThis.fetch;
beforeAll(async () => {
  const hub = await generateKeyPair('RS256'); const internal = await generateKeyPair('RS256');
  hubKey = hub.privateKey; internalKey = internal.publicKey;
  cfg = {issuer:'scp-hub',audience:'test',algorithm:'RS256',maxTtl:900,
    publicKeys:new Map([['hub',hub.publicKey]]),signingKey:internal.privateKey,signingKeyId:'mcp',syncSubjects:new Set(['probe'])};
  server = await startHttpServer({token:'legacy-secret',baseUrl:'https://api.sciverse.space',channel:'scp'},
    {host:'127.0.0.1',port:0,auth:loadAuthOptions({SCIVERSE_MCP_TRUSTED_IPS:'127.0.0.1'}),scp:cfg});
});
afterAll(async () => { vi.unstubAllGlobals(); await server?.close(); });
async function jwt(sub='001') {
  const now = Math.floor(Date.now()/1000);
  return new SignJWT({iss:'scp-hub',aud:'test',sub,iat:now,exp:now+300})
    .setProtectedHeader({alg:'RS256',kid:'hub'}).sign(hubKey);
}
async function rpc(method:string, token?:string, params?:unknown) {
  return realFetch(`http://127.0.0.1:${server.port}/mcp/scp`, {method:'POST',headers:{
    'content-type':'application/json',accept:'application/json, text/event-stream',
    ...(token ? {authorization:`Bearer ${token}`} : {})},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
}
it('非法 JWT 不得回退可信 IP 的固定 token',async()=>{
  expect((await rpc('tools/list')).status).toBe(401);
  expect((await rpc('tools/list','bad')).status).toBe(401);
});
it('无状态 list 与 initialize 不发 session id，探活不可调用工具',async()=>{
  const res = await rpc('tools/list',await jwt('probe')); expect(res.status).toBe(200);
  expect(res.headers.get('mcp-session-id')).toBeNull();
  expect((await res.json()).result.tools.length).toBe(5);
  const init = await rpc('initialize',await jwt(), {protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'test',version:'1'}});
  expect(init.status).toBe(200); expect(init.headers.get('mcp-session-id')).toBeNull();
  expect((await rpc('tools/call',await jwt('probe'),{name:'list_catalog',arguments:{}})).status).toBe(403);
});
it('并发不同用户独立签名；后端 403/503 在工具错误中保留',async()=>{
  const subjects: string[] = [];
  vi.stubGlobal('fetch',vi.fn(async (_url, options) => {
    const {payload} = await jwtVerify(options.headers.authorization.slice(7),internalKey,{issuer:'sciverse-mcp',audience:'sciverse-api'});
    subjects.push(payload.sub!); expect(options.redirect).toBe('error');
    expect(options.headers['x-sciverse-source']).toBe('scp');
    return new Response(JSON.stringify({code:'PROFILE_UNAVAILABLE'}),{status:503});
  }));
  try {
    const results = await Promise.all(['001','002'].map(async uid => (await rpc('tools/call',await jwt(uid),{name:'list_catalog',arguments:{}})).json()));
    expect(subjects.sort()).toEqual(['001','002']);
    for (const result of results) { expect(result.result.isError).toBe(true); expect(JSON.parse(result.result.content[0].text).status).toBe(503); }
  } finally { vi.unstubAllGlobals(); }
});
it('关闭新通道仍不能落入旧可信 IP 分支',async()=>{
  const off = await startHttpServer({token:'legacy',baseUrl:'https://api.sciverse.space',channel:'scp'},
    {host:'127.0.0.1',port:0,auth:loadAuthOptions({SCIVERSE_MCP_TRUSTED_IPS:'127.0.0.1'})});
  try { expect((await realFetch(`http://127.0.0.1:${off.port}/mcp/scp`,{method:'POST'})).status).toBe(503); }
  finally { await off.close(); }
});

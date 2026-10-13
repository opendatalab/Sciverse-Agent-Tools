import { afterAll, beforeAll, expect, it, vi } from 'vitest';
import { generateKeyPair, jwtVerify } from 'jose';
import { startHttpServer, type HttpServerHandle } from '../src/cli-http.js';
import type { HubSsoConfig } from '../src/hub-sso.js';
const realFetch=globalThis.fetch; let server:HttpServerHandle;let pub:CryptoKey;let online=0;
beforeAll(async()=>{
 const pair=await generateKeyPair('RS256');pub=pair.publicKey;
 const sso:HubSsoConfig={mode:'hub_sso',clientId:'test',maxTtl:3600,signingKey:pair.privateKey,signingKeyId:'mcp',syncSubjects:new Set(),validate:async(raw)=>{
  online++;const token=JSON.parse(raw).token;const now=Math.floor(Date.now()/1000);
  if(token==='bad')throw Error('secret');
  return {ssoUid:token,issuedAt:now-1800,expiresAt:now+120,verifiedAt:now,clientId:'test'};
 }};
 server=await startHttpServer({token:'',baseUrl:'https://api.test',channel:'scp'},{host:'127.0.0.1',port:0,scp:sso});
});
afterAll(async()=>{vi.unstubAllGlobals();await server?.close();});
const rpc=(token:string,method='tools/list',params?:unknown)=>realFetch(`http://127.0.0.1:${server.port}/mcp/scp`,{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json',accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})});
it('SSO入口在线验证、无session，空凭证拒绝且错误不泄漏',async()=>{
 const res=await rpc('001');expect(res.status).toBe(200);expect(res.headers.get('mcp-session-id')).toBeNull();expect(online).toBeGreaterThan(0);
 expect((await realFetch(`http://127.0.0.1:${server.port}/mcp/scp`,{method:'POST'})).status).toBe(401);
 const bad=await rpc('bad');expect(bad.status).toBe(503);expect(await bad.text()).not.toContain('secret');
});
it('实际HTTP并发工具请求保持用户归属，只向BE发送内部凭证',async()=>{
 const users:string[]=[];
 vi.stubGlobal('fetch',async(_url:unknown,options:RequestInit)=>{
  const bearer=(options.headers as Record<string,string>).authorization;
  const {payload}=await jwtVerify(bearer.slice(7),pub,{audience:'sciverse-api'});
  expect(payload.auth_method).toBe('scp_hub_sso');expect(payload.ver).toBe(2);users.push(payload.sub!);
  return new Response(JSON.stringify({code:'UNAVAILABLE'}),{status:503});
 });
 try {
  const responses=await Promise.all(['001','002'].map(t=>rpc(t,'tools/call',{name:'list_catalog',arguments:{}})));
  for(const res of responses)expect((await res.json()).result.isError).toBe(true);
  expect(users.sort()).toEqual(['001','002']);
 }finally{vi.unstubAllGlobals();}
});

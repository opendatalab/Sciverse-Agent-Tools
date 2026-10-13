import { beforeAll, expect, it } from 'vitest';
import { generateKeyPair, jwtVerify, exportPKCS8 } from 'jose';
import { loadHubSsoConfig, verifyHubSso, ssoDelegationProvider, type HubSsoConfig } from '../src/hub-sso.js';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
let config: HubSsoConfig; let publicKey: CryptoKey;
beforeAll(async()=>{
 const pair=await generateKeyPair('RS256'); publicKey=pair.publicKey;
 config={mode:'hub_sso',clientId:'sciverse-test',maxTtl:3600,signingKey:pair.privateKey,signingKeyId:'mcp',syncSubjects:new Set(['probe']),
 validate:async(raw,authorization)=>{
  const {payload}=await jwtVerify(authorization.slice(7),publicKey,{issuer:'sciverse-mcp',audience:'sciverse-sso-validator'});
  expect(payload.body_sha256).toBe(createHash('sha256').update(raw).digest('hex'));
  expect(payload.action).toBe('validate_sso');expect(payload.http_path).toBe('/api/internal/identity/validate-sso');
  const now=Math.floor(Date.now()/1000);
  return {ssoUid:JSON.parse(raw).token,issuedAt:now-1800,expiresAt:now+100,verifiedAt:now,clientId:'sciverse-test'};
 }};
});
it('默认关闭；未知模式、双模式及缺少SSO配置时启动失败',async()=>{
 expect(await loadHubSsoConfig({})).toBeUndefined();
 for(const env of [{SCIVERSE_MCP_SCP_AUTH_MODE:'invalid'},{SCIVERSE_MCP_SCP_AUTH_MODE:'hub_sso',SCIVERSE_MCP_HUB_JWT_ENABLED:'true'},{SCIVERSE_MCP_SCP_AUTH_MODE:'hub_sso'}]) await expect(loadHubSsoConfig(env)).rejects.toThrow();
});
it('并发用户独立委派版本2；外部寿命不套900秒限制',async()=>{
 const ids=await Promise.all(['001','002'].map(x=>verifyHubSso(x,config)));
 const tokens=await Promise.all(ids.map(id=>ssoDelegationProvider(id,config)('GET','/meta-catalog')));
 for(let i=0;i<tokens.length;i++){
  const {payload:p}=await jwtVerify(tokens[i].authorization.slice(7),publicKey,{audience:'sciverse-api'});
  expect(p.sub).toBe(['001','002'][i]);expect(p.ver).toBe(2);expect(p.auth_method).toBe('scp_hub_sso');expect(p.external_exp).toBe(ids[i].exp);expect(p).not.toHaveProperty('hub_exp');expect(p).not.toHaveProperty('token');expect(p.exp!-p.iat!).toBeLessThanOrEqual(60);
 }
});
it('错误应用、时间、缺字段和上游异常拒绝且脱敏',async()=>{
 const now=Math.floor(Date.now()/1000);const valid={ssoUid:'001',issuedAt:now-5,expiresAt:now+100,verifiedAt:now,clientId:'sciverse-test'};
 for(const change of [{clientId:'other'},{issuedAt:now+10},{expiresAt:now-1},{verifiedAt:now-100},{ssoUid:7},{issuedAt:undefined}]) await expect(verifyHubSso('opaque',{...config,validate:async()=>({...valid,...change})})).rejects.toThrow();
 await expect(verifyHubSso('opaque',{...config,validate:async()=>{throw Error('SECRET');}})).rejects.not.toThrow('SECRET');
 await expect(verifyHubSso('',config)).rejects.toThrow();
});
it('同步身份、非法路径和过期上下文不可委派',async()=>{
 for(const [sub,exp,path] of [['probe',Math.floor(Date.now()/1000)+20,'/meta-catalog'],['001',1,'/meta-catalog'],['001',Math.floor(Date.now()/1000)+20,'/admin']] as const) await expect(ssoDelegationProvider({sub,iat:1,exp},config)('GET',path)).rejects.toThrow();
});

it('约定渠道无需来源认证声明；仍要求完整SSO配置',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'scp-config-'));
 try {
  const pair=await generateKeyPair('RS256',{extractable:true});
  const key=join(dir,'signing.pem');const tls=join(dir,'tls-fixture.pem');
  await writeFile(key,await exportPKCS8(pair.privateKey),{mode:0o600});
  await writeFile(tls,'transport fixture; no network request in config loading');
  const env={SCIVERSE_MCP_SCP_AUTH_MODE:'hub_sso',SCIVERSE_MCP_SSO_VALIDATION_URL:'https://sciverse-platform-fe.sciverse.svc.cluster.local:8443/api/internal/identity/validate-sso',SCIVERSE_MCP_SSO_MAX_TTL_SECONDS:'3600',SCIVERSE_MCP_SSO_CLIENT_ID:'test-client',SCIVERSE_MCP_DELEGATION_PRIVATE_KEY_FILE:key,SCIVERSE_MCP_DELEGATION_KEY_ID:'test-key',SCIVERSE_MCP_SSO_VALIDATION_CA_FILE:tls,SCIVERSE_MCP_SSO_VALIDATION_CLIENT_CERT_FILE:tls,SCIVERSE_MCP_SSO_VALIDATION_CLIENT_KEY_FILE:tls};
  const loaded=await loadHubSsoConfig(env);
  expect(loaded?.mode).toBe('hub_sso');expect(loaded?.clientId).toBe('test-client');
  await expect(loadHubSsoConfig({...env,SCIVERSE_MCP_SSO_MAX_TTL_SECONDS:''})).rejects.toThrow('Missing configuration');
  await expect(loadHubSsoConfig({...env,SCIVERSE_MCP_SSO_VALIDATION_URL:'http://sciverse-platform-fe.sciverse.svc.cluster.local/api/internal/identity/validate-sso'})).rejects.toThrow('Invalid SSO validator URL');
 } finally {await rm(dir,{recursive:true,force:true});}
});

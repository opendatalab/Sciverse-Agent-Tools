import { beforeAll, describe, expect, it } from 'vitest';
import { generateKeyPair, SignJWT, jwtVerify } from 'jose';
import { verifyHubJwt, delegationProvider, type HubConfig } from '../src/hub-jwt.js';
let config: HubConfig;
let privateKey: CryptoKey;
let internalPublic: CryptoKey;
beforeAll(async () => {
  const hub = await generateKeyPair('RS256');
  const internal = await generateKeyPair('RS256');
  privateKey = hub.privateKey; internalPublic = internal.publicKey;
  config = { issuer: 'scp-hub', audience: 'test-sciverse', algorithm: 'RS256', maxTtl: 900,
    publicKeys: new Map([['hub-1', hub.publicKey]]), signingKey: internal.privateKey,
    signingKeyId: 'mcp-1', syncSubjects: new Set(['probe']) };
});
async function token(claims: Record<string, unknown> = {}, kid = 'hub-1') {
  const now = Math.floor(Date.now()/1000);
  return new SignJWT({ iss:'scp-hub', aud:'test-sciverse', sub:'00123', iat:now, exp:now+300, ...claims })
    .setProtectedHeader({alg:'RS256',kid}).sign(privateKey);
}
describe('Hub 身份及委托隔离', () => {
  it('保留 UID 前导零，逐请求签发绑定路径的内部凭证', async () => {
    const identity = await verifyHubJwt(await token(), config);
    const provider = delegationProvider(identity, config);
    const a = await provider('GET','/meta-catalog');
    const b = await provider('GET','/meta-catalog');
    const {payload} = await jwtVerify(a.authorization.slice(7), internalPublic,
      {issuer:'sciverse-mcp',audience:'sciverse-api'});
    expect(payload.sub).toBe('00123');
    expect(payload.http_path).toBe('/meta-catalog');
    expect(payload.auth_source).toBe('scp');
    expect(a.authorization).not.toBe(b.authorization);
    expect(a.source).toBe('scp');
  });
  it.each([{aud:'other'},{iss:'sso'},{sub:''},{sub:123},{iat:1},{exp:1},
    {exp:Math.floor(Date.now()/1000)+901},{nbf:Math.floor(Date.now()/1000)+120}])('拒绝错误声明 %j', async claims => {
    await expect(verifyHubJwt(await token(claims), config)).rejects.toThrow();
  });
  it('拒绝未知 kid、非法路径与探活身份业务调用', async () => {
    await expect(verifyHubJwt(await token({},'unknown'),config)).rejects.toThrow();
    const id = await verifyHubJwt(await token(),config);
    await expect(delegationProvider(id,config)('POST','/admin')).rejects.toThrow();
    const probe = await verifyHubJwt(await token({sub:'probe'}),config);
    await expect(delegationProvider(probe,config)('GET','/meta-catalog')).rejects.toThrow();
  });
});
it('轮换公钥可以重叠，撤销旧 key 后旧凭证立即被拒绝', async () => {
  const oldToken = await token();
  const next = await generateKeyPair('RS256');
  const now = Math.floor(Date.now()/1000);
  const nextToken = await new SignJWT({iss:'scp-hub',aud:'test-sciverse',sub:'00123',iat:now,exp:now+300})
    .setProtectedHeader({alg:'RS256',kid:'hub-2'}).sign(next.privateKey);
  const rotated = {...config,publicKeys:new Map([...config.publicKeys,['hub-2',next.publicKey]])};
  await verifyHubJwt(oldToken,rotated); await verifyHubJwt(nextToken,rotated);
  rotated.publicKeys.delete('hub-1');
  await expect(verifyHubJwt(oldToken,rotated)).rejects.toThrow();
  await verifyHubJwt(nextToken,rotated);
});
it('拒绝错误签名、算法替换、多受众和远端 key URL', async () => {
  const next = await generateKeyPair('RS256'); const now = Math.floor(Date.now()/1000);
  const claims = {iss:'scp-hub',aud:'test-sciverse',sub:'00123',iat:now,exp:now+300};
  const forged = await new SignJWT(claims).setProtectedHeader({alg:'RS256',kid:'hub-1'}).sign(next.privateKey);
  await expect(verifyHubJwt(forged,config)).rejects.toThrow();
  const symmetric = await new SignJWT(claims).setProtectedHeader({alg:'HS256',kid:'hub-1'}).sign(new Uint8Array(32));
  await expect(verifyHubJwt(symmetric,config)).rejects.toThrow();
  await expect(verifyHubJwt(await token({aud:['test-sciverse','other']}),config)).rejects.toThrow();
  const remote = await new SignJWT(claims).setProtectedHeader({alg:'RS256',kid:'hub-1',jku:'https://evil.test/key'}).sign(privateKey);
  await expect(verifyHubJwt(remote,config)).rejects.toThrow();
});
it('仅显式单公钥模式允许缺 kid',async()=>{
  const now=Math.floor(Date.now()/1000);
  const raw=await new SignJWT({iss:'scp-hub',aud:'test-sciverse',sub:'00123',iat:now,exp:now+300})
    .setProtectedHeader({alg:'RS256'}).sign(privateKey);
  await expect(verifyHubJwt(raw,config)).rejects.toThrow();
  expect((await verifyHubJwt(raw,{...config,singleKey:config.publicKeys.get('hub-1')})).sub).toBe('00123');
});

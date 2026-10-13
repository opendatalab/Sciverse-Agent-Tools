import { afterAll, beforeAll, expect, it } from 'vitest';
import { createServer, type Server } from 'node:https';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { validatorTransport } from '../src/hub-sso.js';
let dir:string;let server:Server;let port:number;let cert:string;let status=200;let payload='{"ssoUid":"001"}';let calls=0;
beforeAll(async()=>{
 dir=mkdtempSync(join(tmpdir(),'sciverse-test-tls-'));
 execFileSync('openssl',['req','-x509','-newkey','rsa:2048','-nodes','-keyout',join(dir,'key.pem'),'-out',join(dir,'cert.pem'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],{stdio:'ignore'});
 cert=readFileSync(join(dir,'cert.pem'),'utf8');
 server=createServer({key:readFileSync(join(dir,'key.pem')),cert},(req,res)=>{
  calls++;req.resume();res.writeHead(status,{'content-type':'application/json',location:'/redirect-target'});res.end(payload);
 });
 await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
 port=(server.address() as {port:number}).port;
});
afterAll(async()=>{await new Promise<void>(resolve=>server?.close(()=>resolve()));if(dir)rmSync(dir,{recursive:true,force:true});});
it('校验证书信任及SAN，拒绝重定向和超大响应',async()=>{
 const good=validatorTransport(new URL(`https://localhost:${port}/validate`),cert);
 expect(await good('{}','Bearer test')).toEqual({ssoUid:'001'});
 await expect(validatorTransport(new URL(`https://127.0.0.1:${port}/validate`),cert)('{}','Bearer test')).rejects.toThrow('SSO_VALIDATION_UNAVAILABLE');
 await expect(validatorTransport(new URL(`https://localhost:${port}/validate`),'')('{}','Bearer test')).rejects.toThrow();
 status=302;const before=calls;await expect(good('{}','Bearer test')).rejects.toThrow();expect(calls-before).toBe(1);
 status=200;payload='x'.repeat(17000);await expect(good('{}','Bearer test')).rejects.toThrow();
});

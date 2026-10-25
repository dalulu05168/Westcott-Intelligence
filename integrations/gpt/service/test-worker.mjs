import assert from 'node:assert/strict';
import worker, {validateRecord} from './worker.mjs';

const now=Date.now();
const stamp=new Date(now-1000).toISOString();
const source='https://source.example.test/article';
const record={kind:'news',target_date:'2026-10-23',slot:'14:00',observed_at:stamp,payload:{source_url:source,items:[{title:'TEST ONLY',source_url:source,published_at:stamp,event_at:null,data_as_of:null}]}};
assert.equal(validateRecord(record,now).kind,'news');
for(const change of [{target_date:'2026-02-30'},{target_date:'9999-99-99'},{slot:'14:01'},{member_id:'66'},{observed_at:'2026-10-23T12:00:00'},{observed_at:new Date(now+60000).toISOString()}]) {
  assert.throws(()=>validateRecord({...record,...change},now));
}
assert.throws(()=>validateRecord({...record,payload:{...record.payload,items:[{title:'missing-source'}]}},now));
const queries=[];
const env={READ_KEY:'test-read-'.padEnd(40,'r'),WRITE_KEY:'test-write-'.padEnd(40,'w'),DB:{
  prepare(sql){return {first:async()=>null,bind(...params){queries.push({sql,params});return {all:async()=>({results:[]})};}}},
  batch:async statements=>{assert.equal(statements.length,1);return [];}
}};
const req=(path,key=env.READ_KEY,options={})=>new Request('https://fixture.integration.local'+path,{...options,headers:{authorization:'Bearer '+key,'content-type':'application/json',...options.headers}});
let res=await worker.fetch(req('/v1/news?date=2026-10-23&slot=14:00','wrong'),env);
assert.equal(res.status,401);
res=await worker.fetch(req('/v1/news?date=2026-10-23&slot=14:00'),env);
assert.equal(res.status,200);
assert.equal((await res.json()).status,'missing');
assert.deepEqual(queries.at(-1).params,['news','2026-10-23','14:00']);
assert.ok(!queries.at(-1).sql.includes(' OR '));
// Winter endpoint does not invent an edition when no new slot record exists.
res=await worker.fetch(req('/v1/news?date=2026-10-26&slot=11:05'),env);
assert.equal(res.status,200);
assert.equal((await res.json()).status,'missing');
assert.deepEqual(queries.at(-1).params,['news','2026-10-26','11:05']);
res=await worker.fetch(req('/v1/news?date=2026-02-30&slot=14:00'),env);
assert.equal(res.status,400);
res=await worker.fetch(req('/v1/context?query=test&member_id=66'),env);
assert.equal(res.status,400);
res=await worker.fetch(req('/internal/records',env.READ_KEY,{method:'POST',body:JSON.stringify({records:[record]})}),env);
assert.equal(res.status,401);
res=await worker.fetch(req('/internal/records',env.WRITE_KEY,{method:'POST',body:JSON.stringify({records:[record]})}),env);
assert.equal(res.status,201);
assert.equal((await res.json()).adopted,false);
res=await worker.fetch(req('/v1/handoff?date=2026-10-23'),env);
assert.equal((await res.json()).status,'missing');
const saved={id:'fixture',kind:'news',target_date:record.target_date,slot:record.slot,member_id:'',observed_at:new Date(now-3*3600000).toISOString(),payload:JSON.stringify(record.payload)};
const staleEnv={...env,DB:{prepare(){return {bind(){return {all:async()=>({results:[saved]})};}}}}};
res=await worker.fetch(req('/v1/news?date=2026-10-23&slot=14:00'),staleEnv);
assert.equal((await res.json()).status,'stale');
console.log('PASS: validation, authentication, separated read/write keys, exact-date missing result, append receipt, no adoption, stale result. D1 is mocked; no live deployment tested.');

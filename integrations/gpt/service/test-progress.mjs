import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker from './worker.mjs';

const sql=new DatabaseSync(':memory:');
sql.exec(readFileSync(new URL('./schema.sql',import.meta.url),'utf8'));
sql.exec(readFileSync(new URL('./progress-schema.sql',import.meta.url),'utf8'));
const db={
  prepare(query){
    return {
      bind(...values){
        const statement=sql.prepare(query);
        return {
          first:async()=>statement.get(...values)||null,
          all:async()=>({results:statement.all(...values)}),
          run:async()=>({meta:{changes:Number(statement.run(...values).changes)}})
        };
      }
    };
  }
};
const env={DB:db,READ_KEY:'fixture-read'.padEnd(40,'r'),WRITE_KEY:'fixture-write'.padEnd(40,'w'),PROGRESS_WRITES_ENABLED:'true'};
const request=(method,body,key=env.READ_KEY,query='')=>new Request('https://fixture.integration.local/v1/progress'+query,{method,headers:{authorization:'Bearer '+key,'content-type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
const save=async(body,environment=env)=>{const response=await worker.fetch(request('POST',body),environment);return {code:response.status,body:await response.json()};};
const get=async(query='')=>{const response=await worker.fetch(request('GET',null,env.READ_KEY,query),env);assert.equal(response.status,200);return response.json();};
const fixture={workspace:'acceptance',request_id:'fixture-0001',expected_revision:0,kind:'autosave',working_state:{summary:'FIRST WINDOW',working_draft:'draft is not adopted',pending:['continue next window']}};
assert.equal((await get()).status,'missing');
assert.equal((await worker.fetch(request('GET',null,env.WRITE_KEY),env)).status,401);
assert.equal((await save(fixture,{...env,PROGRESS_WRITES_ENABLED:'false'})).code,403);
assert.equal((await worker.fetch(request('POST',fixture,'wrong'),env)).status,401);
assert.equal((await save(fixture)).code,201);
assert.equal((await get('?workspace=acceptance')).checkpoint.working_state.working_draft,'draft is not adopted');
assert.deepEqual((await get('?workspace=acceptance')).checkpoint.adopted_state,{});
assert.equal((await save(fixture)).body.replayed,true);
assert.equal((await save({...fixture,working_state:{summary:'different'}})).code,409);
assert.equal((await save({...fixture,request_id:'fixture-0002',adopted_state:{text:'unapproved'}})).code,400);
assert.equal((await save({...fixture,request_id:'fixture-0002',expected_revision:1,kind:'adopt',adopted_state:{text:'approved'},adoption_confirmation:'User explicitly adopted the fixture'})).code,201);
const later={...fixture,request_id:'fixture-0003',expected_revision:2,working_state:{summary:'SECOND WINDOW',working_draft:'new draft'}};
assert.equal((await save(later)).code,201);
assert.equal((await get('?workspace=acceptance')).checkpoint.adopted_state.text,'approved');
assert.equal((await get('?workspace=acceptance&revision=1')).checkpoint.working_state.summary,'FIRST WINDOW');
assert.equal((await save({...later,request_id:'fixture-stale'})).code,409);
const raceA={...later,request_id:'fixture-race-a',expected_revision:3};
const raceB={...later,request_id:'fixture-race-b',expected_revision:3};
const race=await Promise.all([save(raceA),save(raceB)]);
assert.deepEqual(race.map(r=>r.code).sort(),[201,409]);
assert.equal((await get('?workspace=acceptance')).revision,4);
assert.equal((await save({...later,request_id:'fixture-large',expected_revision:4,working_state:{summary:'too large',working_draft:'x'.repeat(86000)}})).body.error,'progress_too_large');
assert.equal((await get()).status,'missing');
assert.equal(sql.prepare('SELECT count(*) AS n FROM progress_checkpoints').get().n,4);
assert.equal((await worker.fetch(new Request('https://fixture.integration.local/internal/records',{method:'POST',headers:{authorization:'Bearer '+env.READ_KEY},body:'{}'}),env)).status,401);
console.log('PASS with real SQLite: cross-client restore, draft/adopt separation, immutable revisions, optimistic conflict, racing writers, idempotency, workspace isolation, disabled writes and credential scope. Cloudflare and GPT not tested here.');

// Authenticated source bridge. No scheduler, model call or automatic adoption.
import {handleProgress} from './progress.mjs';
import {loadRepository,handleRepository,repositoryContext,repositoryNews} from './repository.mjs';
const ZONE = 'Europe/Bucharest';
const SLOTS = new Set(['08:30','10:05','10:30','14:00','15:00','16:00','16:30','17:00']);
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const MEMBER = /^(0[1-9]|[1-5][0-9]|6[0-5])$/;
const STAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const json = (data,status=200) => new Response(JSON.stringify(data), {
  status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}
});
function validDate(value) {
  if(!DATE.test(value || ''))return false;
  const d=new Date(value+'T00:00:00Z');
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0,10)===value;
}
async function authorized(request, key) {
  if (!key || key.length < 32) return false;
  const given=request.headers.get('authorization') || '';
  const digest=async value => new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
  const [a,b]=await Promise.all([digest(given),digest('Bearer '+key)]);
  let diff=0; for(let i=0;i<a.length;i++) diff |= a[i]^b[i];
  return diff===0;
}
export function validateRecord(record, now=Date.now()) {
  if (!record || !['news','context','handoff'].includes(record.kind)) throw Error('invalid kind');
  if (!validDate(record.target_date)) throw Error('invalid target_date');
  if (!STAMP.test(record.observed_at || '') || !Number.isFinite(Date.parse(record.observed_at))) throw Error('observed_at needs timezone');
  if (Date.parse(record.observed_at)>now) throw Error('future observed_at');
  if (record.kind==='news' && !SLOTS.has(record.slot)) throw Error('invalid news slot');
  if (record.member_id && !MEMBER.test(record.member_id)) throw Error('invalid member_id');
  if (!record.payload || typeof record.payload!=='object' || Array.isArray(record.payload)) throw Error('object payload required');
  if (!record.payload.source_url || !/^https:\/\//.test(record.payload.source_url)) throw Error('HTTPS source required');
  // observed_at is ingestion/source snapshot time, never a substitute for market timestamps.
  if (record.kind==='news') {
    if (!Array.isArray(record.payload.items) || !record.payload.items.length) throw Error('news items required');
    for (const item of record.payload.items) {
      if (!item.title || !/^https:\/\//.test(item.source_url || '')) throw Error('news title/source required');
      for (const field of ['published_at','event_at','data_as_of']) {
        if (!(field in item)) throw Error('missing '+field+'; use null when unknown');
        if (item[field]!==null && (!STAMP.test(item[field]) || !Number.isFinite(Date.parse(item[field])))) throw Error('invalid '+field);
        if (item[field]!==null && field!=='event_at' && Date.parse(item[field])>now) throw Error('future '+field);
      }
    }
  }
  if (record.kind==='context' && !record.payload.text) throw Error('context text required');
  if (record.kind==='handoff' && (!record.payload.last_adopted_line || !record.payload.document_revision)) throw Error('handoff anchor required');
  return {...record,id:crypto.randomUUID(),observed_ms:Date.parse(record.observed_at),created_at:new Date(now).toISOString()};
}
export default {
  async fetch(request, env) {
    try {
      const url=new URL(request.url);
      if (request.method==='GET' && url.pathname==='/health') return json({service:'westcott-source-bridge',status:'running',collects_news:false});
      const isWrite=request.method==='POST' && ['/internal/records','/internal/repository'].includes(url.pathname);
      if (!await authorized(request,isWrite?env.WRITE_KEY:env.READ_KEY)) return json({error:'unauthorized'},401);
      if (!env.DB) return json({error:'database_not_configured'},503);
      if (url.pathname==='/v1/progress')return await handleProgress(request,env);
      if(url.pathname==='/internal/repository')return await handleRepository(request,env,null);
      const repositoryRoute=['/v1/runtime','/v1/archive','/v1/validate-scene'].includes(url.pathname);
      if(repositoryRoute){
        if(request.method!==(url.pathname==='/v1/validate-scene'?'POST':'GET'))return json({error:'method_not_allowed'},405);
        return await handleRepository(request,env,await loadRepository(env));
      }
      if (isWrite) {
        // Bounded streaming read, even when Content-Length is absent.
        const reader=request.body?.getReader();
        if (!reader) return json({error:'empty_body'},400);
        const chunks=[];let size=0;
        while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>200000){await reader.cancel();return json({error:'body_too_large'},413);}chunks.push(value);}
        const data=new Uint8Array(size);let offset=0;for(const c of chunks){data.set(c,offset);offset+=c.byteLength;}
        let body;
        try{body=JSON.parse(new TextDecoder().decode(data));}catch{return json({error:'invalid_json'},400);}
        if (!Array.isArray(body.records) || body.records.length<1 || body.records.length>20) return json({error:'require_1_to_20_records'},400);
        let records;
        try{records=body.records.map(r=>validateRecord(r));}catch(e){return json({error:e.message},400);}
        await env.DB.batch(records.map(r=>env.DB.prepare('INSERT INTO source_records(id,kind,target_date,slot,member_id,observed_at,observed_ms,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?)').bind(r.id,r.kind,r.target_date,r.slot||'',r.member_id||'',r.observed_at,r.observed_ms,JSON.stringify(r.payload),r.created_at)));
        return json({stored:true,ids:records.map(r=>r.id),adopted:false,review_status:'unverified_source_assertions'},201);
      }
      if(request.method!=='GET') return json({error:'method_not_allowed'},405);
      const kind={'/v1/news':'news','/v1/context':'context','/v1/handoff':'handoff'}[url.pathname];
      if(!kind)return json({error:'not_found'},404);
      const date=url.searchParams.get('date');
      const member=url.searchParams.get('member_id');
      let sql='SELECT * FROM source_records WHERE kind=?';
      const params=[kind];
      if(kind!=='context') {
        if(!validDate(date))return json({error:'valid_date_required'},400);
        sql+=' AND target_date=?';params.push(date);
      } else {
        const query=url.searchParams.get('query');
        if(!query || query.length>300)return json({error:'query_required_max_300'},400);
        if(member && !MEMBER.test(member))return json({error:'invalid_member_id'},400);
        if(member){sql+=' AND member_id=?';params.push(member);}
        // Simple keyword fallback only; not LlamaIndex or semantic retrieval.
        sql+=" AND json_extract(payload,'$.text') LIKE ? ESCAPE '\\'";
        params.push('%'+query.replace(/[\\%_]/g,x=>'\\'+x)+'%');
      }
      if(kind==='news') {
        const slot=url.searchParams.get('slot');
        if(!SLOTS.has(slot))return json({error:'invalid_slot'},400);
        sql+=' AND slot=?';params.push(slot);
      }
      sql+=' ORDER BY observed_ms DESC,created_at DESC LIMIT '+(kind==='context'?'12':'1');
      const result=await env.DB.prepare(sql).bind(...params).all();
      if(!result.results?.length && (kind==='context'||kind==='news')){
        const data=await loadRepository(env);
        if(data){if(kind==='context'&&member)return json(repositoryContext(data,member,url.searchParams.get('query')));
          if(kind==='news')return json(repositoryNews(data,date,url.searchParams.get('slot')));}
      }
      const now=Date.now();
      const records=(result.results || []).map(r=>({id:r.id,kind:r.kind,target_date:r.target_date,slot:r.slot,member_id:r.member_id,observed_at:r.observed_at,payload:JSON.parse(r.payload)}));
      const maxAge=kind==='context'?5*60000:2*3600000;
      const stale=records.some(r=>now-Date.parse(r.observed_at)>maxAge);
      return json({status:records.length?(stale?'stale':'candidate'):'missing',retrieved_at:new Date(now).toISOString(),timezone:ZONE,records,warnings:['接口未执行新闻事实审核；记录内容是来源声明，不自动成为已采用剧情或真实成交。','快照新鲜度不等于行情新鲜度，需另外核对每个指标data_as_of。','上下文检索当前仅关键词匹配，尚未接入LlamaIndex。']});
    }catch{return json({error:'source_unavailable'},503);}
  }
};

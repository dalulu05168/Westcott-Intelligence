// Authenticated repository archive, not real-time Docs or autonomous generation.
const send = (data, status=200) => new Response(JSON.stringify(data), {status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
export async function readBounded(request, max=8000000) {
  const reader=request.body?.getReader(); if(!reader)throw Error('empty_body');
  const chunks=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>max){await reader.cancel();throw Error('body_too_large');}chunks.push(value);}
  const bytes=new Uint8Array(size);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.length;}
  return JSON.parse(new TextDecoder().decode(bytes));
}
export function validateExport(data){
  if(data?.schema!=='westcott.repository-export.v1'||data.repository!=='dalulu05168/Westcott-Intelligence'||!Array.isArray(data.members)||data.members.length!==65||!Array.isArray(data.days)||!Array.isArray(data.news_editions)||!Array.isArray(data.rules?.rules))throw Error('invalid_repository_export');
  if(!/^[a-f0-9]{40}$/.test(data.commit)||!Number.isFinite(Date.parse(data.exported_at))||data.dirty_worktree)throw Error('uncommitted_export');
  if(new Set(data.members.map(m=>m.identity?.id)).size!==65||data.members.some((m,i)=>m.identity.id!==String(i+1).padStart(2,'0')||!['男','女'].includes(m.identity.gender)))throw Error('invalid_identity_roster');
  return data;
}
export async function loadRepository(env){
  const row=await env.DB.prepare('SELECT export_hash,payload FROM repository_exports ORDER BY stored_at DESC,rowid DESC LIMIT 1').first();
  if(!row)return null;
  const meta=JSON.parse(row.payload);if(!meta.chunk_count)return meta;
  const parts=await env.DB.prepare('SELECT payload FROM repository_export_chunks WHERE export_hash=? ORDER BY part').bind(row.export_hash).all();
  if(parts.results.length!==meta.chunk_count)throw Error('incomplete_repository_export');
  return JSON.parse(parts.results.map(r=>r.payload).join(''));
}
export function repositoryContext(data, member, query=''){
  if(member&&!/^(0[1-9]|[1-5][0-9]|6[0-5])$/.test(member))return {error:'invalid_member_id'};
  const selected=member?data.members.filter(m=>m.identity.id===member):[];
  // Return complete per-member evidence as paged records; never fabricate a lexical hit.
  return {status:'stale',retrieved_at:new Date().toISOString(),timezone:'Europe/Bucharest',document_revision:data.voice_source?.revision_id,
    repository_commit:data.commit,exported_at:data.exported_at,records:selected.map(m=>({kind:'context',member_id:m.identity.id,payload:{identity:m.identity,profile_draft:m.profile_draft,voice_snapshot:m.voice_snapshot,long_term:m.long_term,source_path:m.source_path}})),
    warnings:['Dated repository evidence, not live Google Docs. Read source dates for each quote.','Member selection is by ID; query is a retrieval request, not proof that every returned quote matches it.','Profile voice suggestions are drafts; historical staff labels do not override current male assistant.'],query};
}
export function repositoryNews(data,date,slot){
  const local=stamp=>{const d=new Date(stamp);if(!Number.isFinite(d.getTime()))return null;const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Bucharest',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d).map(x=>[x.type,x.value]));return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;};
  const cutoff=date+'T'+slot;
  // Never select a snapshot captured after the requested slot or an article published after it.
  const editions=data.news_editions.filter(x=>{const t=local(x.edition.window_end);return t&&t<=cutoff&&t.slice(0,10)===date;});
  const found=new Map();
  for(const e of editions){for(const item of e.edition.candidates||[]){const t=local(item.published_at);if(!t||t>cutoff||new Date(item.published_at)>new Date())continue;
    if(t.slice(0,10)!==date&&!['08:30','09:30'].includes(slot))continue;
    const key=item.article_url||item.id;if(!key)continue;
    found.set(key,{...item,source_text_snapshot:(item.source_text_snapshot||'').slice(0,7000),source_excerpt_truncated:(item.source_text_snapshot||'').length>7000,edition_path:e.path,source_url:item.article_url,original_image_url:item.original_image_candidate_url||null,image_match_status:'PUBLISHER_CANDIDATE_REQUIRES_REVIEW',fact_review_status:'UNREVIEWED'});
  }}
  const items=[...found.values()].sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at)).slice(0,3);
  return {status:items.length?'candidate':'missing',retrieved_at:new Date().toISOString(),timezone:'Europe/Bucharest',repository_commit:data.commit,
    records:items.length?[{kind:'news',target_date:date,slot,payload:{items,source:'repository_editions',review_status:'UNREVIEWED'}}]:[],
    coverage:editions.at(-1)?{path:editions.at(-1).path,status:editions.at(-1).edition.status,assessments_status:editions.at(-1).edition.assessments_status}:null,
    warnings:['No prior-day fallback; no synthetic news or generated pictures.','Publisher image links are candidates, not proof of visual match or a reuse license.','Repository intake is not fact verification; GPT must open original sources.','Missing means no matching imported records, not that there is no news.']};
}
export function validateScene(data, input){
  const text=input.text;
  if(typeof text!=='string'||text.length>120000||!/^\d{4}-\d{2}-\d{2}$/.test(input.date)||!['morning','afternoon','evening'].includes(input.session)||!['complete','partial'].includes(input.mode||'complete'))throw Error('invalid_scene_input');
  const date=new Date(input.date+'T12:00:00Z');if(!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==input.date)throw Error('invalid_date');
  const day=date.getUTCDay(),existing=input.existing_count??0;if(!Number.isInteger(existing)||existing<0||existing>200)throw Error('invalid_existing_count');
  const hits=[...text.matchAll(/(?:^|\n)[ \t]*(?:(\d{1,3})(男|女)[：:]|={3,}\s*(资讯助理|先生)\s*={3,})/g)];
  const errors=[],seen=new Map();let valid=0;
  const blocks=hits.map((h,i)=>{const body=text.slice(h.index+h[0].length,hits[i+1]?.index??text.length).trim();const id=h[1],who=id??h[3];
    if(!body)errors.push({code:'EMPTY_LABEL',block:i+1,speaker:who});else valid++;
    if(id){const person=data.members.find(m=>m.identity.id===id)?.identity;if(!person)errors.push({code:'INVALID_ID',block:i+1,speaker:id});else{if(person.gender!==h[2])errors.push({code:'GENDER_MISMATCH',block:i+1,speaker:id,expected:person.gender});if(Number(id)>42)errors.push({code:'INACTIVE_MEMBER',block:i+1,speaker:id});}}
    const norm=body.replace(/[\s，。！？、,.!?；;：:]/g,'');if(norm){if(seen.has(norm))errors.push({code:'EXACT_DUPLICATE',block:i+1,previous_block:seen.get(norm)});else seen.set(norm,i+1);}
    return {speaker:who,gender:h[2]??null,nonempty:!!body};});
  if(!hits.length)errors.push({code:'NO_LABELLED_CONTENT'});
  let min,max;
  if(input.session==='morning'||input.session==='evening'){min=35;max=38;}else if([1,3,5].includes(day)){min=null;max=38;}else if([2,4].includes(day)){min=null;max=39;}else{min=null;max=null;}
  const total=valid+existing;if(max!==null&&total>max)errors.push({code:'QUOTA_EXCEEDED',actual:total,max});
  if((input.mode||'complete')==='complete'&&min!==null&&total<min)errors.push({code:'QUOTA_SHORT',actual:total,min});
  return {status:errors.length?'BLOCK':'STRUCTURE_PASS',repository_commit:data.commit,label_count:hits.length,valid_count:valid,existing_count:existing,total_count:total,quota:{min,max},errors,blocks,semantic_review:'NOT_PERFORMED',news_fact_review:'NOT_PERFORMED',adopted:false};
}
export async function handleRepository(request,env,data){
  const url=new URL(request.url);
  if(url.pathname==='/internal/repository'){
    if(request.method!=='POST')return send({error:'method_not_allowed'},405);
    const payload=validateExport(await readBounded(request));
    const encoded=JSON.stringify(payload),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(encoded)))).map(x=>x.toString(16).padStart(2,'0')).join('');
    const chunks=[];for(let i=0;i<encoded.length;i+=100000)chunks.push(encoded.slice(i,i+100000));
    const stmts=chunks.map((part,i)=>env.DB.prepare('INSERT OR IGNORE INTO repository_export_chunks(export_hash,part,payload) VALUES(?,?,?)').bind(hash,i,part));
    stmts.push(env.DB.prepare('INSERT OR IGNORE INTO repository_exports(export_hash,commit_sha,payload,stored_at) VALUES(?,?,?,?)').bind(hash,payload.commit,JSON.stringify({chunk_count:chunks.length}),new Date().toISOString()));
    await env.DB.batch(stmts);
    return send({stored:true,commit:payload.commit,export_hash:hash,adopted:false},201);
  }
  if(!data)return send({status:'missing',records:[],warning:'No repository export imported.'});
  if(url.pathname==='/v1/runtime'){
    const role=url.searchParams.get('role');if(role&&!['director','writer','teacher','assistant','members'].includes(role))return send({error:'invalid_role'},400);
    return send({status:'ok',repository_commit:data.commit,exported_at:data.exported_at,rules:data.rules,skill:role?{role,text:data.skills[role]}:null,archive_dates:data.days.map(d=>d.snapshot.date||d.snapshot.story_date),latest_archive_date:data.days.at(-1)?.snapshot.date??null,warnings:['Versioned repository export; commit is not proof of a live GitHub read.','Official news images come from publisher sources; GPT must not generate substitute news photos.','No scheduler or external-message sender is enabled by this read.']});
  }
  if(url.pathname==='/v1/archive'){
    const date=url.searchParams.get('date'),page=Number(url.searchParams.get('page')||'1');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date||'')||!Number.isInteger(page)||page<1)return send({error:'invalid_archive_parameters'},400);
    const day=data.days.find(d=>(d.snapshot.date||d.snapshot.story_date)===date);if(!day)return send({status:'missing',records:[],repository_commit:data.commit});
    const messages=day.snapshot.messages||[],size=12,part=messages.slice((page-1)*size,page*size);
    return send({status:'stale',repository_commit:data.commit,source_path:day.path,source_revision:day.snapshot.source_document_revision??null,source_retrieved_at:day.snapshot.retrieved_at??null,source_status:day.snapshot.status||day.snapshot.adoption||null,date_conflict:day.snapshot.date_conflict||null,date,page,total_messages:messages.length,next_page:page*size<messages.length?page+1:null,records:part,warnings:['Dated archive, not current live document. Preserve audit flags and exclude unadopted/invalid entries.']});
  }
  if(url.pathname==='/v1/validate-scene')return send(validateScene(data,await readBounded(request,500000)));
  return null;
}

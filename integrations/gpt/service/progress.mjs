// Versioned private workspace state; drafts cannot silently replace adopted state.
const progressReply=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const progressObject=value=>!!value && typeof value==='object' && !Array.isArray(value);
function progressWorkspace(value='main') {
  if(!['main','acceptance'].includes(value))throw Error('invalid_workspace');
  return value;
}
function progressCanonical(value) {
  if(Array.isArray(value))return value.map(progressCanonical);
  if(progressObject(value))return Object.fromEntries(Object.keys(value).sort().map(key=>[key,progressCanonical(value[key])]));
  return value;
}
async function progressBody(request) {
  const reader=request.body?.getReader();
  if(!reader)throw Error('empty_body');
  const chunks=[];let length=0;
  while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>180000){await reader.cancel();throw Error('progress_too_large');}chunks.push(value);}
  const bytes=new Uint8Array(length);let pos=0;
  for(const chunk of chunks){bytes.set(chunk,pos);pos+=chunk.byteLength;}
  return JSON.parse(new TextDecoder().decode(bytes));
}
function progressRow(row) {
  return {revision:row.revision,previous_revision:row.revision-1,workspace:row.workspace,kind:row.kind,working_state:JSON.parse(row.working_state),adopted_state:JSON.parse(row.adopted_state),updated_at:row.updated_at,adoption_confirmation:row.adoption_confirmation || null};
}
export async function handleProgress(request,env) {
  const url=new URL(request.url);
  if(request.method==='GET') {
    let workspace;
    try{workspace=progressWorkspace(url.searchParams.get('workspace') || 'main');}catch(e){return progressReply({error:e.message},400);}
    const revision=url.searchParams.get('revision');
    if(revision!==null && (!/^[1-9]\d*$/.test(revision) || !Number.isSafeInteger(Number(revision))))return progressReply({error:'invalid_revision'},400);
    const row=revision===null
      ?await env.DB.prepare('SELECT * FROM progress_checkpoints WHERE workspace=? ORDER BY revision DESC LIMIT 1').bind(workspace).first()
      :await env.DB.prepare('SELECT * FROM progress_checkpoints WHERE workspace=? AND revision=?').bind(workspace,Number(revision)).first();
    if(!row)return progressReply({status:'missing',revision:0,workspace,checkpoint:null,warning:'没有已保存进度；不要猜测上一窗口内容。'});
    const recent=await env.DB.prepare('SELECT revision,kind,summary,updated_at FROM progress_checkpoints WHERE workspace=? ORDER BY revision DESC LIMIT 5').bind(workspace).all();
    return progressReply({status:'ok',revision:row.revision,workspace,checkpoint:progressRow(row),recent_revisions:recent.results,warning:'这是已保存工作状态，不是实时Google文档或完整聊天历史；日期与行情需另外核验。'});
  }
  if(request.method!=='POST')return progressReply({error:'method_not_allowed'},405);
  if(env.PROGRESS_WRITES_ENABLED!=='true')return progressReply({stored:false,error:'progress_writes_disabled'},403);
  let body,workspace;
  try {
    body=await progressBody(request);
    workspace=progressWorkspace(body.workspace || 'main');
    if(!/^[A-Za-z0-9_-]{8,128}$/.test(body.request_id || ''))throw Error('invalid_request_id');
    if(!Number.isSafeInteger(body.expected_revision) || body.expected_revision<0)throw Error('invalid_expected_revision');
    if(!['autosave','adopt','handoff'].includes(body.kind))throw Error('invalid_kind');
    if(!progressObject(body.working_state) || typeof body.working_state.summary!=='string' || !body.working_state.summary.trim() || body.working_state.summary.length>6000)throw Error('working_summary_required_max_6000');
    if(body.kind!=='adopt' && body.adopted_state!==undefined)throw Error('draft_cannot_replace_adopted_state');
    if(body.kind==='adopt' && (!progressObject(body.adopted_state) || typeof body.adoption_confirmation!=='string' || !body.adoption_confirmation.trim() || body.adoption_confirmation.length>3000))throw Error('adoption_requires_user_confirmation_and_state');
  }catch(e){return progressReply({stored:false,error:e instanceof SyntaxError?'invalid_json':e.message},400);}
  const raw=JSON.stringify(progressCanonical(body));
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw))),b=>b.toString(16).padStart(2,'0')).join('');
  const prior=await env.DB.prepare('SELECT revision,request_hash FROM progress_checkpoints WHERE workspace=? AND request_id=?').bind(workspace,body.request_id).first();
  if(prior)return progressReply(prior.request_hash===hash?{stored:true,status:'saved',revision:prior.revision,workspace,replayed:true}:{stored:false,error:'request_id_reused_with_different_payload'},prior.request_hash===hash?200:409);
  const current=await env.DB.prepare('SELECT * FROM progress_checkpoints WHERE workspace=? ORDER BY revision DESC LIMIT 1').bind(workspace).first();
  const currentRevision=current?.revision || 0;
  if(body.expected_revision!==currentRevision)return progressReply({stored:false,status:'conflict',current_revision:currentRevision,warning:'另一个窗口已更新进度；先读取最新版本再合并，禁止盲目覆盖。'},409);
  const next=currentRevision+1;
  const adopted=body.kind==='adopt'?body.adopted_state:(current?JSON.parse(current.adopted_state):{});
  if(JSON.stringify({working_state:body.working_state,adopted_state:adopted}).length>85000)return progressReply({stored:false,error:'progress_too_large',warning:'保留旧版本；不要静默截断正文。'},400);
  const confirmation=body.kind==='adopt'?body.adoption_confirmation:null;
  const created=new Date().toISOString();
  // Atomic compare-and-insert guards concurrent windows; all old rows remain recoverable.
  const result=await env.DB.prepare('INSERT INTO progress_checkpoints(workspace,revision,request_id,request_hash,kind,summary,working_state,adopted_state,adoption_confirmation,updated_at) SELECT ?,?,?,?,?,?,?,?,?,? WHERE (SELECT COALESCE(MAX(revision),0) FROM progress_checkpoints WHERE workspace=?)=?').bind(workspace,next,body.request_id,hash,body.kind,body.working_state.summary,JSON.stringify(body.working_state),JSON.stringify(adopted),confirmation,created,workspace,currentRevision).run();
  if(result.meta.changes!==1) {
    const winner=await env.DB.prepare('SELECT * FROM progress_checkpoints WHERE workspace=? ORDER BY revision DESC LIMIT 1').bind(workspace).first();
    if(winner?.request_id===body.request_id && winner.request_hash===hash)return progressReply({stored:true,status:'saved',revision:winner.revision,workspace,replayed:true});
    return progressReply({stored:false,status:'conflict',current_revision:winner?.revision || 0},409);
  }
  return progressReply({stored:true,status:'saved',revision:next,previous_revision:currentRevision,workspace,updated_at:created,adopted_changed:body.kind==='adopt'},201);
}

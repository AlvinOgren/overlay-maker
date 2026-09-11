'use strict';
const $=id=>document.getElementById(id);
const paths={upload:'M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5',layers:'m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5',play:'m8 4 12 8-12 8V4Z',pause:'M8 4v16M16 4v16',download:'M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4',clock:'M12 7v5l4 2',heart:'M2 12h5l3-8 4 16 3-8h5',bolt:'m14 2-11 12h8l-1 8L22 9h-9l1-7Z',speed:'M4 19a10 10 0 1 1 16 0M12 12l5-5',cadence:'M12 5v7l5 4',distance:'m2 18 6-12 8 12 6-12',mountain:'m2 20 8-16 6 11 3-6 3 11H2Z',temperature:'M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0Z'};
function svg(name){return '<svg viewBox="0 0 24 24" aria-hidden="true">'+(['clock','cadence'].includes(name)?'<circle cx="12" cy="12" r="9"/>':'')+'<path d="'+(paths[name]||paths.layers)+'"/></svg>';}
document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=svg(el.dataset.icon));
const state={activity:null,metrics:[],elapsed:0,playing:false,busy:false,job:null,formats:[],previewPending:false,previewRunning:false};
const token=document.querySelector('meta[name="api-token"]').content;
function fail(error){$('error').textContent=error.message||String(error);$('error').hidden=false;}
function clearError(){$('error').hidden=true;}
async function api(path,body,headers={}){
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),60000);
  try{
    const response=await fetch(path,{method:body===undefined?'GET':'POST',signal:controller.signal,headers:{'X-Overlay-Token':token,...(body===undefined?{}:{'Content-Type':body instanceof File?'application/gpx+xml':'application/json'}),...headers},body:body===undefined?undefined:body instanceof File?body:JSON.stringify(body)});
    if(!response.ok){let error;try{error=await response.json();}catch{error={error:'Servern svarade inte som väntat. Starta om appen via START.bat.'};}throw Error(error.error||'Förfrågan misslyckades.');}
    const bytes=await response.arrayBuffer();
    return new Response(bytes,{status:response.status,headers:response.headers});
  }catch(e){
    if(e.name==='AbortError')throw Error('Inläsningen tog för lång tid. Försök igen eller starta om appen via START.bat.');
    if(e instanceof TypeError)throw Error('Ingen kontakt med appen. Starta START.bat och använd sidan som öppnas. Låt terminalfönstret vara öppet.');
    throw e;
  }finally{clearTimeout(timer);}
}
function clock(t){t=Math.max(0,Math.floor(t));return [Math.floor(t/3600),Math.floor(t/60)%60,t%60].map(v=>String(v).padStart(2,'0')).join(':');}
function seconds(text){if(!/^\d+:\d{2}:\d{2}(?:\.\d+)?$/.test(text.trim()))throw Error('Ange tiden som hh:mm:ss.');const [h,m,s]=text.split(':').map(Number);if(m>=60||s>=60)throw Error('Minuter och sekunder måste vara under 60.');return h*3600+m*60+s;}
function config(){
  if(!state.activity)throw Error('Välj en GPX-fil först.');
  const cfg={activity:state.activity.id,metrics:[...state.metrics],elapsed:state.elapsed};
  for(const id of ['layout','size','format','accent'])cfg[id]=$(id).value;
  for(const id of ['icons','outline'])cfg[id]=$(id).checked;
  cfg.fps=Number($('fps').value);cfg.start=seconds($('start').value);cfg.end=seconds($('end').value);
  if(!cfg.metrics.length)throw Error('Välj minst ett mätvärde.');
  if(!(cfg.start>=0&&cfg.end>cfg.start&&cfg.end<=state.activity.duration))throw Error('Välj ett utsnitt inom aktiviteten med slutet efter starten.');
  return cfg;
}
function updateSummary(){
  $('selected-count').textContent=state.metrics.length+' valda';
  $('accent-label').textContent=$('accent').value.toUpperCase();
  const opaque=$('format').value==='mp4';
  $('background-controls').hidden=opaque;
  $('preview-caption-text').textContent=opaque?'MP4 har svart bakgrund. Videoytan anpassas runt dina mätvärden.':'Videon har transparens. Förhandsvisningens bakgrund följer inte med.';
  $('preview-stage').className='preview-stage '+(opaque?'dark':document.querySelector('[data-background].active').dataset.background);
  try{const c=config(),n=Math.ceil((c.end-c.start)*c.fps);$('clip-duration').textContent=clock(n/c.fps);$('frame-summary').textContent=n.toLocaleString('sv-SE')+' bildrutor · '+c.fps+' fps';$('export-button').disabled=state.busy||!state.formats.includes(c.format);}
  catch(e){$('clip-duration').textContent='—';$('frame-summary').textContent=state.activity?e.message:'Ladda upp en GPX-fil för att fortsätta.';$('export-button').disabled=true;}
}
function metricsUI(){
  $('metrics').replaceChildren();
  const definitions=state.activity?.metrics||{speed:{label:'Hastighet',unit:'km/h',icon:'speed'},hr:{label:'Puls',unit:'bpm',icon:'heart'},power:{label:'Effekt',unit:'W',icon:'bolt'},cad:{label:'Kadens',unit:'rpm',icon:'cadence'},elapsed:{label:'Elapsed time',unit:'',icon:'clock'}};
  for(const [key,meta]of Object.entries(definitions)){
    const label=document.createElement('label');label.className='metric'+(!meta.available?' unavailable':'');
    const input=document.createElement('input');input.type='checkbox';input.checked=state.metrics.includes(key);input.disabled=!meta.available;
    input.addEventListener('change',()=>{state.metrics=input.checked?[...state.metrics,key]:state.metrics.filter(k=>k!==key);updateSummary();requestPreview();});
    const pict=document.createElement('span');pict.innerHTML=svg(meta.icon);
    const name=document.createElement('span');name.className='metric-name';name.textContent=meta.label;
    if(state.activity){const small=document.createElement('small');small.textContent=!meta.available?'Saknas i filen':meta.derived?'Beräknat från GPX':meta.count<meta.total?'Saknas vid '+(meta.total-meta.count)+' punkter':'Finns i filen';name.append(small);}
    const unit=document.createElement('span');unit.className='metric-unit';unit.textContent=meta.unit;
    label.append(input,pict,name,unit);$('metrics').append(label);
  }
}
let previewURL=null, previewTimer=null, uploadSerial=0;
function requestPreview(){$('canvas-label').textContent='Beräknar videoyta…';state.previewPending=true;clearTimeout(previewTimer);previewTimer=setTimeout(preview,110);}
async function preview(){
  if(state.previewRunning||!state.previewPending||!state.activity)return;
  let cfg;try{cfg=config();}catch{return;}
  state.previewPending=false;state.previewRunning=true;$('preview-loading').hidden=false;
  const serial=uploadSerial;
  try{const response=await api('/api/preview',cfg),blob=await response.blob();if(serial!==uploadSerial)return;
    $('canvas-label').textContent=response.headers.get('X-Overlay-Width')+' × '+response.headers.get('X-Overlay-Height')+' px · beskuren';
    const url=URL.createObjectURL(blob);$('preview-image').src=url;$('preview-image').hidden=false;$('preview-empty').hidden=true;
    if(previewURL)URL.revokeObjectURL(previewURL);previewURL=url;
  }catch(e){if(serial===uploadSerial)fail(e);}finally{state.previewRunning=false;$('preview-loading').hidden=true;if(state.previewPending)requestPreview();}
}
function seek(t){state.elapsed=Math.min(state.activity.duration,Math.max(0,t));$('scrubber').value=state.elapsed;$('current-time').textContent=clock(state.elapsed);requestPreview();}
function stop(){state.playing=false;$('play').innerHTML=svg('play');$('play').setAttribute('aria-label','Spela förhandsvisning');}
async function upload(file){
  if(!file)return;clearError();stop();const serial=++uploadSerial;
  state.activity=null;state.metrics=[];state.previewPending=false;clearTimeout(previewTimer);
  for(const id of ['controls','export-controls','play','scrubber'])$(id).disabled=true;
  $('preview-image').hidden=true;$('preview-empty').hidden=false;
  $('activity-summary').hidden=true;$('data-notes').hidden=true;
  $('file-title').textContent=file.name;$('file-description').textContent='Läser och kontrollerar GPX-filen…';
  setUploadStatus('loading','Läser filen…',file.name+' · '+(file.size/1024/1024).toFixed(1)+' MB');
  metricsUI();updateSummary();
  try{
    if(!file.size)throw Error('Filen är tom. Välj en GPX-fil med mätpunkter.');
    if(file.size>20*1024*1024)throw Error('Filen är för stor. Maxstorleken är 20 MB.');
    const a=await(await api('/api/activity',file,{'X-Filename':encodeURIComponent(file.name)})).json();if(serial!==uploadSerial)return;
    state.activity=a;state.metrics=['speed','hr','power','cad','elapsed'].filter(k=>a.metrics[k].available);
    $('file-title').textContent=a.name;$('file-description').textContent='Byt aktivitet genom att släppa en ny fil';
    const summary=$('activity-summary');summary.replaceChildren();summary.hidden=false;
    for(const [label,value]of [['TID',clock(a.duration)],['DISTANS',a.distance.toFixed(1)+' km'],['PUNKTER',a.count.toLocaleString('sv-SE')]]){const el=document.createElement('span');el.textContent=label;const strong=document.createElement('strong');strong.textContent=value;el.append(strong);summary.append(el);}
    $('warnings').replaceChildren();
    const notes=['Hastighet och distans beräknas från GPS. Distans över långa luckor räknas inte med. Sensorvärden interpoleras mellan närliggande punkter.',...a.warnings];
    for(const text of notes){const p=document.createElement('p');p.textContent=text;$('warnings').append(p);}
    $('data-notes').hidden=false;$('controls').disabled=false;$('export-controls').disabled=false;$('play').disabled=false;$('scrubber').disabled=false;
    $('scrubber').max=a.duration;$('total-time').textContent=clock(a.duration);$('start').value='00:00:00';$('end').value=clock(Math.min(a.duration,10));
    if(a.duration<1)$('end').value='00:00:00.'+String(Math.round(a.duration*1000)).padStart(3,'0');
    metricsUI();updateSummary();seek(0);
    setUploadStatus('success','✓ Filen är inläst',a.name+' · '+a.count.toLocaleString('sv-SE')+' mätpunkter · '+clock(a.duration)+'. Välj mätvärden nedan.');
  }catch(e){if(serial!==uploadSerial)return;fail(e);setUploadStatus('error','Filen kunde inte läsas in',e.message);$('file-description').textContent='Klicka för att välja fil igen · max 20 MB';}
  finally{if(serial===uploadSerial)$('file').value='';}
}
function setUploadStatus(kind,title,detail){
  $('upload-status').hidden=false;$('upload-status').className='upload-status '+kind;
  $('upload-status-title').textContent=title;$('upload-status-detail').textContent=detail;
  $('dropzone').dataset.state=kind;$('dropzone').setAttribute('aria-busy',String(kind==='loading'));
}
$('file').addEventListener('change',()=>upload($('file').files[0]));
$('dropzone').addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();$('file').click();}});
for(const event of ['dragenter','dragover'])$('dropzone').addEventListener(event,e=>{e.preventDefault();$('dropzone').classList.add('drag');});
for(const event of ['dragleave','drop'])$('dropzone').addEventListener(event,e=>{e.preventDefault();$('dropzone').classList.remove('drag');if(event==='drop')upload(e.dataTransfer.files[0]);});
for(const id of ['layout','size','format','accent','fps','icons','outline','start','end'])$(id).addEventListener('input',()=>{updateSummary();requestPreview();});
$('scrubber').addEventListener('input',()=>seek(Number($('scrubber').value)));
$('full-range').addEventListener('click',()=>{if(!state.activity)return;$('start').value='00:00:00';$('end').value=clock(state.activity.duration);updateSummary();requestPreview();});
$('play').addEventListener('click',()=>{if(state.playing){stop();return;}if(state.elapsed>=state.activity.duration)seek(0);state.playing=true;$('play').innerHTML=svg('pause');$('play').setAttribute('aria-label','Pausa förhandsvisning');});
setInterval(()=>{if(state.playing&&state.activity){seek(state.elapsed+.5);if(state.elapsed>=state.activity.duration)stop();}},500);
document.querySelectorAll('[data-background]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('[data-background]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});$('preview-stage').className='preview-stage '+button.dataset.background;}));
async function poll(){
  if(!state.job)return;
  try{const j=await(await api('/api/jobs/'+state.job)).json();$('job-progress').value=j.progress;$('job-detail').textContent=Math.round(j.progress)+' % · '+j.seconds+' s';
    if(j.state==='running'){setTimeout(poll,1000);return;}
    state.busy=false;$('cancel').hidden=true;updateSummary();
    $('job-title').textContent={done:'Din overlay är klar',cancelled:'Exporten avbröts',failed:'Exporten misslyckades'}[j.state]||j.state;
    if(j.state==='done'){$('download').href=j.download;$('download').hidden=false;$('job-detail').textContent='Sparad i exports · '+j.seconds+' s';}
    if(j.state==='failed')fail(Error(j.error));
  }catch(e){fail(e);$('job-detail').textContent='Anslutningen bröts. Försöker igen…';setTimeout(poll,3000);}
}
async function startExport(){
  clearError();const cfg=config();if(state.busy)throw Error('En export pågår redan.');stop();
  state.busy=true;updateSummary();
  try{const j=await(await api('/api/export',cfg)).json();state.job=j.id;$('job').hidden=false;$('job-title').textContent='Skapar video…';$('job-progress').value=0;$('cancel').hidden=false;$('cancel').disabled=false;$('download').hidden=true;poll();return j;}
  catch(e){state.busy=false;updateSummary();throw e;}
}
$('export-button').addEventListener('click',()=>startExport().catch(fail));
$('cancel').addEventListener('click',async()=>{try{$('cancel').disabled=true;await api('/api/jobs/'+state.job+'/cancel',{});}catch(e){fail(e);$('cancel').disabled=false;}});
$('help-button').addEventListener('click',()=>$('help').showModal());$('close-help').addEventListener('click',()=>$('help').close());
metricsUI();updateSummary();
if(location.protocol==='file:'||token==='__API_TOKEN__'){
  $('startup-status').textContent='Appen behöver startas via START.bat. Stäng den här fliken och använd sidan som öppnas automatiskt.';
}else{
  $('startup-status').hidden=true;$('file').disabled=false;
}
api('/api/health').then(r=>r.json()).then(data=>{state.formats=data.formats;for(const option of $('format').options)option.disabled=!data.formats.includes(option.value);if(!data.formats.includes($('format').value)&&data.formats.length)$('format').value=data.formats[0];if(!data.formats.length)fail(Error('Ingen videokodare hittades. Starta appen via START.bat för att installera beroenden.'));updateSummary();}).catch(fail);
const modelContext=document.modelContext;
if(modelContext?.registerTool){
  const lifecycle=new AbortController();
  window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
  const definitions=[
    {name:'read_overlay_activity',description:'Read the uploaded activity and current overlay settings.',annotations:{readOnlyHint:true,untrustedContentHint:true},inputSchema:{type:'object',properties:{},additionalProperties:false},execute:async()=>({activity:state.activity,selected:state.metrics,elapsed:state.elapsed})},
    {name:'configure_overlay_metrics',description:'Select available metrics and update the visible overlay preview.',annotations:{readOnlyHint:false,untrustedContentHint:false},inputSchema:{type:'object',properties:{metrics:{type:'array',items:{type:'string'},minItems:1,uniqueItems:true}},required:['metrics'],additionalProperties:false},execute:async input=>{
      if(!state.activity||!Array.isArray(input.metrics)||!input.metrics.length||input.metrics.some(k=>!state.activity.metrics[k]?.available))throw Error('Select available metrics from an uploaded activity.');
      state.metrics=[...new Set(input.metrics)];metricsUI();updateSummary();requestPreview();return {selected:state.metrics,preview:'updating'};
    }},
    {name:'start_overlay_export',description:'Start rendering the current selection to a local cropped video file. Returns a job ID; rendering continues in the visible export panel.',annotations:{readOnlyHint:false,untrustedContentHint:false},inputSchema:{type:'object',properties:{},additionalProperties:false},execute:async()=>startExport()}
  ];
  for(const definition of definitions){try{Promise.resolve(modelContext.registerTool(definition,{signal:lifecycle.signal})).catch(()=>{});}catch{}}
}

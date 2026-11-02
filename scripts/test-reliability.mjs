import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { deflateSync } from 'node:zlib';

const file = new URL('../src/app.html', import.meta.url);
const src = fs.readFileSync(file, 'utf8');
function cut(a, b) {
  const i = src.indexOf(a), j = src.indexOf(b, i + a.length);
  assert(i >= 0 && j > i, `Source boundaries: ${a} -> ${b}`);
  return src.slice(i, j);
}
function line(a) {
  return src.split('\n').find(s => s.startsWith(a));
}
function ctx(extra = {}) {
  return vm.createContext({ console, Blob, Uint8Array, TextEncoder, TextDecoder, URL,
    crypto: webcrypto, setTimeout, clearTimeout, structuredClone,document:{addEventListener(){}}, ...extra });
}
const run = (c, code) => vm.runInContext(code, c, { filename: 'extracted-app.js' });
const results = [];
function record(name, evidence) { results.push({ name, evidence }); }
const doc = () => ({ kind:'body', name:'original', trimW:148, trimH:210, bleed:3,
  binding:'right', color:'mono', margins:{top:15,bottom:15,inner:15,outer:12},
  nombre:{mode:'none',start:1,size:8,font:'Noto Sans JP',offset:8},
  pages:[{id:'p1',items:[]}] });
const pw = cut('function pw(d)', '\nfunction isLeft');
const load = cut('function validateProject(p)', '\nlet dlCap');

// Compile the real script blocks; this does not execute a browser.
const scripts = [...src.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)];
scripts.forEach((m, i) => new vm.Script(m[1], {filename:`app-script-${i}.js`}));
record('script_syntax', { compiledScriptBlocks:scripts.length });

// Paper text editing: exercise the actual input, keydown and blur callbacks.
{
  const listeners = {};
  const textarea = { style:{}, value:'', addEventListener:(k,fn)=>listeners[k]=fn,
    focus(){}, remove(){}, blur(){ listeners.blur?.(); } };
  const it = {type:'text',text:'before',x:0,y:0,w:10,h:10,size:9,leading:175,track:0,dir:'v'};
  let commits = 0, dirtyCalls = 0, saves = 0, scheduled = 0;
  const c = ctx({ S:{doc:{bleed:3},s:1,pageEls:[{el:{append(){}}}]},
    document:{createElement:()=>textarea}, styled:x=>x,headOf:x=>x,chainOf:x=>[x],
    FF:()=>'',cmykCss:()=>'',PT:25.4/72,dirty:()=>dirtyCalls++,dirtyAll(){},
    commit:()=>commits++,saveProject:()=>saves++,scheduleSave:()=>scheduled++,renderProps(){},runPreflight(){} });
  run(c,cut('function editText(pi,it)', '\nfunction decodeText'));
  c.it = it;
  run(c,'editText(0,it)');
  textarea.value = 'unsaved new text'; listeners.input();
  assert.equal(it.text,'unsaved new text'); assert.equal(commits,0);
  let stopped=false, prevented=false;
  listeners.keydown({key:'s',ctrlKey:true,metaKey:false,
    stopPropagation(){stopped=true;},preventDefault(){prevented=true;}});
  assert(stopped && prevented);assert.equal(saves,1);assert.equal(scheduled,1);
  record('inline_text_save', { commitsDuringInput:commits,dirtyCalls,
    ctrlSPropagationStopped:stopped,ctrlSDefaultPrevented:prevented });
  listeners.blur(); assert.equal(commits,2);
}

// Storage failures must be reported to the caller and the user.
{
  let notified=false;const c=ctx({kvWrite:async()=>{throw new Error('QuotaExceededError');},toast:()=>{notified=true}});
  run(c,cut('async function kvSet(k,v)', '\nasync function kvGet'));
  const result=await run(c,"kvSet('project',{name:'test'})");
  assert.equal(result,false);assert(notified);
  record('storage_failure', {rejects:false,result:String(result)});
}

// Malformed import: use the actual loadProject, fitZoom, spreadsOf and rebuild.
{
  const original=doc(), bad={...doc()}; delete bad.pages;
  const blank={innerHTML:'',style:{setProperty(){}}};
  const c=ctx({S:{doc:original,images:{old:{src:'old'}},media:{old:{}},zoom:1,
    single:false,visible:new Set(),dirty:new Set(),tdirty:new Set()},
    kvGet:async()=>null,migrateSlides(){},stage:{clientHeight:700,clientWidth:900},
    PX:96/25.4,clamp:(v,a,b)=>Math.max(a,Math.min(b,v)),stopInline(){},
    io:{disconnect(){}},spreadsEl:blank,pagesEl:{innerHTML:''},lcache:new Map(),
    thumbH:()=>64,isFlat:()=>false, renderAll(){},resetHistory(){} });
  run(c,pw+cut('function spreadsOf(d)', '\nconst io=')+
    cut('function rebuild()', '\nfunction updateInfo')+
    cut('function fitZoom()', "\n$('#bZi')")+load);
  c.input={app:'honhon',doc:bad};
  let error=''; try {await run(c,'loadProject(input)');} catch(e) {error=e.message;}
  assert(error); assert.equal(c.S.doc,original); assert.equal(Object.keys(c.S.images).length,1);
  record('invalid_import_state', {error,originalDocumentRestored:c.S.doc===original,
    imagesRemaining:Object.keys(c.S.images).length});
}

// The current document and its images must remain intact during image decoding.
{
  const original=doc(); original.pages[0].items=[{type:'image',imageId:'old',x:0,y:0,w:10,h:10}];
  const incoming=doc();incoming.name='incoming';incoming.pages[0].items=[{type:'image',imageId:'new',x:0,y:0,w:10,h:10}];
  let release; let saved;
  const c=ctx({S:{doc:original,images:{old:{src:'old',w:10,h:10}},media:{}},
    SL:()=>c.S.doc.pages,MS:()=>[],loadImg:()=>new Promise(r=>release=r),
    kvWrite:async(k,v)=>{saved=structuredClone(v)},kvGet:async()=>null,saveQueue:Promise.resolve(),saveT:0,saveRevision:0,saveStatus(){},toast(){},commitT:0,docT:0,
    migrateSlides(){},fitZoom(){},rebuild(){},renderAll(){},resetHistory(){} });
  run(c,cut('function projectData(file)', '\nfunction validateProject')+load);
  c.input={app:'honhon',doc:incoming,images:{new:{src:'new',w:10,h:10}}};
  const loading=run(c,'loadProject(input)');
  await run(c,'autosave()');
  assert.equal(saved.doc.name,'original');assert.equal(saved.doc.pages[0].items[0].imageId,'old');
  assert.deepEqual(Object.keys(saved.images),['old']);
  record('import_autosave_race',{savedDocument:saved.doc.name,
    referencedImage:saved.doc.pages[0].items[0].imageId,savedImages:Object.keys(saved.images)});
  release({});await loading;
}

// Generate real colophon elements and inspect their text, without rendering them.
{
  const c=ctx({S:{doc:doc()},PT:25.4/72,r1:v=>Math.round(v*10)/10,
    uid:()=>Math.random().toString(36),gAdv:s=>String(s).length*3});
  run(c,cut('function textItem(o)', '\nfunction videoItem')+
    line('const GK=')+'\n'+cut('function gT(kind,o)', '\nfunction tocRowH')+
    cut('function colRows(g,o)', '\nfunction tocAuto'));
  c.g={m:{x:15,y:15,w:120,h:180},font:['Noto Sans JP','Noto Sans JP'],
    title:'Test',rows:[{label:'Author',value:'Alice'},{label:'Date',value:'2026'}],L:true};
  const out=run(c,"['center','ctrrule','min'].map(k=>({design:k,text:COL_DESIGNS[k].make(g).find(x=>x.text?.includes('Alice')).text}))");
  for(const o of out){assert(o.text.includes('\n'));assert(!o.text.includes('\\n'));}
  record('colophon_linebreaks',Array.from(out));
}

// Export must wait for pending images; an image that cannot be decoded is reported and left as an empty frame.
{
  let imageDraws=0;
  const drawing={setTransform(){},fillRect(){},save(){},restore(){},beginPath(){},rect(){},clip(){},
    drawImage(){imageDraws++},getImageData:(x,y,w,h)=>({data:new Uint8Array(w*h*4).fill(255)})};
  const d=doc();d.kind='slide';d.trimW=10;d.trimH=10;d.bleed=0;
  d.pages[0].items=[{type:'image',imageId:'photo',x:0,y:0,w:10,h:10,fit:'contain'}];
  const c=ctx({S:{doc:d,images:{photo:{pending:true,w:10,h:10}}},
    document:{createElement:()=>({getContext:()=>drawing}),fonts:{load:async()=>[],ready:Promise.resolve()}},
    FF:x=>x,wcache:new Map(),lcache:new Map(),sepCache:new Map(),exporting:false,
    SL:()=>d.pages,MS:()=>[],loadPendingImages:async()=>{c.S.images.photo={pending:false,w:10,h:10,img:{}}},mBg:()=>({}),mUnder:()=>[],nombreText:i=>String(i+1),sepCanvas:()=>({}),exportNames:()=>({one:'audit',page:()=> 'audit'}),
    deflate:async u=>new Uint8Array(deflateSync(u)),enc:new TextEncoder(),MMPT:72/25.4});
  run(c,pw+cut('function imgScale(it,im)', '\nfunction effPpi')+
    cut('function drawItem(ctx,it,ch,preview)', '\nfunction nombreText')+
    cut('function drawNombre(ctx,i,ch)', '\nfunction drawGuides')+
    cut('function drawPage(ctx,i,o)', '\nfunction drawMarks')+
    cut('function pdfStr(s)', '\nasync function ensureFonts')+
    cut('async function ensureFonts()', '\nfunction pdfFrom')+
    cut('function pdfFrom(pages,title)', '\nasync function exportPDF'));
  const out=await run(c,"exportJob({fmt:'pdf',dpi:25.4,range:[0],base:'audit'},()=>{})");
  assert(out.blob.size>0);assert(imageDraws>0);assert(!c.S.images.photo.pending);
  record('pending_image_pdf',{pdfBytes:out.blob.size,imageDraws,pending:c.S.images.photo.pending});
  let notice='';c.toast=m=>{notice=m};
  c.loadPendingImages=async()=>{c.S.images.photo={failed:true}};
  await run(c,"exportJob({fmt:'pdf',dpi:25.4,range:[0],base:'audit'},()=>{})");assert.match(notice,/読み込めない画像 1件/);
  c.loadPendingImages=async()=>{};c.S.images.photo={pending:true,w:10,h:10};
  await assert.rejects(run(c,"exportJob({fmt:'pdf',dpi:25.4,range:[0],base:'audit'},()=>{})"),/読み込みが終わっていません/);
}

// Imported numeric values must never introduce markup in the inspector.
{
  const d=doc();d.nombre.size='8\"><span data-review-probe="injected"></span><input value="';
  const fields=new Map();const $=s=>{if(!fields.has(s))fields.set(s,{});return fields.get(s)};
  const c=ctx({S:{doc:d,tab:'doc'},$,PR:()=>({}),PRINTERS:{generic:{name:'None'}},
    isFlat:()=>false,FSEL:()=>'<select></select>'});
  run(c,line('const esc=')+'\n'+line('const F=')+'\n'+cut('function renderDoc()', '\nfunction spineOf'));
  run(c,'renderDoc()');
  const html=fields.get('#tab-doc').innerHTML;
  assert(!html.includes('<span data-review-probe="injected"></span>'));assert(html.includes('&lt;span'));
  record('imported_html_injection',{markerInsertedAsMarkup:false,scriptExecutionTested:false});
}

// Reject malformed numeric data before touching the current project.
{
  const c=ctx();run(c,cut('function validateProject(p)', '\nasync function loadProject'));
  const valid=doc();valid.pages[0].items=[{type:'text',x:0,y:0,w:20,h:20,text:'<plain text>',size:9}];
  c.input={app:'honhon',doc:valid};run(c,'validateProject(input)');
  for(const bad of ['8\"><span>test</span>',Infinity,NaN]){
    c.input=structuredClone({app:'honhon',doc:valid});c.input.doc.nombre.size=bad;
    assert.throws(()=>run(c,'validateProject(input)'),/ページ番号/);
  }
  c.input=structuredClone({app:'honhon',doc:valid});c.input.doc.pages[0].items[0].size='9';
  assert.throws(()=>run(c,'validateProject(input)'),/数値項目/);
  record('project_validation',{validAccepted:true,invalidNumbersRejected:true});
}

// Recovery snapshots must include original PPTX bytes and be independent of edits.
{
  const current=doc();current.pages[0].items=[{type:'rect',x:0,y:0,w:20,h:20}];
  const originalFile=new Blob(['original-pptx']);let snapshot;
  const c=ctx({S:{doc:current,pptxSrc:originalFile},SL:()=>current.pages,
    projectData:()=>({app:'honhon',doc:current}),kvWrite:async(k,v)=>{assert.equal(k,'previousProject');snapshot=v}});
  run(c,cut('async function backupBeforeSwitch()', '\nconst switchBypass'));
  await run(c,'backupBeforeSwitch()');current.name='changed';
  assert.equal(snapshot.doc.name,'original');assert.equal(await snapshot.pptxSrc.text(),'original-pptx');
  record('recovery_snapshot',{independent:true,pptxPreserved:true});
}

// A view rebuild failure preserves the original document; an undecodable image opens the document without that image.
{
  for(const failure of ['image','view']){
    const original=doc(),originalImages={old:{src:'old'}};let builds=0;
    const incoming=doc();incoming.name='incoming';
    const c=ctx({S:{doc:original,images:originalImages,media:{}},commitT:0,docT:0,saveT:0,
      kvGet:async()=>null,loadImg:async()=>{throw new Error('decode failed')},
      migrateSlides(){},fitZoom(){},rebuild(){if(++builds===1)throw new Error('view failed')},
      renderAll(){},resetHistory(){},scheduleSave(){}});
    run(c,load);c.input={app:'honhon',doc:incoming,images:failure==='image'?{broken:{src:'bad'}}:{}};
    if(failure==='image'){let notice='';c.toast=m=>{notice=m};builds=1;await run(c,'loadProject(input)');assert.equal(c.S.doc.name,'incoming');assert(!c.S.images.broken);assert.match(notice,/読み込めない画像が1件/);continue}
    await assert.rejects(run(c,'loadProject(input)'),/failed/);
    assert.equal(c.S.doc,original);assert.equal(c.S.images,originalImages);
  }
  record('import_rollback',{imageFailureOpensWithoutImage:true,viewFailurePreservesProject:true});
}

// Snapshot writes are serialized: an older save cannot overwrite a newer save.
{
  let release;const writes=[];let generation=1;
  const c=ctx({S:{doc:doc()},saveT:0,saveRevision:0,saveQueue:Promise.resolve(),saveStatus(){},toast(){},
    projectData:()=>({generation}),kvWrite:async(k,v)=>{writes.push(v.generation);if(v.generation===1)await new Promise(r=>release=r)}});
  run(c,cut('function autosave()', '\nfunction validateProject'));
  const first=run(c,'autosave()');await Promise.resolve();generation=2;const second=run(c,'autosave()');
  await Promise.resolve();assert.deepEqual(writes,[1]);release();await Promise.all([first,second]);assert.deepEqual(writes,[1,2]);
  record('save_ordering',{writes});
}


console.log(JSON.stringify(results,null,2));

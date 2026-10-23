import assert from 'node:assert/strict';
// Run against a local Flask server and Chrome launched with remote debugging.
// APP_URL defaults to port 5055; CHROME_CDP_URL defaults to port 9228.
const appUrl=process.env.APP_URL || 'http://127.0.0.1:5055';
const chromeUrl=process.env.CHROME_CDP_URL || 'http://127.0.0.1:9228';
const target=await(await fetch(`${chromeUrl}/json/new?about:blank`,{method:'PUT'})).json();
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
let sequence=0; const jobs=new Map(),errors=[];
socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const job=jobs.get(m.id);jobs.delete(m.id);m.error?job.reject(Error(JSON.stringify(m.error))):job.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);});
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;jobs.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression:`(async()=>{return (${expression});})()`,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function until(expression){for(let i=0;i<200;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out: '+expression);}
async function click(selector){await until(`!!document.querySelector(${JSON.stringify(selector)})`);await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
try {
 await send('Runtime.enable'); await send('Page.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
 await send('Page.addScriptToEvaluateOnNewDocument',{source:"sessionStorage.setItem('bipol_session_initialized','true')"});
 await send('Page.navigate',{url:appUrl});
 await until('typeof currentResults!=="undefined"&&currentResults!==null&&!document.querySelector("#calcBtn").disabled');
 await evaluate('(async()=>{const presets=await(await fetch("/api/presets")).json();loadProjectIntoForm({name:"Audyt projektanta",params:presets.ga_trainer});await performCalculation();return true})()');
 await click('[data-studio-nav="tab-trends"]');
 await until('document.querySelector("[data-sugg-key=me_m0]")');
 const before=await evaluate('currentResults.mass.m0');
 await click('[data-sugg-key="me_m0"]');
 await until('currentResults.mass.empty_mass_model==="fixed_fraction"&&!document.querySelector("#calcBtn").disabled');
 assert.notEqual(await evaluate('currentResults.mass.m0'),before);
 assert.ok(await evaluate('Math.abs(currentResults.mass.empty_fraction-currentResults.params.empty_mass_fraction)<.0001'));
 await click('#trendResetMassModel');
 await until('currentResults.mass.empty_mass_model==="class_correlation"&&!document.querySelector("#calcBtn").disabled');
 await click('[data-sugg-key="vh"]');
 await until('!document.querySelector("#calcBtn").disabled');
 await click('[data-sugg-key="ws"]');
 await until('currentResults.params.wing_input_mode==="area_aspect"&&!document.querySelector("#calcBtn").disabled');
 assert.ok(await evaluate('currentResults.params.wing_area_m2>0'));
 await click('[data-sugg-key="pw"]');
 await until('currentResults.params.power_input_mode==="fixed"&&!document.querySelector("#calcBtn").disabled');
 assert.equal(await evaluate('currentResults.sizing.design_point.power_kw===currentResults.params.engine_power_kw'),true);
 await evaluate('(async()=>{document.querySelector("#engine_power_kw").value="0.001";await performCalculation();return true})()');
 await until('currentResults.sizing.design_point.power_kw===.001');
 assert.equal(await evaluate('currentResults.performance.level_flight_available_sl'),false);
 assert.ok(await evaluate('currentResults.compliance_checks.some(c=>c.parameter.startsWith("Lot poziomy")&&!c.passed)'));
 assert.equal(await evaluate('currentResults.performance.paturski_p6.range_endurance_6_5.range_at_requested_speed_km'),null);
 assert.ok(await evaluate('currentResults.bipol_projects.p5.recommendations.includes("nie spełnia")'));
 assert.equal(await evaluate('document.querySelector("#p5_range_tbody").textContent.includes("null")'),false);
 const report=await evaluate('(async()=>{const r=await fetch("/report/project/p3",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(currentResults.params)});return {status:r.status,html:await r.text()}})()');
 assert.equal(report.status,200); assert.ok(report.html.includes('Brak zweryfikowanych rzędnych'));
 await evaluate('(async()=>{const topics=(await(await fetch("/api/topics")).json()).topics;loadProjectIntoForm({name:"Temat 82 — audyt",params:topics.find(t=>t.num===82).parameters});await performCalculation();return true})()');
 assert.equal(await evaluate('currentResults.params.v_stall_kmh'),140);
 assert.ok(await evaluate('currentResults.geometry.wing.b<50'));
 for(const width of [1600,390,320]) {
   await send('Emulation.setDeviceMetricsOverride',{width,height:1100,deviceScaleFactor:1,mobile:false});
   await click('[data-studio-nav="tab-overview"]');
   await new Promise(r=>setTimeout(r,250));
   assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'));
 }
 await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
 assert.deepEqual(errors,[]);
 console.log('PASS: real UI adoption (mass, VH, area, power), inadequate propulsion, P3 report, topic82, responsive views; no JS exceptions.');
} finally {await send('Page.close');socket.close();}

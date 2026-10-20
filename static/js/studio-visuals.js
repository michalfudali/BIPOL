/* Wizualizacje zaadaptowane z załączonego BIPOL_Studio, bez zależności od jego silnika. */
(function (root) {
'use strict';
const {format: fmt, escape: esc} = root.BipolStudio;
const COLORS = ['#168c83', '#667ed5', '#d89b45', '#bf728e', '#65a4c3'];
function icon(name,size=20){const paths={plane:'M22 2 9.5 14.5M22 2l-7 20-4-9-9-4 20-7Z',grid:'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z',target:'M20 11.1V12a8 8 0 1 1-4.8-7.3M20 4l-8 8-3-3',wing:'M3 15 21 5l-5 13-6-4-7 1Z',chart:'M3 3v18h18M6 15l5-5 4 3 6-8',layers:'m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5',shield:'M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7l-9-4Zm-4 9 3 3 5-6',file:'M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8M8 16h8',book:'M3 4h6c2 0 3 1 3 2 0-1 1-2 3-2h6v16h-6c-2 0-3 1-3 2 0-1-1-2-3-2H3V4Zm9 2v16',save:'M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2ZM7 3v6h10V3M7 21v-8h10v8',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',plus:'M12 5v14M5 12h14',chevron:'m9 5 7 7-7 7',arrow:'M5 12h14m-5-5 5 5-5 5',check:'m5 12 4 4L19 6',warn:'m12 3 10 18H2L12 3Zm0 6v5m0 3v.01',close:'m6 6 12 12M6 18 18 6',upload:'M12 16V4m-5 5 5-5 5 5M4 17v4h16v-4',compare:'M8 3v18M16 3v18M3 7h10M11 17h10',settings:'M4 6h16M4 18h16M8 3v6M16 15v6M4 12h16M12 9v6',clock:'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',external:'M15 3h6v6m0-6L10 14M11 3H3v18h18v-8',menu:'M3 6h18M3 12h18M3 18h18',glider:'M2 12h20M12 3v18m-4-2h8',drone:'M8 8h8v8H8Zm-5-5 5 5m8 8 5 5M3 21l5-5M16 8l5-5M1 3h4M19 3h4M1 21h4m14 0h4',refresh:'M20 7a9 9 0 1 0 1 9M20 2v6h-6',info:'M12 11v6m0-10v.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7',edit:'m16 3 5 5-12 12-6 1 1-6L16 3Z'};
 return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.plane}"/></svg>`;}
function chart({series,xLabel='',yLabel='',width=640,height=270,xMin,xMax,yMin,yMax,vertical=[],points=[],shade=false,title=''}){
 const all=series.flatMap(s=>s.data.filter(p=>p&&Number.isFinite(p[0])&&Number.isFinite(p[1])));if(!all.length)return '<p class="empty">Brak danych do wykresu.</p>';
 xMin=xMin??Math.min(...all.map(p=>p[0]));xMax=xMax??Math.max(...all.map(p=>p[0]));yMin=yMin??Math.min(0,...all.map(p=>p[1]));yMax=yMax??Math.max(...all.map(p=>p[1]))*1.1;
 if(xMax===xMin)xMax=xMin+1;if(yMax===yMin)yMax=yMin+1;
 const l=66,r=20,t=22,b=49,w=width-l-r,h=height-t-b,X=x=>l+(x-xMin)/(xMax-xMin)*w,Y=y=>t+h-(y-yMin)/(yMax-yMin)*h;
 let out=`<svg class="plot" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title||`${yLabel} w funkcji ${xLabel}`)}"><title>${esc(title||`${yLabel} w funkcji ${xLabel}`)}</title><defs><clipPath id="clip-${esc(title.replace(/[^a-z0-9]/gi,''))}"><rect x="${l}" y="${t}" width="${w}" height="${h}"/></clipPath></defs>`;
 for(let i=0;i<=5;i++){const x=xMin+(xMax-xMin)*i/5,y=yMin+(yMax-yMin)*i/5;out+=`<path d="M${X(x)} ${t}V${t+h}M${l} ${Y(y)}H${width-r}" stroke="#e7ecef" stroke-dasharray="3 4"/><text x="${X(x)}" y="${height-b+22}" text-anchor="middle" class="axis">${fmt(x,Math.abs(xMax)<3?2:0)}</text><text x="${l-10}" y="${Y(y)+4}" text-anchor="end" class="axis">${fmt(y,Math.abs(yMax)<5?2:0)}</text>`;}
 for(const v of vertical){if(v.x>=xMin&&v.x<=xMax)out+=`<path d="M${X(v.x)} ${t}V${t+h}" stroke="${v.color||'#c48b39'}" stroke-dasharray="5 4"/><text x="${Math.min(X(v.x)+5,width-100)}" y="${t+12}" class="axis" fill="${v.color||'#a16d26'}">${esc(v.label)}</text>`;}
 series.forEach((s,i)=>{let pen=false;let path='';for(const p of s.data){if(!p||!Number.isFinite(p[1])){pen=false;continue;}path+=`${pen?'L':'M'}${X(p[0]).toFixed(2)},${Y(p[1]).toFixed(2)} `;pen=true;}out+=`<path d="${path}" clip-path="url(#clip-${esc(title.replace(/[^a-z0-9]/gi,''))})" fill="none" stroke="${s.color||COLORS[i%COLORS.length]}" stroke-width="2.5" ${s.dash?'stroke-dasharray="6 5"':''}/>`;});
 for(const p of points)if(p.x>=xMin&&p.x<=xMax&&p.y>=yMin&&p.y<=yMax)out+=`<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="5" fill="${p.color||'#102d38'}" stroke="white" stroke-width="2"/><text x="${X(p.x)+9}" y="${Y(p.y)-9}" class="axis" fill="#102d38">${esc(p.label||'Projekt')}</text>`;
 out+=`<text x="${l+w/2}" y="${height-6}" class="axis-label" text-anchor="middle">${esc(xLabel)}</text><text transform="translate(15 ${t+h/2}) rotate(-90)" class="axis-label" text-anchor="middle">${esc(yLabel)}</text></svg><div class="legend">${series.map((s,i)=>`<span><i style="background:${s.color||COLORS[i%COLORS.length]}"></i>${esc(s.name)}</span>`).join('')}</div>`;return out;
}
function planeSVG(d,r,view='iso',withGrid=true){
 const {g}=r,L=d.length,fw=d.fuseWidth,zWing=d.wingPosition==='high'?fw*.36:d.wingPosition==='low'?-fw*.32:0,tailZ=d.tailType==='t'?g.hv*.85:fw*.1;
 const projection=p=>view==='top'?[p[1],-p[0]]:view==='side'?[p[0],-p[2]]:view==='front'?[p[1],-p[2]]:[.82*p[0]+.64*p[1],-.32*p[0]+.36*p[1]-.95*p[2]];
 const fitPoints=[[0,0,0],[L,0,0],[L,0,g.hv],[L*.49,fw*.65,-fw*.65],[L*.1,-fw*.3,-fw*.3],[L*.35,fw*.5,fw*.55]];
 const tx=d.wingX+g.b/2*Math.tan(d.sweep*Math.PI/180),tz=zWing+Math.tan(d.dihedral*Math.PI/180)*g.b/2,tc=g.sh/g.bh;
 for(const sign of [-1,1])fitPoints.push([d.wingX,0,zWing],[d.wingX+g.root,0,zWing],[tx,sign*g.b/2,tz],[tx+g.tip,sign*g.b/2,tz],[L-tc*.7,sign*g.bh/2,tailZ],[L+tc*.3,sign*g.bh/2,tailZ]);
 if(d.propulsion!=='jet' && d.propulsion!=='none'){const px=d.propPosition==='tractor'?-.1:L*.83,pz=d.propPosition==='tractor'?0:fw*.6;for(const sign of [-1,1])fitPoints.push([px,sign*d.propDiameter/2,pz],[px,0,pz+sign*d.propDiameter/2]);}
 const bounds=fitPoints.map(projection);
 const xmin=Math.min(...bounds.map(p=>p[0])),xmax=Math.max(...bounds.map(p=>p[0])),ymin=Math.min(...bounds.map(p=>p[1])),ymax=Math.max(...bounds.map(p=>p[1]));
 const W=760,H=410,scale=Math.min(590/(xmax-xmin),260/(ymax-ymin));
 const P=p=>{const q=projection(p);return [380+(q[0]-(xmin+xmax)/2)*scale,205+(q[1]-(ymin+ymax)/2)*scale];};
 const str=ps=>ps.map(p=>P(p).map(v=>v.toFixed(2)).join(',')).join(' ');
 const poly=(ps,fill='#e7f0f2',stroke='#527780',sw=1.2)=>`<polygon points="${str(ps)}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>`;
 const line=(a,b,color='#82a6aa',dash='')=>`<line x1="${P(a)[0]}" y1="${P(a)[1]}" x2="${P(b)[0]}" y2="${P(b)[1]}" stroke="${color}" stroke-width="1" ${dash?'stroke-dasharray="4 4"':''}/>`;
 const tipX=d.wingX+g.b/2*Math.tan(d.sweep*Math.PI/180);
 const wing=s=>[[d.wingX,0,zWing],[tipX,s*g.b/2,zWing+Math.tan(d.dihedral*Math.PI/180)*g.b/2],[tipX+g.tip,s*g.b/2,zWing+Math.tan(d.dihedral*Math.PI/180)*g.b/2],[d.wingX+g.root,0,zWing]];
 const tailX=L-g.sh/g.bh*.7,tailChord=g.sh/g.bh;
 const tail=s=>[[tailX,0,tailZ],[tailX+.3*tailChord,s*g.bh/2,tailZ+.05],[tailX+tailChord,s*g.bh/2,tailZ+.05],[tailX+1.4*tailChord,0,tailZ]];
 let out=`<svg id="aircraft-svg-${view}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Schemat parametryczny samolotu ${esc(d.name)}, widok ${esc(view)}"><title>${esc(d.name)} — schemat poglądowy</title><defs><pattern id="draft-grid-${view}" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="#e6edef" stroke-width=".6"/></pattern><linearGradient id="body-shade-${view}" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#f7fafb"/><stop offset="1" stop-color="#b7ced2"/></linearGradient></defs>`;
 if(withGrid)out+=`<rect width="760" height="410" fill="#f7fafb"/><rect width="760" height="410" fill="url(#draft-grid-${view})"/><path d="M20 205H740M380 20V390" stroke="#d6e2e5" stroke-dasharray="5 7"/>`;
 out+=line([-.4,0,0],[L+.3,0,0],'#bdced2',true)+poly(wing(-1),'#d5e5e8')+poly(tail(-1),'#d5e5e8');
 const stations=[[0,.01,.02],[.1,.3,.32],[.24,.5,.45],[.43,.48,.55],[.58,.34,.37],[.8,.17,.18],[1,.02,.03]],ring=[];
 for(const [x,w,h] of stations)ring.push(Array.from({length:10},(_,i)=>[x*L,Math.cos(i*Math.PI/5)*w*fw,Math.sin(i*Math.PI/5)*h*fw]));
 for(let side=4;side>=0;side--)for(let j=0;j<ring.length-1;j++){const k=side,k2=(side+1)%10;out+=poly([ring[j][k],ring[j+1][k],ring[j+1][k2],ring[j][k2]],side>2?'#cfdee1':'#e8f0f2','#91aab0',.65);}
 out+=poly([[L-.75*tailChord,0,0],[L-.45*tailChord,0,g.hv],[L+.18*tailChord,0,g.hv*.85],[L+.12*tailChord,0,0]],'#d0e2e5');
 out+=poly(tail(1),'#e2edef')+poly(wing(1),'#eaf3f4');
 for(const s of [-1,1]){const wp=wing(s);out+=line([d.wingX+g.root*.72,0,zWing+.005],[tipX+g.tip*.72,s*g.b/2,zWing+Math.tan(d.dihedral*Math.PI/180)*g.b/2]);out+=line([d.wingX+g.root*.3,0,zWing+.005],[tipX+g.tip*.3,s*g.b/2,zWing+Math.tan(d.dihedral*Math.PI/180)*g.b/2],'#c0d0d4',true);}
 // Canopy is a dimensional envelope, not a cockpit layout.
 out+=poly([[L*.23,-fw*.32,fw*.23],[L*.34,-fw*.3,fw*.49],[L*.48,-fw*.21,fw*.4],[L*.46,fw*.22,fw*.4],[L*.32,fw*.3,fw*.46],[L*.23,fw*.32,fw*.23]],'#1b515d','#426f79',1.1);
 if(d.propulsion!=='jet' && d.propulsion!=='none'){
  const px=d.propPosition==='tractor'?-.1:L*.83,zc=d.propPosition==='tractor'?0:fw*.6;
  const prop=[];for(let i=0;i<=50;i++)prop.push([px,Math.cos(i*Math.PI/25)*d.propDiameter/2,zc+Math.sin(i*Math.PI/25)*d.propDiameter/2]);
  out+=`<polyline points="${str(prop)}" fill="#168c8308" stroke="#168c83" stroke-width="1.2" stroke-dasharray="4 4"/>`+line([px,0,zc-d.propDiameter/2],[px,0,zc+d.propDiameter/2],'#168c83');
 }
 for(const s of [-1,1]){const p1=[L*.47,s*fw*.22,-fw*.1],p2=[L*.49,s*fw*.65,-fw*.65];out+=line(p1,p2,'#57727c');const p=P(p2);out+=`<ellipse cx="${p[0]}" cy="${p[1]}" rx="${Math.max(2,scale*fw*.08)}" ry="${Math.max(3,scale*fw*.13)}" fill="#2a424b"/>`;}
 const extraWheel=[d.gear==='tailwheel'?L*.92:L*.14,0,-fw*.65],ew=P(extraWheel);out+=line([extraWheel[0],0,-fw*.15],extraWheel,'#57727c')+`<ellipse cx="${ew[0]}" cy="${ew[1]}" rx="${Math.max(2,scale*fw*.06)}" ry="${Math.max(3,scale*fw*.10)}" fill="#2a424b"/>`;
 const cg=P([r.cg.cg,0,0]);out+=`<circle cx="${cg[0]}" cy="${cg[1]}" r="4.5" fill="#e1a94c" stroke="white" stroke-width="1.5"/>`;
 if(view==='top'||view==='iso'){
  const p1=P([d.wingX-.6,-g.b/2,zWing]),p2=P([d.wingX-.6,g.b/2,zWing]);
  out+=`<path d="M${p1[0]},${p1[1]}L${p2[0]},${p2[1]}" fill="none" stroke="#168c83" stroke-width="1" stroke-dasharray="3 4"/><rect x="${(p1[0]+p2[0])/2-40}" y="${(p1[1]+p2[1])/2-10}" width="80" height="20" rx="5" fill="#f4f9f9"/><text x="${(p1[0]+p2[0])/2}" y="${(p1[1]+p2[1])/2+4}" fill="#147e76" text-anchor="middle" font-family="monospace" font-size="12">b = ${fmt(g.b,2)} m</text>`;
 }
 out+=`<text x="25" y="33" font-size="11" fill="#7c939b" font-family="monospace">${({iso:'AXONOMETRIA',top:'RZUT Z GÓRY',side:'RZUT Z BOKU',front:'RZUT Z PRZODU'})[view]}</text><text x="25" y="389" font-size="11" fill="#7c939b" font-family="monospace">${esc(d.name.toUpperCase())} / S = ${fmt(d.area,2)} m²</text><text x="735" y="389" font-size="11" fill="#7c939b" text-anchor="end" font-family="monospace">SC ● / SCHEMAT POGLĄDOWY</text></svg>`;
 return out;
}

function aircraft(result, view = 'iso') {
 const w = result.geometry.wing, f = result.geometry.fuselage;
 const ht = result.geometry.horizontal_tail, vt = result.geometry.vertical_tail;
 const quarterSweep = w.sweep_deg * Math.PI / 180;
 const leadingSweep = Math.atan(Math.tan(quarterSweep) + (w.cr - w.ct) / (2 * w.b)) * 180 / Math.PI;
 const d = {
   name: result.params.name, area: w.S, length: f.length, fuseWidth: f.diameter,
   wingX: result.balance.x_le_wing_m, wingPosition: w.wing_config === 'braced_high' ? 'high' : w.wing_config,
   tailType: 'conventional', sweep: leadingSweep, dihedral: w.dihedral_deg,
   propulsion: result.params.engine_type, propPosition: result.params.engine_location === 'nose' ? 'tractor' : 'pusher',
   propDiameter: result.bipol_projects?.p4?.paturski_propulsion?.propeller_selection?.diameter_m || Math.min(3, w.b * 0.2),
   gear: 'tricycle'
 };
 const r = {g: {b:w.b, root:w.cr, tip:w.ct, sh:ht.S_h, bh:ht.b_h, hv:vt.h_v},
   cg:{cg:result.balance.loading_states.at(-1).xcg_m}};
 return planeSVG(d,r,view);
}
root.BipolVisuals = {icon, chart, aircraft};
})(globalThis);

/* Parametryczny model poglądowy. Współrzędne w metrach: x do ogona, y w poprzek, z w górę. */
(function (root) {
  'use strict';
  const rad = Math.PI / 180;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const finite = (v, fallback) => Number.isFinite(v) ? v : fallback;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const format = value => value.toLocaleString('pl-PL', {maximumFractionDigits:2});
  const styles = {
    fuselage:['#d6e3e7', 'Kadłub'], wing:['#e3edef', 'Skrzydło'], tail:['#cadde1', 'Usterzenie'],
    canopy:['#285a68', 'Osłona kabiny'], gear:['#334c57', 'Podwozie'],
    engine:['#8197a5', 'Silnik / gondola'], propeller:['#28515b', 'Śmigło'],
    aileron:['#6489d2', 'Lotki'], flap:['#dda54c', 'Klapy'], slat:['#41a79b', 'Sloty / przedskrzydła'],
    flaperon:['#9b7ac2', 'Klapolotki']
  };
  const presets = {iso:{yaw:38, elevation:25}, top:{yaw:90, elevation:90}, side:{yaw:0, elevation:0}, front:{yaw:90, elevation:0}};
  function camera(view = 'iso', value = {}) {
    const base = presets[view] || presets.iso;
    const yaw = finite(value.yaw, base.yaw);
    return {yaw:((yaw + 180) % 360 + 360) % 360 - 180, elevation:clamp(finite(value.elevation, base.elevation), -90, 90)};
  }
  function project(point, orientation) {
    const a = orientation.yaw * rad, e = orientation.elevation * rad;
    const [x,y,z] = point, across = -Math.sin(a) * x + Math.cos(a) * y;
    return [Math.cos(a) * x + Math.sin(a) * y, Math.sin(e) * across - Math.cos(e) * z,
      Math.cos(e) * across + Math.sin(e) * z];
  }

  function model(result) {
    const p = result.params, g = result.geometry, w = g.wing, f = g.fuselage;
    const ht = g.horizontal_tail, vt = g.vertical_tail, controls = g.control_surfaces || {};
    const L = f.length, fw = f.diameter, half = w.b / 2;
    const wingZ = ['high','braced_high'].includes(w.wing_config) ? fw * .36 : w.wing_config === 'low' ? -fw * .32 : 0;
    const faces = [], parts = new Set();
    function face(points, part, label = styles[part][1], color = styles[part][0], line = false) {
      faces.push({points, part, label, color, line}); parts.add(part);
    }
    // Closed surfaces allow inspection from below and from either side.
    function lathe(stations, center, part, label, axis = 'x', color) {
      const rings = stations.map(([along, radius]) => Array.from({length:12}, (_, i) => {
        const angle = i * Math.PI / 6;
        return axis === 'x' ? [along, center[1] + Math.cos(angle) * radius, center[2] + Math.sin(angle) * radius]
          : [center[0] + Math.cos(angle) * radius, along, center[2] + Math.sin(angle) * radius];
      }));
      for (let j = 0; j < rings.length - 1; j++) for (let i = 0; i < 12; i++) {
        const k = (i + 1) % 12;
        face([rings[j][i], rings[j+1][i], rings[j+1][k], rings[j][k]], part, label, color);
      }
      face(rings[0], part, label, color); face(rings.at(-1), part, label, color);
    }
    // Matching short longitudinal panels keep the cabin and skin in depth order.
    function sample(stations, x) {
      const index=stations.findIndex(station=>station[0]>=x);
      if (index<=0) return [...stations[Math.max(0,index)]];
      const a=stations[index-1], b=stations[index], t=(x-a[0])/(b[0]-a[0]);
      return a.map((value,i)=>i===0?x:value+(b[i]-value)*t);
    }
    const bodyShape = [[0,.025],[.08,.30],[.2,.46],[.32,.50],[.44,.46],[.58,.34],[.72,.23],[.86,.12],[1,.018]];
    const cockpit = [[.20,0,0,.47],[.28,.25,.22,.45],[.37,.24,.20,.45],[.46,0,0,.445]];
    const longitudinal = [...new Set([...bodyShape.map(p=>p[0]),...cockpit.map(p=>p[0]),
      ...Array.from({length:41},(_,i)=>i/40)])].sort((a,b)=>a-b);
    const body=longitudinal.map(x=>sample(bodyShape,x));
    const rings = body.map(([x, radius]) => Array.from({length:12}, (_, i) => [x*L, Math.cos(i*Math.PI/6)*radius*fw, Math.sin(i*Math.PI/6)*radius*fw]));
    for (let j = 0; j < rings.length-1; j++) for (let i = 0; i < 12; i++) {
      face([rings[j][i], rings[j+1][i], rings[j+1][(i+1)%12], rings[j][(i+1)%12]], 'fuselage');
    }
    face(rings[0], 'fuselage'); face(rings.at(-1), 'fuselage');
    // Only the exposed canopy roof is meshed; its base follows the fuselage skin.
    const canopy = longitudinal.filter(x=>x>=.20&&x<=.46).map(x=>sample(cockpit,x)).map(([x,width,height,base]) => Array.from({length:7}, (_,i) => {
      const angle=i*Math.PI/6;
      return [x*L,Math.cos(angle)*width*fw,(base+Math.sin(angle)*height)*fw];
    }));
    for (let j=0; j<canopy.length-1; j++) for (let i=0; i<6; i++) {
      face([canopy[j][i],canopy[j+1][i],canopy[j+1][i+1],canopy[j][i+1]],'canopy');
    }

    function chord(y) {
      if (w.wing_planform === 'elliptical') return w.cr * Math.sqrt(Math.max(0, 1-(y/half)**2));
      if (w.wing_planform === 'rectangular') return w.cr;
      if (w.wing_planform === 'compound_trapezoid') {
        const split = finite(w.break_station_m, half*.4);
        return w.cr - (w.cr-w.ct)*clamp((y-split)/(half-split), 0, 1);
      }
      return w.cr + (w.ct-w.cr)*y/half;
    }
    function leading(y) {
      // The solver defines quarter-chord sweep; keep its planform convention.
      return result.balance.x_le_wing_m + (['rectangular','compound_trapezoid','elliptical'].includes(w.wing_planform)
        ? (w.wing_planform === 'elliptical' ? (w.cr-chord(y))*.25 : 0)
        : y*Math.tan(w.sweep_deg*rad) + (w.cr-chord(y))*.25);
    }
    function device(source, fallbackIn, fallbackOut, ratio, enabled) {
      return {in:clamp(finite(source?.y_in_m, half*fallbackIn), 0, half),
        out:clamp(finite(source?.y_out_m, half*fallbackOut), 0, half), ratio, enabled};
    }
    const combined = controls.is_flaperon || p.flap_type === 'flaperon' || p.aileron_type === 'flaperon';
    const flap = device(controls.flaps, Math.max(.08,fw/w.b), .7,
      clamp(finite(controls.flaps?.cf_over_c, finite(p.flap_chord_ratio,.25)), .05,.5), combined || p.flap_type !== 'none');
    const aileron = device(controls.ailerons, .72, .97,
      clamp(finite(controls.ailerons?.ca_over_c, finite(p.aileron_chord_ratio,.22)), .05,.5), p.aileron_type !== 'none');
    const slatType = p.slat_type || 'none', hasSlats = slatType !== 'none';
    const slat = {in:Math.max(fw*.6,half*.08), out:half*.94};
    const slatName = {fixed_slot:'Slot stały', slats_auto:'Slot automatyczny', auto_slat:'Slot automatyczny', krueger:'Klapa Kruegera'}[slatType] || 'Przedskrzydło';
    const spanStations = [...new Set([0,half,flap.in,flap.out,aileron.in,aileron.out,
      ...(hasSlats ? [slat.in,slat.out] : []), finite(w.break_station_m,0),
      ...Array.from({length:11}, (_,i) => half*i/10)])].filter(y=>y>=0&&y<=half).sort((a,b)=>a-b);
    const chordStations = [...new Set([0,.12,.3,1-flap.ratio,1-aileron.ratio,1])].sort((a,b)=>a-b);
    const contains = (device,y) => device.enabled !== false && y>device.in && y<device.out;
    function wingPoint(y, fraction, sign, side) {
      const c = chord(y), thickness = finite(w.tc_ratio,.12)*c*.5*Math.sin(Math.PI*fraction);
      return [leading(y)+c*fraction,sign*y,wingZ + y*Math.tan(w.dihedral_deg*rad)+side*thickness];
    }
    for (const sign of [-1,1]) for (let i=0; i<spanStations.length-1; i++) {
      const a=spanStations[i], b=spanStations[i+1], mid=(a+b)/2;
      for (let j=0; j<chordStations.length-1; j++) {
        const u=chordStations[j], v=chordStations[j+1], fraction=(u+v)/2;
        let part='wing', label=styles.wing[1];
        if (combined && contains(flap,mid) && fraction>1-flap.ratio) { part='flaperon'; label='Klapolotka'; }
        else if (!combined && contains(flap,mid) && fraction>1-flap.ratio) { part='flap'; label=controls.flaps?.name || 'Klapa'; }
        else if (!combined && contains(aileron,mid) && fraction>1-aileron.ratio) { part='aileron'; label=controls.ailerons?.name || 'Lotka'; }
        if (hasSlats && contains(slat,mid) && fraction<.12) { part='slat'; label=slatName; }
        for (const side of [-1,1]) {
          face([wingPoint(a,u,sign,side),wingPoint(b,u,sign,side),wingPoint(b,v,sign,side),wingPoint(a,v,sign,side)],part,label);
          const hinge = part==='slat' ? v : u;
          if (part==='slat' || (['flap','flaperon'].includes(part) && u===1-flap.ratio) || (part==='aileron' && u===1-aileron.ratio)) {
            face([wingPoint(a,hinge,sign,side),wingPoint(b,hinge,sign,side)],part,label,'#486873',true);
          }
        }
        if (b===half) face([wingPoint(b,u,sign,-1),wingPoint(b,u,sign,1),wingPoint(b,v,sign,1),wingPoint(b,v,sign,-1)],part,label);
      }
    }
    // Tail outlines use the calculated root/tip chords and span/height.
    const tailZ = fw*.1, tailRoot=finite(ht.cr_h,ht.S_h/ht.b_h*1.25), tailTip=finite(ht.ct_h,tailRoot*.6);
    const tailX=L-tailRoot*.9;
    for (const sign of [-1,1]) for (const side of [-1,1]) {
      face([[tailX,0,tailZ+side*.02*tailRoot],[tailX+.3*tailRoot,sign*ht.b_h/2,tailZ+side*.02*tailTip],
        [tailX+.3*tailRoot+tailTip,sign*ht.b_h/2,tailZ+side*.02*tailTip],[tailX+tailRoot,0,tailZ+side*.02*tailRoot]],'tail');
    }
    const finRoot=finite(vt.cr_v,tailRoot), finTip=finite(vt.ct_v,finRoot*.5);
    for (const side of [-1,1]) face([[L-finRoot,side*fw*.025,0],[L-finTip*.9,side*fw*.01,vt.h_v],
      [L+finTip*.1,side*fw*.01,vt.h_v],[L,side*fw*.025,0]],'tail');

    if (p.engine_type && p.engine_type!=='none' && p.engine_location!=='none') {
      const jet=p.engine_type==='jet', loc=p.engine_location || 'nose';
      const diameter=finite(result.bipol_projects?.p4?.paturski_propulsion?.propeller_selection?.diameter_m, Math.min(3,w.b*.2));
      const propRadius=Math.max(.1,diameter/2), length=Math.max(fw*.85,L*(jet ? .12 : .10));
      let engines;
      if (loc==='wing') engines=[-1,1].map(sign=>{
        const y=sign*Math.max(fw*.95,half*.32);
        return {x:leading(Math.abs(y))-length*.7,y,z:wingZ+Math.abs(y)*Math.tan(w.dihedral_deg*rad)-(jet?fw*.55:0),pusher:false};
      });
      else if (loc==='rear' && jet) engines=[-1,1].map(sign=>({x:L*.68,y:sign*fw*.72,z:fw*.12,pusher:false}));
      else if (loc==='retractable') engines=[{x:L*.51,y:0,z:fw*.6+propRadius,pusher:true}];
      else if (loc==='rear') engines=[{x:L*.68,y:0,z:fw*.7,pusher:true}];
      else engines=[{x:-fw*.06,y:0,z:0,pusher:false}];
      for (const engine of engines) {
        const {x,y,z,pusher}=engine, radius=fw*(jet ? .25 : loc==='nose' ? .34 : .23);
        lathe([[x,radius*.75],[x+length*.2,radius],[x+length*.8,radius*.9],[x+length,radius*.6]], [0,y,z], 'engine', jet?'Gondola silnika odrzutowego':'Osłona silnika śmigłowego');
        if (loc==='wing' || loc==='retractable' || loc==='rear') face([[x+length*.5,y,z],[x+length*.5,y,loc==='wing'?wingZ:fw*.3]],'engine','Mocowanie silnika','#6b858f',true);
        if (jet) {
          lathe([[x-.005*fw,radius*.67],[x+.01*fw,radius*.67]],[0,y,z],'engine','Wlot silnika odrzutowego','x','#243e49');
          lathe([[x+length,radius*.5],[x+length+.01*fw,radius*.5]],[0,y,z],'engine','Dysza silnika odrzutowego','x','#243e49');
        } else {
          const px=pusher?x+length+.08*fw:x-.08*fw;
          for (let blade=0; blade<3; blade++) {
            const angle=(blade*120+20)*rad;
            const propPoint=(r,offset,side)=>[px+side*fw*.012,y+Math.cos(angle)*r-Math.sin(angle)*offset,z+Math.sin(angle)*r+Math.cos(angle)*offset];
            for (const side of [-1,1]) face([propPoint(propRadius*.1,-propRadius*.035,side),propPoint(propRadius*.8,-propRadius*.07,side),
              propPoint(propRadius,0,side),propPoint(propRadius*.85,propRadius*.06,side),propPoint(propRadius*.15,propRadius*.06,side)],'propeller','Łopata śmigła');
          }
          lathe([[px-fw*.07,fw*.005],[px,fw*.08],[px+fw*.07,fw*.005]],[0,y,z],'propeller','Kołpak śmigła');
        }
      }
    }
    const track=finite(g.gear?.track,fw*1.3), ground=-fw*.72;
    for (const [x,y,radius] of [[L*.47,-track/2,fw*.115],[L*.47,track/2,fw*.115],[L*.14,0,fw*.085]]) {
      face([[x,y*.4,-fw*.1],[x,y,ground]],'gear','Goleń podwozia','#657e88',true);
      lathe([[y-fw*.04,radius],[y+fw*.04,radius]],[x,0,ground],'gear','Koło podwozia','y');
    }
    return {faces, parts:[...parts].map(id=>({id,color:styles[id][0],label:id==='slat'?slatName:styles[id][1]})),
      name:p.name || 'Samolot', area:w.S, span:w.b, cg:[finite(result.balance.loading_states?.at(-1)?.xcg_m,L*.4),0,0]};
  }

  function render(aircraft, view = 'iso', orientation) {
    const angle=camera(view,orientation), projected=aircraft.faces.map(face=>({...face, projected:face.points.map(p=>project(p,angle))}));
    const points=projected.flatMap(face=>face.projected);
    const xs=points.map(p=>p[0]), ys=points.map(p=>p[1]);
    const minX=Math.min(...xs), maxX=Math.max(...xs), minY=Math.min(...ys), maxY=Math.max(...ys);
    const scale=Math.min(650/Math.max(.1,maxX-minX),285/Math.max(.1,maxY-minY));
    const screen=p=>[380+(p[0]-(minX+maxX)/2)*scale,205+(p[1]-(minY+maxY)/2)*scale];
    const str=points=>points.map(p=>screen(p).map(v=>v.toFixed(2)).join(',')).join(' ');
    const title=({iso:'AXONOMETRIA',top:'RZUT Z GÓRY',side:'RZUT Z BOKU',front:'RZUT Z PRZODU'})[view] || 'WIDOK SWOBODNY';
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 410" role="img" aria-label="${escape(aircraft.name)} — obracany schemat samolotu" data-yaw="${angle.yaw}" data-elevation="${angle.elevation}"><title>${escape(aircraft.name)} — schemat poglądowy</title><rect width="760" height="410" fill="#f7fafb"/>`;
    for (let x=20; x<760; x+=25) svg+=`<path d="M${x} 48V356" stroke="#e7edef" stroke-width=".5"/>`;
    for (let y=55; y<360; y+=25) svg+=`<path d="M20 ${y}H740" stroke="#e7edef" stroke-width=".5"/>`;
    // Painter order is recalculated for every orientation, including underside views.
    projected.forEach(face=>{face.depth=face.projected.reduce((sum,p)=>sum+p[2],0)/face.points.length+(face.line ? .0001 : 0);});
    projected.sort((a,b)=>a.depth-b.depth);
    for (const face of projected) {
      const label=`data-aircraft-part="${face.part}"`;
      if (face.line) svg+=`<polyline ${label} points="${str(face.projected)}" fill="none" stroke="${face.color}" stroke-width="1.2"><title>${escape(face.label)}</title></polyline>`;
      else {
        const [a,b,c]=face.points, u=b.map((v,i)=>v-a[i]), v=c.map((v,i)=>v-a[i]);
        const normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
        const light=.84+.16*Math.abs(normal[2])/Math.max(.00001,Math.hypot(...normal));
        const rgb=face.color.match(/\w\w/g).map(hex=>Math.round(parseInt(hex,16)*light));
        const color=`rgb(${rgb.join(',')})`;
        svg+=`<polygon ${label} points="${str(face.projected)}" fill="${color}" stroke="${color}" stroke-width=".6" stroke-linejoin="round"><title>${escape(face.label)}</title></polygon>`;
      }
    }
    const cg=screen(project(aircraft.cg,angle));
    svg+=`<circle cx="${cg[0].toFixed(2)}" cy="${cg[1].toFixed(2)}" r="4" fill="#e1a94c" stroke="white" stroke-width="1.5"><title>Środek ciężkości</title></circle>`;
    svg+=`<g font-family="monospace" font-size="11" fill="#607e89"><text x="25" y="32">${title}</text><text x="735" y="32" text-anchor="end">${Math.round(angle.yaw)}° / ${Math.round(angle.elevation)}°</text><text x="25" y="378">${escape(aircraft.name)} · S = ${format(aircraft.area)} m² · b = ${format(aircraft.span)} m</text><text x="25" y="397">SC ● / SCHEMAT POGLĄDOWY</text></g></svg>`;
    return svg;
  }
  const api={model,render,camera,project};
  if (typeof module==='object' && module.exports) module.exports=api;
  else root.BipolAircraftPreview=api;
})(globalThis);

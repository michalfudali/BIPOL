/* Descriptive P1 analyses; all fits and source selection come from Python. */
(function () {
  'use strict';
  const {escape: esc, format: fmt, csv, filename} = BipolStudio;
  const $ = id => document.getElementById(id);
  const defaults = {trend_source:'all', trend_count:50, trend_engine_count:0, trend_year_min:0, trend_year_max:0,
    trend_weighting:'family', mission_phase_model:'standard', fuel_reserve_factor:1.06, mission_ld_factor:0.8};
  let result, catalog, catalogPromise, page = 0, selected = new Set(), visible = [];
  const size = 20;
  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const a = document.createElement('a'); a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function syncControls() {
    for (const [key, fallback] of Object.entries(defaults)) if ($(key)) $(key).value = formBaseParams[key] ?? fallback;
  }
  function status(message, error = false) {
    $('trendStatus').textContent = message; $('trendStatus').classList.toggle('trend-error', error);
  }
  const fitText = fit => fit ? `n = ${fit.n} · R² = ${fmt(fit.r2,3)}` : 'Za mało zróżnicowanych danych do regresji.';

  function plot(points, fit, {title, xLabel, yLabel, forecast, project} = {}) {
    if (!points.length) return '<p class="trend-empty">Brak kompletnych obserwacji dla tej zależności.</p>';
    const all = [...points]; if (project) all.push(project); if (forecast) all.push(forecast);
    let xmin=Math.min(...all.map(p=>p.x)), xmax=Math.max(...all.map(p=>p.x));
    let ymin=Math.min(...all.map(p=>p.y)), ymax=Math.max(...all.map(p=>p.y));
    const padX=(xmax-xmin)*.06||1, padY=(ymax-ymin)*.12||.1;
    xmin-=padX;xmax+=padX;ymin-=padY;ymax+=padY;
    const W=720,H=310,l=78,r=24,t=28,b=57, X=x=>l+(x-xmin)/(xmax-xmin)*(W-l-r), Y=y=>H-b-(y-ymin)/(ymax-ymin)*(H-t-b);
    let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>`;
    for(let i=0;i<=4;i++) {
      const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;
      svg+=`<path d="M${X(x)} ${t}V${H-b}M${l} ${Y(y)}H${W-r}" stroke="#dce7eb" stroke-dasharray="3 4"/><text x="${X(x)}" y="${H-b+22}" text-anchor="middle">${fmt(x,Math.abs(x)<10?2:0)}</text><text x="${l-8}" y="${Y(y)+4}" text-anchor="end">${fmt(y,Math.abs(y)<10?2:0)}</text>`;
    }
    const predict=x=>fit.kind==='power'?fit.A*Math.pow(x,fit.C):fit.intercept+fit.slope*x;
    if(fit) {
      const path=Array.from({length:65},(_,i)=>{const x=fit.x_min+(fit.x_max-fit.x_min)*i/64;return `${i?'L':'M'}${X(x)},${Y(predict(x))}`;}).join(' ');
      svg+=`<path d="${path}" stroke="#147f76" stroke-width="2.5" fill="none"/>`;
      if(forecast)svg+=`<path d="M${X(fit.x_max)},${Y(predict(fit.x_max))}L${X(forecast.x)},${Y(forecast.y)}" stroke="#a86621" stroke-width="2" stroke-dasharray="5 4"/>`;
    }
    for(const p of points) svg+=`<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="4" fill="#5478a9" fill-opacity=".72"><title>${esc(p.model)}: ${fmt(p.x,2)}; ${fmt(p.y,3)}</title></circle>`;
    for(const p of [project,forecast].filter(Boolean))svg+=`<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="6" stroke="white" stroke-width="2" fill="${p===project?'#b5486a':'#a86621'}"><title>${esc(p.model)}: ${fmt(p.x,2)}; ${fmt(p.y,3)}</title></circle>`;
    svg+=`<text x="${(W+l-r)/2}" y="${H-8}" text-anchor="middle">${esc(xLabel)}</text><text transform="translate(17 ${(H+t-b)/2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text></svg>`;
    return `<div class="trend-chart">${svg}</div><p class="studio-fine-print">Niebieskie punkty: konstrukcje · zielona linia: regresja${forecast?' · brązowy: prognoza +5 lat':''}${project?' · różowy: projekt':''}. ${fitText(fit)}</p>`;
  }

  function renderPlots() {
    const a=result?.bipol_projects?.p1?.trend_analysis; if(!a)return;
    const valid=a.similar_aircraft.filter(r=>r.empty_fraction>.15&&r.empty_fraction<.95);
    const t=a.time_trends.find(t=>t.key===$('trendTimeMetric').value);
    if(t) {
      const forecast=t.fit&&t.forecast_physical?{x:t.forecast_year,y:t.forecast,model:'Prognoza +5 lat'}:null;
      $('trendTimeChart').innerHTML=plot(t.points,t.fit,{title:`${t.label} — trend czasowy`,xLabel:'Rok certyfikacji',yLabel:`${t.label} [${t.unit}]`,forecast})+
        `<p>${t.fit?`Prognoza na ${t.forecast_year}: <strong>${fmt(t.forecast,3)} ${esc(t.unit)}</strong>${!t.forecast_physical?' — wartość poza zakresem fizycznym; odrzuć prognozę.':''}${t.provisional?' · próba poniżej 20 obserwacji.':''}`:'Wymagane co najmniej 3 kompletne daty i rozpiętość czasu ≥5 lat.'}</p>`;
    }
    $('trendMassChart').innerHTML=plot(valid.map(r=>({x:r.m0,y:r.empty_fraction,model:r.model})),a.mass_fit,
      {title:'Udział masy pustej a MTOW',xLabel:'MTOW [kg]',yLabel:'OEW / MTOW [−]',project:{x:result.mass.m0,y:a.we_wo_actual,model:'Projekt'}});
    const x=$('trendRelationX').value==='propulsion'?(result.params.engine_type==='jet'?'thrust_to_weight':'power_loading_kg_kw'):$('trendRelationX').value;
    const relation=a.relationships.find(r=>r.x_key===x&&r.y_key===$('trendRelationY').value);
    $('trendRelationChart').innerHTML=relation?plot(relation.points,relation.fit,{title:`${relation.y_label} a ${relation.x_label}`,xLabel:`${relation.x_label} [${relation.x_unit}]`,yLabel:`${relation.y_label} [${relation.y_unit}]`}):'<p>Brak porównywalnego rodzaju napędu.</p>';
  }

  async function loadCatalog() {
    if(!catalogPromise)catalogPromise=fetch('/api/aircraft').then(async r=>{if(!r.ok)throw new Error('Nie udało się pobrać bazy. Odśwież stronę.');return r.json();}).then(data=>{catalog=data;return data;});
    try {await catalogPromise;renderCatalog();}catch(error){$('trendCatalogStatus').textContent=error.message;catalogPromise=null;}
  }
  function filteredCatalog() {
    if(!catalog||!result)return [];
    const query=$('trendSearch').value.trim().toLocaleLowerCase('pl');
    const ids=new Set(result.bipol_projects.p1.trend_analysis.similar_aircraft.map(r=>r.id));
    return catalog.aircraft.filter(r=>r.aircraft_type===result.params.aircraft_type&&r.engine_type===result.params.engine_type)
      .filter(r=>result.params.trend_source==null||result.params.trend_source==='all'||r.source_id===result.params.trend_source)
      .filter(r=>!result.params.trend_engine_count||r.n_engines===result.params.trend_engine_count)
      .filter(r=>(!result.params.trend_year_min&&!result.params.trend_year_max)||r.year!=null&&(!result.params.trend_year_min||r.year>=result.params.trend_year_min)&&(!result.params.trend_year_max||r.year<=result.params.trend_year_max))
      .filter(r=>!query||`${r.model} ${r.manufacturer} ${r.family}`.toLocaleLowerCase('pl').includes(query))
      .sort((a,b)=>Number(ids.has(b.id))-Number(ids.has(a.id))||a.model.localeCompare(b.model));
  }
  function renderCatalog() {
    const all=filteredCatalog();page=Math.max(0,Math.min(page,Math.ceil(all.length/size)-1));visible=all.slice(page*size,(page+1)*size);
    $('trendCatalogStatus').textContent=`${all.length} pozycji w bieżącej klasie i źródle${$('trendSearch').value?' po wyszukaniu':''}. Zaznaczenie jest robocze do użycia „Zastosuj zaznaczone”.`;
    $('trendAircraftRows').innerHTML=visible.map(r=>`<tr class="${selected.has(r.id)?'trend-selected':''}"><td><input type="checkbox" data-aircraft-id="${esc(r.id)}" aria-label="Dodaj ${esc(r.model)} do próby" ${selected.has(r.id)?'checked':''}></td><td><strong>${esc(r.model)}</strong><small>${esc(r.family)} · <a href="${esc(catalog.sources[r.source_id].url)}" target="_blank" rel="noopener">${esc(r.source_id.toUpperCase())}</a></small><details><summary>Pochodzenie</summary><p>${esc(r.source_locator)}<br>${esc(r.source_references)}<br>${esc(r.empty_mass_definition)}</p>${r.quality_notes.length?`<p>${esc(r.quality_notes.join(' '))}</p>`:''}</details></td><td>${r.year??'—'}</td><td>${fmt(r.m0,0)}</td><td>${fmt(r.me,0)}</td><td>${fmt(r.s,2)}</td><td>${fmt(r.ar,2)}</td><td>${r.engine_type==='jet'?`${fmt(r.t_kn,1)} kN`:`${fmt(r.p_kw,1)} kW`}</td><td>${r.v_cruise_kmh!=null?`${fmt(r.v_cruise_kmh,0)} km/h`:r.cruise_mach!=null?`${fmt(r.cruise_mach,3)} Ma`:'—'}</td></tr>`).join('')||'<tr><td colspan="9">Brak konstrukcji w tej klasie i źródle. Nie zastępujemy ich samolotami o innym przeznaczeniu.</td></tr>';
    $('trendPage').textContent=all.length?`${page+1} / ${Math.ceil(all.length/size)}`:'0 / 0';
    $('trendPrev').disabled=page===0;$('trendNext').disabled=(page+1)*size>=all.length;
    $('trendSelectionStatus').textContent=`Zaznaczono: ${selected.size}`;
  }

  function render(res) {
    result=res;
    const a=res.bipol_projects.p1.trend_analysis,p=res.bipol_projects.p1.preliminary;
    selected=new Set(a.similar_aircraft.map(r=>r.id));
    status('Analiza aktualna. Zmieniaj próbę i porównuj założenia; braki danych są oznaczone kreską.');
    $('p1_we_trend').textContent=fmt(a.we_wo_trend,3);$('p1_we_actual').textContent=fmt(a.we_wo_actual,3);
    $('p1_trend_summary').textContent=`Baza: ${a.database_total} pozycji · próba: ${a.selected_n} wariantów / ${a.families_n} rodzin · regresja masowa: n=${a.mass_fit?.n??0}. ${a.warnings[0]||''}`;
    $('trendClassDescription').textContent=`${a.class_label} · napęd ${res.params.engine_type==='jet'?'odrzutowy':res.params.engine_type==='none'?'bez napędu':'śmigłowy'} · masa projektu ${fmt(res.mass.m0,1)} kg.`;
    $('trendSummary').innerHTML=[['Konstrukcji w bazie',a.database_total],['Wariantów w próbie',a.selected_n],['Rodzin w próbie',a.families_n],['Pełnych par masowych',a.mass_fit?.n??0]].map(([label,value])=>`<div><small>${esc(label)}</small><strong>${value}</strong></div>`).join('');
    $('trendWarnings').innerHTML=a.warnings.map(w=>`<p>${esc(w)}</p>`).join('');
    $('trendMassStats').innerHTML=`<p class="studio-equation">OEW / MTOW = ${fmt(a.reg_A,4)} · m₀<sup>${fmt(a.reg_C,4)}</sup> · ${fmt(a.k_vs,2)}</p><p>${fitText(a.mass_fit)} · projekt ${fmt(a.we_wo_actual,3)} · trend ${fmt(a.we_wo_trend,3)}</p><p>${esc(a.method)}</p>`;
    const metric=$('trendTimeMetric').value;
    $('trendTimeMetric').innerHTML=a.time_trends.map(t=>`<option value="${esc(t.key)}">${esc(t.label)} [${esc(t.unit)}] · n=${t.available_n}</option>`).join('');
    $('trendTimeMetric').value=metric||'m0';
    const labels={empty_fraction:'OEW / MTOW [−]',ar:'Wydłużenie AR [−]',wing_loading_kg_m2:'Obciążenie powierzchni [kg/m²]',h_tail_area:'Powierzchnia usterzenia poziomego [m²]',v_tail_area:'Powierzchnia usterzenia pionowego [m²]'};
    $('trendAverages').innerHTML='<div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Parametr</th><th>Średnia ważona</th><th>n</th></tr></thead><tbody>'+Object.entries(a.averages).map(([key,value])=>`<tr><td>${esc(labels[key])}</td><td>${fmt(value.mean,3)}</td><td>${value.n}</td></tr>`).join('')+'</tbody></table></div>';
    const turn=p.turn_45,mission=res.mass.mission_assumptions;
    $('trendPreliminary').innerHTML=`<p><strong>Kmax = ${fmt(p.k_max,2)}</strong> · Cx₀ z odwróconego wzoru = ${fmt(p.cx0_from_kmax,4)} · wydłużenie omywane AR/(Swet/S) = ${fmt(p.wetted_aspect_ratio,2)}.</p><div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Warunek analityczny</th><th>Cz</th><th>K</th><th>V TAS [km/h]</th><th>Granica Czmax</th></tr></thead><tbody>${p.operating_points.map(v=>`<tr><td>${esc(v.label)}<small>${esc(v.formula)}</small></td><td>${fmt(v.cl,3)}</td><td>${fmt(v.ld,2)}</td><td>${fmt(v.v_tas_kmh,1)}</td><td>${v.below_stall_limit?'W zakresie':'Punkt nieosiągalny'}</td></tr>`).join('')}</tbody></table></div><p>Wznoszenie: <code>${esc(p.climb.formula)}</code> → minimum T/W = ${fmt(p.climb.tw_lower_bound,4)}.</p><p>Zakręt poziomy 45° przy prędkości przelotowej: n = ${fmt(turn.load_factor,3)}, r = ${fmt(turn.radius_m,0)} m, ω = ${fmt(turn.rate_deg_s,2)} °/s. Wymagany T/W = ${fmt(turn.tw_required,4)}, Cz = ${fmt(turn.cl_required,3)} ${turn.cl_required>res.aerodynamics.cz_max_clean?'— powyżej Czmax; zakręt nieosiągalny.':''}</p><p>Bilans misji: K przelotu = ${fmt(res.mass.ld_cruise_used,2)}, współczynnik rezerwy = ${fmt(mission.reserve_factor,2)}; względna reszta równania masowego = ${fmt(mission.mass_residual_relative*100,5)}% (cel PDF: ≤0,1%).</p><p class="studio-fine-print">${esc(p.limitations)}</p>`;
    $('trendSources').innerHTML=Object.entries(a.sources).map(([id,s])=>`<p><a href="${esc(s.url)}" target="_blank" rel="noopener"><strong>${esc(s.name)}</strong></a><br>${esc(s.citation)}<br>${s.attribution?esc(s.attribution)+'<br>':''}<a href="/download/aircraft/${id}/data">Dane JSON</a> · <a href="/download/aircraft/${id}/license">Licencja ${esc(s.license)}</a></p>`).join('')+`<p class="studio-fine-print">${esc(a.limitations)}</p>`;
    renderPlots();loadCatalog();
  }
  function exportRows() {
    const a=result.bipol_projects.p1.trend_analysis;
    const rows=[['Model','Rodzina','Klasa','Rok certyfikacji','MTOW [kg]','OEW [kg]','S [m²]','b [m]','AR','Moc łączna [kW]','Ciąg łączny [kN]','V przelotowa [km/h]','Mach przelotu','Zasięg [km]','Źródło','Lokalizacja danych','Licencja','Definicja masy','Atrybucja']];
    for(const r of a.similar_aircraft)rows.push([r.model,r.family,r.aircraft_type,r.year,r.m0,r.me,r.s,r.b,r.ar,r.p_kw,r.t_kn,r.v_cruise_kmh,r.cruise_mach,r.range_km,a.sources[r.source_id].url,r.source_locator,a.sources[r.source_id].license,r.empty_mass_definition,a.sources[r.source_id].attribution||a.sources[r.source_id].citation]);
    return rows;
  }
  document.addEventListener('bipol:project',()=>{syncControls();status('Projekt zmieniony — oczekiwanie na nową analizę.');});
  document.addEventListener('bipol:calculating',()=>status('Dane wymagają przeliczenia lub trwają obliczenia.'));
  document.addEventListener('bipol:results',event=>render(event.detail));
  document.addEventListener('DOMContentLoaded',()=>{
    syncControls();if(currentResults)render(currentResults);
    document.querySelectorAll('[data-analysis-param]').forEach(input=>input.addEventListener('change',()=>{
      if(input.id.startsWith('trend_'))delete formBaseParams.trend_aircraft_ids;
      document.dispatchEvent(new CustomEvent('bipol:calculating'));status('Założenia zmienione — użyj „Przelicz analizę”.');
    }));
    for(const id of ['trendRecalculate','trendMissionApply'])$(id).addEventListener('click',()=>performCalculation());
    $('trendAutomatic').addEventListener('click',()=>{delete formBaseParams.trend_aircraft_ids;performCalculation();});
    $('trendApplySelection').addEventListener('click',()=>{
      // Search only affects visibility; keep all checked aircraft in this class.
      const ids=[...selected].filter(id=>catalog.aircraft.some(r=>r.id===id&&r.aircraft_type===result.params.aircraft_type&&r.engine_type===result.params.engine_type));
      if(!ids.length){status('Zaznacz przynajmniej jedną konstrukcję.',true);return;}
      formBaseParams.trend_aircraft_ids=ids;$('trend_count').value='0';performCalculation();
    });
    $('trendSearch').addEventListener('input',()=>{page=0;renderCatalog();});
    $('trendAircraftRows').addEventListener('change',event=>{const id=event.target.dataset.aircraftId;if(!id)return;if(event.target.checked)selected.add(id);else selected.delete(id);$('trendSelectionStatus').textContent=`Zaznaczono: ${selected.size}`;});
    $('trendSelectVisible').addEventListener('click',()=>{visible.forEach(r=>selected.add(r.id));renderCatalog();});
    $('trendClearSelection').addEventListener('click',()=>{selected.clear();renderCatalog();});
    $('trendPrev').addEventListener('click',()=>{page--;renderCatalog();});$('trendNext').addEventListener('click',()=>{page++;renderCatalog();});
    for(const id of ['trendTimeMetric','trendRelationX','trendRelationY'])$(id).addEventListener('change',renderPlots);
    $('trendExportCsv').addEventListener('click',async()=>{await performCalculation();if(currentResults&&$('openReportBtn').dataset.resultsStale==='false'){result=currentResults;download(`${filename(result.params.name)}-proba-trendow.csv`,csv(exportRows()),'text/csv;charset=utf-8');}});
    $('trendExportJson').addEventListener('click',async()=>{await performCalculation();if(currentResults&&$('openReportBtn').dataset.resultsStale==='false')download(`${filename(currentResults.params.name)}-analiza-trendow.json`,JSON.stringify({params:currentResults.params,analysis:currentResults.bipol_projects.p1},null,2),'application/json');});
  });
})();

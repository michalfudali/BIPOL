/* Mapa głównych zależności bieżącego projektu. Wartości pochodzą wyłącznie z API. */
(function (root) {
  'use strict';

  const GROUPS = [
    ['load', 'Ładunek i załoga'],
    ['mission', 'Misja'],
    ['wing', 'Skrzydło i aerodynamika'],
    ['drive', 'Napęd i wymagania']
  ];
  const PRIMARY_INPUTS = new Set([
    'aircraft_type', 'engine_type', 'n_pax', 'n_crew', 'm_pax', 'm_bag', 'm_cargo', 'm_payload', 'm_crew_person',
    'range_km', 'cruise_speed_kmh', 'cruise_altitude_m', 'v_stall_kmh', 'cz_max_lnd',
    'aspect_ratio', 'wingspan_m', 'wing_area_m2'
  ]);
  const LABELS = {
    glider: 'Szybowiec', motoglider: 'Motoszybowiec', piston_ga: 'Samolot śmigłowy',
    turboprop_regional: 'Samolot turbośmigłowy', jet_business: 'Odrzutowiec dyspozycyjny',
    jet_transport: 'Samolot odrzutowy', uav: 'Bezzałogowy statek powietrzny',
    prop: 'Śmigłowy', jet: 'Odrzutowy', none: 'Brak',
    low: 'Dolnopłat', mid: 'Średniopłat', high: 'Górnopłat', braced_high: 'Górnopłat zastrzałowy',
    trapezoidal: 'Trapezowy', rectangular: 'Prostokątny', compound_trapezoid: 'Prostokątno-trapezowy',
    elliptical: 'Eliptyczny', swept_trapezoidal: 'Skośny trapezowy',
    galinski: 'Model Galińskiego', cs23_level1: 'CS-23 poziom 1', cs23_level2: 'CS-23 poziom 2',
    cs23_level3: 'CS-23 poziom 3', cs23_level4: 'CS-23 poziom 4', single_slotted: 'Jednoszczelinowe',
    double_slotted: 'Dwuszczelinowe', fowler: 'Fowlera', plain: 'Zwykłe',
    auto_slat: 'Automatyczne', fixed_slot: 'Stałe',
    nose: 'Dziób', rear: 'Tył kadłuba', wing: 'Skrzydła', retractable: 'Chowany'
  };

  function build(result) {
    if (!result || result.status !== 'success') throw new Error('Brak aktualnych wyników obliczeń.');
    const p = result.params, m = result.mass, sizing = result.sizing, wing = result.geometry.wing;
    const aero = result.aerodynamics, perf = result.performance;
    const mode = p.wing_input_mode || (p.wingspan_m ? 'span_aspect' : p.wing_area_m2 ? 'area_aspect' : 'loading');
    const payloadMode = p.payload_input_mode || 'seats';
    const powered = p.engine_type !== 'none';
    const nodes = [], byId = new Map();
    function add(id, label, value, unit, deps, formula, phase, group) {
      if (byId.has(id)) throw new Error(`Powtórzony węzeł: ${id}`);
      const node = {id, label, value, unit, deps, formula, phase, group, kind: deps ? 'result' : 'input'};
      nodes.push(node); byId.set(id, node); return node;
    }
    const input = (id, label, unit, group, value = p[id]) => add(id, label, value, unit, null, '', '', group);
    const output = (id, label, value, unit, deps, formula, phase) => add(id, label, value, unit, deps, formula, phase);

    input('aircraft_type', 'Typ samolotu', '', 'drive');
    input('category', 'Kategoria', '', 'drive');
    input('engine_type', 'Napęd', '', 'drive');
    input('wing_config', 'Położenie płata', '', 'wing');
    input('flap_type', 'Typ klap', '', 'wing');
    input('slat_type', 'Skrzela', '', 'wing');
    input('wing_planform', 'Obrys skrzydła', '', 'wing');
    input('cx0', 'Opór bazowy Cx₀', '−', 'wing');
    input('oswald_e', 'Współczynnik Oswalda e', '−', 'wing');
    input('cz_max_lnd', 'Założone Cz max do doboru', '−', 'wing');
    input('cz_max_to', 'Cz max do startu', '−', 'wing');
    input('cz_max_clean', 'Cz max płata gładkiego', '−', 'wing');
    input('v_stall_kmh', 'Wymaganie VS0', 'km/h', 'drive');
    input('range_km', 'Zasięg', 'km', 'mission');
    input('cruise_speed_kmh', 'Prędkość przelotowa', 'km/h', 'mission');
    input('cruise_altitude_m', 'Wysokość przelotu', 'm', 'mission');
    input('mission_ld_factor', 'Udział K przelotowego', '−', 'mission', m.mission_assumptions.ld_factor);
    if (powered) {
      input('loiter_time_min', 'Rezerwa czasu', 'min', 'mission', p.loiter_time_min ?? 45);
      input('sfc', 'Zużycie jednostkowe', p.engine_type === 'jet' ? '1/h' : 'g/kWh', 'drive');
      input('fuel_reserve_factor', 'Współczynnik paliwa', '−', 'mission', m.mission_assumptions.reserve_factor);
      input('mission_phase_model', 'Model faz misji', '', 'mission', m.mission_assumptions.phase_model);
      input('takeoff_run_m', 'Wymagany rozbieg', 'm', 'drive');
      input('climb_rate_ms', 'Wymagane wznoszenie', 'm/s', 'drive');
      if (p.engine_type === 'prop') {
        input('prop_efficiency', 'Sprawność śmigła', '−', 'drive');
        input('prop_eff_to', 'Sprawność przy starcie', '−', 'drive');
      }
    }
    input('m_pax', 'Masa pasażera', 'kg', 'load');
    input('m_bag', 'Bagaż pasażera', 'kg', 'load', p.m_bag ?? 0);
    input('m_crew_person', 'Masa członka załogi', 'kg', 'load', p.m_crew_person ?? 90);
    if (m.unmanned) {
      output('n_pax', 'Liczba pasażerów', 0, 'os.', ['aircraft_type'], 'Bezzałogowy statek powietrzny → 0 pasażerów', 'P1');
      output('n_crew', 'Liczba załogi', 0, 'os.', ['aircraft_type'], 'Bezzałogowy statek powietrzny → 0 osób na pokładzie', 'P1');
    } else {
      input('n_pax', 'Liczba pasażerów', 'os.', 'load');
      input('n_crew', 'Liczba załogi', 'os.', 'load');
    }
    if (payloadMode === 'total') {
      input('m_payload', 'Masa płatna', 'kg', 'load');
      output('m_cargo', 'Masa cargo', p.m_cargo, 'kg', ['m_payload', 'n_pax', 'm_pax', 'm_bag'],
        'm_cargo = m_payload − n_pax · (m_pax + m_bag)', 'P1');
    } else {
      input('m_cargo', 'Masa cargo', 'kg', 'load');
      output('m_payload', 'Masa płatna', m.m_payload, 'kg', ['n_pax', 'm_pax', 'm_bag', 'm_cargo'],
        'm_payload = n_pax · (m_pax + m_bag) + m_cargo', 'P1');
    }
    output('m_crew', 'Masa załogi', m.m_crew, 'kg', ['n_crew', 'm_crew_person'],
      'm_crew = n_crew · m_os', 'P1');

    if (mode === 'span_area') {
      input('wingspan_m', 'Rozpiętość b', 'm', 'wing');
      input('wing_area_m2', 'Powierzchnia S', 'm²', 'wing');
      output('aspect_ratio', 'Wydłużenie Λ', wing.AR, '−', ['wingspan_m', 'wing_area_m2'], 'Λ = b² / S', 'P3');
    } else {
      input('aspect_ratio', 'Wydłużenie Λ', '−', 'wing');
      if (mode === 'span_aspect') {
        input('wingspan_m', 'Rozpiętość b', 'm', 'wing');
        output('wing_area_m2', 'Powierzchnia S', wing.S, 'm²', ['wingspan_m', 'aspect_ratio'], 'S = b² / Λ', 'P3');
      } else if (mode === 'area_aspect') {
        input('wing_area_m2', 'Powierzchnia S', 'm²', 'wing');
        output('wingspan_m', 'Rozpiętość b', wing.b, 'm', ['wing_area_m2', 'aspect_ratio'], 'b = √(S · Λ)', 'P3');
      }
    }

    output('ld_cruise_used', 'Wstępna doskonałość do bilansu Kcr', m.ld_cruise_used, '−',
      ['aspect_ratio', 'cx0', 'oswald_e', 'wing_config', 'flap_type', 'slat_type', 'mission_ld_factor'],
      'Kcr = współczynnik misji · Kmax, z korektą oporu konfiguracji', 'P1');
    output('fuel_fraction', 'Udział paliwa', m.fuel_fraction, '−', powered
      ? ['ld_cruise_used', 'range_km', 'cruise_speed_kmh', 'loiter_time_min', 'engine_type', 'sfc', 'fuel_reserve_factor', 'mission_phase_model', ...(p.engine_type === 'prop' ? ['prop_efficiency'] : [])]
      : ['engine_type'], powered ? 'Bilans faz misji i paliwa rezerwowego' : 'Lot bez napędu → udział paliwa 0', 'P1');
    output('m0', 'Masa startowa MTOW', m.m0, 'kg',
      ['m_payload', 'm_crew', 'fuel_fraction', 'aircraft_type', 'category', 'aspect_ratio', 'wing_config', 'flap_type'],
      'Iteracyjny bilans masy: m₀ = m_pusta + m_płatna + m_załoga + m_paliwo', 'P2');
    output('m_empty', 'Masa pusta', m.m_empty, 'kg', ['m0', 'aircraft_type', 'category', 'aspect_ratio', 'wing_config', 'flap_type'],
      'Udział masy pustej z korelacji statystycznej', 'P2');
    output('m_fuel', 'Masa paliwa', m.m_fuel, 'kg', ['m0', 'fuel_fraction'], 'm_paliwo = m₀ · udział paliwa', 'P2');

    if (mode === 'loading') {
      output('ws', 'Dobór W/S', sizing.design_point.ws, 'N/m²', ['v_stall_kmh', 'cz_max_lnd'],
        'W/S = 0,95 · ½ρ₀ · VS0² · Czmax,ląd', 'P2');
      output('wing_area_m2', 'Powierzchnia S', wing.S, 'm²', ['m0', 'ws'], 'S = m₀g / (W/S)', 'P3');
      output('wingspan_m', 'Rozpiętość b', wing.b, 'm', ['wing_area_m2', 'aspect_ratio'], 'b = √(S · Λ)', 'P3');
    } else {
      output('ws', 'Obciążenie W/S', sizing.design_point.ws, 'N/m²', ['m0', 'wing_area_m2'],
        'W/S = m₀g / S; wymaganie VS0 jest sprawdzane osobno', 'P2');
    }
    output('wing_loading_kg_m2', 'Obciążenie m₀/S', m.m0 / wing.S, 'kg/m²', ['m0', 'wing_area_m2'],
      'm₀/S', 'P3');
    if (result.constraints?.parameter_states?.taper_ratio?.state === 'derived') {
      output('taper_ratio', 'Zbieżność płata', wing.eta, '−', ['wing_planform'],
        'Zbieżność wynika z wybranego obrysu', 'P3');
    } else input('taper_ratio', 'Zbieżność płata', '−', 'wing', wing.eta);
    input('sweep_quarter_deg', 'Skos skrzydła', '°', 'wing', wing.sweep_deg);
    output('mac', 'Średnia cięciwa aerodynamiczna', wing.mac, 'm',
      ['wing_area_m2', 'wingspan_m', 'wing_planform', 'taper_ratio', 'sweep_quarter_deg'],
      'Wymiarowanie płata według wybranego obrysu', 'P3');

    if (powered) {
      const powerDeps = ['m0', 'ws', 'engine_type', 'aspect_ratio', 'cx0', 'oswald_e', 'wing_config',
        'flap_type', 'slat_type', 'cz_max_to', 'takeoff_run_m', 'climb_rate_ms', 'cruise_speed_kmh', 'cruise_altitude_m',
        ...(p.engine_type === 'prop' ? ['prop_efficiency', 'prop_eff_to'] : [])];
      if (p.engine_type === 'prop') {
        output('required_power_kw', 'Moc wymagana', sizing.design_point.required_power_kw, 'kW', powerDeps,
          'Maksimum wymagań startu, wznoszenia i przelotu z marginesem', 'P2');
        if (p.power_input_mode === 'fixed') input('engine_power_kw', 'Moc dostępna', 'kW', 'drive', p.engine_power_kw);
        else output('engine_power_kw', 'Moc dobrana', sizing.design_point.power_kw, 'kW', ['required_power_kw'],
          'Moc dobrana = moc wymagana', 'P2');
      } else {
        output('thrust_kn', 'Ciąg dobrany', sizing.design_point.thrust_kn, 'kN', powerDeps,
          'Maksimum wymagań startu, wznoszenia i przelotu z marginesem', 'P2');
      }
    }

    output('k_max', 'Doskonałość maksymalna Kmax', aero.k_max, '−',
      ['m0', 'wing_area_m2', 'wingspan_m', 'mac', 'cx0', 'oswald_e', 'wing_config', 'flap_type', 'slat_type'],
      'Biegunowa samolotu z uwzględnieniem geometrii i oporu', 'P4');
    output('cz_max_lnd_actual', 'Cz max w konfiguracji do lądowania', aero.cz_max_lnd, '−',
      ['cz_max_clean', 'flap_type', 'slat_type', 'mac'],
      'Cz max płata gładkiego + przyrost od klap i skrzeli', 'P4');
    output('vs_lnd_kmh', 'Prędkość przeciągnięcia VS0', perf.speeds.vs_lnd_kmh, 'km/h',
      ['m0', 'wing_area_m2', 'cz_max_lnd_actual'], 'VS0 = √(2m₀g / (ρ₀S·Czmax,ląd))', 'P5');
    output('best_glide', 'Najlepsza doskonałość lotu szybowego', perf.glide?.best_glide?.ld, '−',
      ['m0', 'wing_area_m2', 'k_max', 'cruise_altitude_m'], 'Biegunowa lotu szybowego na zadanej wysokości', 'P5');
    output('landing_distance_m', 'Lądowanie znad 15 m', perf.landing.distance_from_15m, 'm',
      ['m0', 'wing_area_m2', 'k_max', 'vs_lnd_kmh'], 'Podejście + wyrównanie + dobieg', 'P5');
    if (powered) {
      output('wy_max_ms', 'Maksymalne wznoszenie', perf.climb.wy_max_ms, 'm/s',
        ['m0', 'wing_area_m2', 'k_max', p.engine_type === 'prop' ? 'engine_power_kw' : 'thrust_kn'],
        'Nadwyżka mocy lub ciągu względem oporu', 'P5');
      output('distance_to_15m', 'Start do 15 m', perf.takeoff.distance_to_15m, 'm',
        ['m0', 'wing_area_m2', 'k_max', 'cz_max_to', p.engine_type === 'prop' ? 'engine_power_kw' : 'thrust_kn'],
        'Rozbieg + odcinek powietrzny do 15 m', 'P5');
    }
    output('n_max', 'Dopuszczalne przeciążenie dodatnie', result.envelope.limits.n_max, 'g',
      ['m0', 'category'], 'Limit według kategorii i masy', 'P6');
    if (powered) input('engine_location', 'Położenie silnika', '', 'drive');
    output('static_margin_aft_pct', 'Zapas stateczności dla tylnego ŚM', result.balance.stability.static_margin_aft_pct, '% ŚDA',
      ['m0', 'm_empty', 'm_payload', 'm_crew', 'm_fuel', 'mac', 'k_max', ...(powered ? ['engine_location'] : [])],
      'Punkt neutralny minus skrajne tylne położenie środka masy', 'P6');

    function lineage(node, stack = new Set()) {
      if (node.kind === 'input') return {depth: 0, inputs: new Set([node.id])};
      if (stack.has(node.id)) throw new Error(`Cykl zależności: ${node.id}`);
      stack.add(node.id);
      let depth = 0;
      const inputs = new Set();
      for (const id of node.deps) {
        const parent = byId.get(id);
        if (!parent) throw new Error(`Brak zależności ${id} dla ${node.id}`);
        const branch = lineage(parent, stack);
        depth = Math.max(depth, branch.depth + 1);
        for (const leaf of branch.inputs) inputs.add(leaf);
      }
      stack.delete(node.id);
      return {depth, inputs};
    }
    for (const node of nodes) {
      const chain = lineage(node);
      node.level = chain.depth;
      node.inputCount = chain.inputs.size;
    }
    const outputs = nodes.filter(node => node.kind === 'result')
      .sort((a, b) => a.level - b.level || a.inputCount - b.inputCount || a.label.localeCompare(b.label, 'pl'));
    const levels = [...new Set(outputs.map(node => node.level))];
    return {nodes, byId, outputs, levels, groups: GROUPS, wingMode: mode, payloadMode};
  }

  function formatValue(value, unit, id = '') {
    if (value == null || (typeof value === 'number' && !Number.isFinite(value))) return '—';
    if (typeof value === 'number') {
      const digits = unit === '−' ? 3 : unit === 'km/h' || unit === 'N/m²' ? 1 : 2;
      return `${value.toLocaleString('pl-PL', {maximumFractionDigits: digits})}${unit ? ` ${unit}` : ''}`;
    }
    const label = id === 'engine_type' && value === 'none' ? 'Bez napędu' : LABELS[value] || String(value);
    return `${label}${unit ? ` ${unit}` : ''}`;
  }

  function countWord(count, one, few, many) {
    if (count === 1) return one;
    const last = count % 10, lastTwo = count % 100;
    return last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14) ? few : many;
  }

  function render(result, container, visibleLevel = 1) {
    const graph = build(result);
    const escape = root.BipolStudio?.escape || (value => String(value));
    const nodeId = id => `tree-node-${id}`;
    const inputCard = ([group, title]) => {
      const inputs = graph.nodes.filter(node => node.kind === 'input' && node.group === group);
      if (!inputs.length) return '';
      const row = node => `<div id="${nodeId(node.id)}" class="calc-tree-input-row"><dt>${escape(node.label)}</dt><dd>${escape(formatValue(node.value, node.unit, node.id))}</dd></div>`;
      const primary = inputs.filter(node => PRIMARY_INPUTS.has(node.id));
      const extra = inputs.filter(node => !PRIMARY_INPUTS.has(node.id));
      return `<section class="calc-tree-input-card"><h3>${escape(title)} <small>${inputs.length}</small></h3>
        <dl>${primary.map(row).join('')}</dl>${extra.length ? `<details class="calc-tree-extra" data-tree-extra="${group}"><summary>Pozostałe założenia (${extra.length})</summary><dl>${extra.map(row).join('')}</dl></details>` : ''}</section>`;
    };
    const outputCard = node => `<details class="calc-tree-node" id="${nodeId(node.id)}" data-tree-node="${node.id}">
      <summary><span class="calc-tree-node-kicker">${escape(node.phase)} · ${node.deps.length} ${countWord(node.deps.length, 'poprzednik', 'poprzedniki', 'poprzedników')}</span>
        <span class="calc-tree-node-title">${escape(node.label)}</span><strong>${escape(formatValue(node.value, node.unit, node.id))}</strong>
        <small>${node.inputCount} ${countWord(node.inputCount, 'parametr', 'parametry', 'parametrów')} na pokazanej ścieżce</small></summary>
      <div class="calc-tree-node-detail"><p class="calc-tree-formula">${escape(node.formula)}</p><p class="calc-tree-dep-label">Główne zależności:</p>
        <div class="calc-tree-deps">${node.deps.map(id => `<button type="button" data-tree-jump="${id}">${escape(graph.byId.get(id).label)} <span>↑</span></button>`).join('')}</div></div>
    </details>`;
    const max = Math.max(...graph.levels);
    container.innerHTML = `<div class="calc-tree-start"><div class="calc-tree-start-head"><span class="calc-tree-step">START · 0</span><h2>Najpierw dane niezależne</h2><p>Pokazano główne założenia użyte w tej ścieżce. Tryb skrzydła: <strong>${escape({loading:'automatyczny dobór S',span_aspect:'b + Λ',span_area:'b + S',area_aspect:'S + Λ'}[graph.wingMode])}</strong>. Masa płatna: <strong>${graph.payloadMode === 'total' ? 'zadana łącznie' : 'z pasażerów i cargo'}</strong>.</p></div>
      <div class="calc-tree-input-grid">${graph.groups.map(inputCard).join('')}</div></div>
      ${graph.levels.map(level => `<section class="calc-tree-level" data-tree-level="${level}" ${level > visibleLevel ? 'hidden' : ''}>
        <div class="calc-tree-level-head"><span class="calc-tree-step">KROK ${level}</span><h2>${level === 1 ? 'Pierwsze wyniki' : 'Kolejne obliczenia'}</h2><p>Najpierw wyniki wymagające mniejszej liczby założeń.</p></div>
        <div class="calc-tree-node-grid">${graph.outputs.filter(node => node.level === level).map(outputCard).join('')}</div></section>`).join('')}`;
    return {max, graph};
  }

  function init() {
    const container = document.getElementById('calculationTreeRoot');
    const status = document.getElementById('calculationTreeStatus');
    if (!container || !status) return;
    let result = null, level = 1, max = 1, stale = false;
    function sync() {
      if (!result) {
        container.innerHTML = '<p class="calc-tree-empty">Oblicz projekt, aby zobaczyć zależności parametrów.</p>';
        status.textContent = 'Oczekiwanie na obliczenia.';
        for (const button of document.querySelectorAll('[data-tree-action]')) button.disabled = true;
        return;
      }
      const openIds = [...container.querySelectorAll('.calc-tree-node[open]')].map(node => node.id);
      const openExtras = [...container.querySelectorAll('.calc-tree-extra[open]')].map(node => node.dataset.treeExtra);
      const rendered = render(result, container, level);
      max = rendered.max;
      level = Math.min(level, max);
      for (const id of openIds) {
        const node = document.getElementById(id);
        if (node?.tagName === 'DETAILS') node.open = true;
      }
      for (const group of openExtras) {
        const details = container.querySelector(`[data-tree-extra="${group}"]`);
        if (details) details.open = true;
      }
      document.querySelector('[data-tree-action="next"]').disabled = level >= max;
      document.querySelector('[data-tree-action="all"]').disabled = level >= max;
      document.querySelector('[data-tree-action="reset"]').disabled = level <= 1;
      const count = rendered.graph.outputs.length;
      status.textContent = `${stale ? 'Wyniki wymagają przeliczenia. ' : ''}Krok ${Math.min(level, max)} z ${max}; ${count} ${countWord(count, 'wynik', 'wyniki', 'wyników')} w drzewie.`;
      status.classList.toggle('is-stale', stale);
    }
    function markStale() { if (result) { stale = true; status.textContent = 'Wyniki wymagają przeliczenia. Wyświetlane wartości pochodzą z poprzednich obliczeń.'; status.classList.add('is-stale'); } }
    document.addEventListener('bipol:results', event => { result = event.detail; stale = false; sync(); });
    document.addEventListener('bipol:project', () => { result = null; stale = false; level = 1; sync(); });
    document.getElementById('designForm')?.addEventListener('input', markStale, true);
    document.getElementById('designForm')?.addEventListener('change', markStale, true);
    document.addEventListener('bipol:calculating', markStale);
    document.getElementById('tab-calculation-tree')?.addEventListener('click', event => {
      const action = event.target.closest('[data-tree-action]')?.dataset.treeAction;
      if (action) {
        if (action === 'next') level = Math.min(max, level + 1);
        if (action === 'all') level = max;
        if (action === 'reset') level = 1;
        sync();
      }
      const jump = event.target.closest('[data-tree-jump]')?.dataset.treeJump;
      if (jump && result) {
        const graph = build(result), target = graph.byId.get(jump);
        level = Math.max(level, target.level);
        sync();
        const element = document.getElementById(nodeId(jump));
        const collapsed = element?.closest('.calc-tree-extra');
        if (collapsed) collapsed.open = true;
        if (element?.tagName === 'DETAILS') element.open = true;
        element?.scrollIntoView({behavior: 'smooth', block: 'center'});
        element?.classList.add('is-target');
        setTimeout(() => element?.classList.remove('is-target'), 1800);
      }
    });
    function nodeId(id) { return `tree-node-${id}`; }
    if (typeof currentResults !== 'undefined' && currentResults) result = currentResults;
    sync();
  }

  const api = {build, formatValue, render, init};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BipolCalculationTree = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', () => BipolCalculationTree.init());

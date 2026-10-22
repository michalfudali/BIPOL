/* Map a source-backed catalogue observation to project starting assumptions. */
(function (root) {
  'use strict';

  const classes = new Set(['piston_ga', 'turboprop_regional', 'jet_business',
    'jet_transport', 'glider', 'motoglider', 'uav']);
  const engines = new Set(['prop', 'jet', 'none']);
  const fullDistanceBases = new Set(['15m', '50ft', 'field_length']);
  const limits = {
    range_km: [0, 30000], cruise_speed_kmh: [80, 950], v_stall_kmh: [1, 400],
    climb_rate_ms: [1.5, 30], takeoff_distance_m: [0, 20000],
    landing_distance_m: [0, 20000], wingspan_m: [0.5, 80],
    wing_area_m2: [0.5, 1000], aspect_ratio: [2, 35],
    engine_power_kw: [0.001, 15000], dihedral_deg: [-3, 10],
    v_h: [0.05, 2], aileron_chord_ratio: [0.05, 0.45],
  };
  const observedNumbers = ['m0', 'me', 's', 'b', 'ar', 'p_kw', 't_kn',
    'v_cruise_kmh', 'v_stall_kmh', 'cruise_mach', 'range_km', 'takeoff_m', 'landing_m',
    'climb_rate_ms', 'ld_max', 'prop_diameter_m', 'v_h',
    'aileron_chord_ratio', 'dihedral_deg', 'year', 'n_engines'];

  function valid(value, key) {
    const [min, max] = limits[key];
    return typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max;
  }

  function fromRecord(record) {
    if (!record || typeof record !== 'object' || Array.isArray(record) ||
        typeof record.id !== 'string' || !record.id.trim() ||
        typeof record.model !== 'string' || !record.model.trim() ||
        typeof record.source_id !== 'string' || !record.source_id.trim() ||
        !classes.has(record.aircraft_type) || !engines.has(record.engine_type)) {
      throw new TypeError('Wybierz poprawny samolot z katalogu.');
    }

    const name = `Projekt na podstawie ${record.model.trim()}`;
    const params = {name, aircraft_type: record.aircraft_type, engine_type: record.engine_type};
    const locked = [];
    const copy = (target, value, key = target) => {
      if (valid(value, target)) params[target] = value;
    };

    copy('range_km', record.range_km);
    copy('cruise_speed_kmh', record.v_cruise_kmh);
    copy('v_stall_kmh', record.v_stall_kmh);
    if (record.engine_type !== 'none') {
      copy('climb_rate_ms', record.climb_rate_ms);
      const takeoff = record.takeoff_distance_m ??
        (fullDistanceBases.has(record.takeoff_basis) ? record.takeoff_m : null);
      copy('takeoff_distance_m', takeoff);
    }
    const landing = record.landing_distance_m ??
      (fullDistanceBases.has(record.landing_basis) ? record.landing_m : null);
    copy('landing_distance_m', landing);
    copy('dihedral_deg', record.dihedral_deg);
    copy('v_h', record.v_h);
    copy('aileron_chord_ratio', record.aileron_chord_ratio);

    const span = record.b, area = record.s;
    const computedAspect = typeof span === 'number' && Number.isFinite(span) &&
      typeof area === 'number' && Number.isFinite(area) && area > 0 ? span * span / area : null;
    const aspect = computedAspect ?? record.ar;
    if (valid(span, 'wingspan_m') && valid(area, 'wing_area_m2') &&
        valid(computedAspect, 'aspect_ratio')) {
      Object.assign(params, {wing_input_mode: 'span_area', wingspan_m: span,
        wing_area_m2: area, aspect_ratio: computedAspect});
      locked.push('wingspan_m', 'wing_area_m2');
    } else if (valid(aspect, 'aspect_ratio')) {
      params.aspect_ratio = aspect;
      if (valid(span, 'wingspan_m')) {
        params.wing_input_mode = 'span_aspect';
        params.wingspan_m = span;
        locked.push('wingspan_m', 'aspect_ratio');
      } else if (valid(area, 'wing_area_m2')) {
        params.wing_input_mode = 'area_aspect';
        params.wing_area_m2 = area;
        locked.push('wing_area_m2', 'aspect_ratio');
      } else {
        params.wing_input_mode = 'loading';
        locked.push('aspect_ratio');
      }
    }

    if (record.engine_type === 'prop' && valid(record.p_kw, 'engine_power_kw')) {
      params.power_input_mode = 'fixed';
      params.engine_power_kw = record.p_kw;
      locked.push('engine_power_kw');
    }
    if (locked.length) params.locked_params = locked;

    // MTOW and OEW are observations for comparison. The mass solver must
    // compute its own values from independent payload and mission assumptions.
    const observed = {};
    for (const key of observedNumbers) {
      observed[key] = typeof record[key] === 'number' && Number.isFinite(record[key])
        ? record[key] : null;
    }
    const reference_aircraft = {
      id: record.id, model: record.model, source_id: record.source_id,
      source_locator: record.source_locator ?? null,
      source_references: record.source_references ?? null,
      m0: observed.m0, me: observed.me,
      observed, applied_params: {...params},
    };
    return {name, aircraft_type: record.aircraft_type, params, reference_aircraft};
  }

  const api = {fromRecord};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BipolAircraftProject = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

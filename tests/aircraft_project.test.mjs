import test from 'node:test';
import assert from 'node:assert/strict';
import aircraftProject from '../static/js/aircraft-project.js';

const source = () => ({
  id: 'cado-ae270', model: 'Ae270', aircraft_type: 'turboprop_regional',
  engine_type: 'prop', source_id: 'cado', source_locator: 'CSV:4',
  source_references: 'CADO v1.0', m0: 4000, me: 2564, b: 13.84, s: 21,
  p_kw: 634, v_cruise_kmh: 402, range_km: 2350, takeoff_m: 621,
  takeoff_basis: 'field_length', landing_m: 606,
  landing_basis: 'field_length', year: 2000,
});

test('maps documented observations to independent project inputs and keeps mass as reference', () => {
  const record = source();
  const project = aircraftProject.fromRecord(record);
  assert.equal(project.name, 'Projekt na podstawie Ae270');
  assert.equal(project.params.aircraft_type, 'turboprop_regional');
  assert.equal(project.params.wing_input_mode, 'span_area');
  assert.equal(project.params.wingspan_m, 13.84);
  assert.equal(project.params.wing_area_m2, 21);
  assert.equal(project.params.aspect_ratio, 13.84 ** 2 / 21);
  assert.equal(project.params.power_input_mode, 'fixed');
  assert.equal(project.params.engine_power_kw, 634);
  assert.equal(project.params.takeoff_distance_m, 621);
  assert.equal(project.params.landing_distance_m, 606);
  assert.equal(project.params.cruise_speed_kmh, 402);
  assert.equal(project.params.range_km, 2350);
  assert.deepEqual(project.params.locked_params,
    ['wingspan_m', 'wing_area_m2', 'engine_power_kw']);
  assert.ok(!Object.hasOwn(project.params, 'm0'));
  assert.ok(!Object.hasOwn(project.params, 'me'));
  assert.equal(project.reference_aircraft.m0, 4000);
  assert.equal(project.reference_aircraft.me, 2564);
  assert.equal(project.reference_aircraft.source_id, 'cado');
  record.b = 100;
  assert.equal(project.params.wingspan_m, 13.84);
});

test('missing and unrelated fields remain absent from solver inputs', () => {
  const project = aircraftProject.fromRecord({
    id: 'fast-jet', model: 'Jet', aircraft_type: 'jet_transport',
    engine_type: 'jet', source_id: 'fast', m0: 60000, me: null,
    cruise_mach: 0.8, t_kn: 100, p_kw: null, b: null, s: null,
    range_km: null, v_cruise_kmh: null, takeoff_m: 900,
    takeoff_basis: 'ground_roll',
  });
  assert.equal(project.params.engine_type, 'jet');
  for (const key of ['m0', 'me', 'engine_power_kw', 'cruise_speed_kmh',
    'range_km', 'wing_input_mode', 'takeoff_distance_m', 'category',
    'v_stall_kmh', 'n_pax', 'sfc']) {
    assert.ok(!Object.hasOwn(project.params, key), key);
  }
  assert.equal(project.reference_aircraft.observed.cruise_mach, 0.8);
  assert.equal(project.reference_aircraft.observed.me, null);
});

test('a single measured dimension is used only with a valid aspect ratio', () => {
  const record = {...source(), s: null, ar: 9};
  const project = aircraftProject.fromRecord(record);
  assert.equal(project.params.wing_input_mode, 'span_aspect');
  assert.equal(project.params.wingspan_m, 13.84);
  assert.equal(project.params.aspect_ratio, 9);
  assert.ok(!Object.hasOwn(project.params, 'wing_area_m2'));

  const unqualified = aircraftProject.fromRecord({...record, ar: null});
  assert.ok(!Object.hasOwn(unqualified.params, 'wing_input_mode'));
  assert.ok(!Object.hasOwn(unqualified.params, 'wingspan_m'));
});

test('invalid geometry is not silently clamped or inferred from a conflicting AR', () => {
  const project = aircraftProject.fromRecord({...source(), b: 40, s: 20, ar: 8});
  assert.ok(!Object.hasOwn(project.params, 'wing_input_mode'));
  assert.ok(!Object.hasOwn(project.params, 'aspect_ratio'));
  assert.ok(!Object.hasOwn(project.params, 'wing_area_m2'));
});

test('rejects a record without catalog identity', () => {
  assert.throws(() => aircraftProject.fromRecord({...source(), id: ''}), TypeError);
  assert.throws(() => aircraftProject.fromRecord({...source(), aircraft_type: 'unknown'}), TypeError);
});

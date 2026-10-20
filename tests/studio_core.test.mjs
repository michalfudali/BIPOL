import test from 'node:test';
import assert from 'node:assert/strict';
import core from '../static/js/studio-core.js';

function result() {
  return {status:'success',params:{name:'=Nazwa; "test"',engine_type:'prop'},
    mass:{m0:650,m_fuel:70},geometry:{wing:{S:12,b:10,AR:8},schrenk:[{y:0,c_schrenk:1.4}]},
    sizing:{design_point:{power_kw:80,thrust_kn:null}},aerodynamics:{k_max:15,polar_points:[]},
    performance:{speeds:{vs_lnd_kmh:80,v_max_sl_kmh:220},climb:{wy_max_ms:4},ceiling:{service_ceiling_m:4000},glide:{points:[]}},
    balance:{stability:{static_margin_aft_pct:7},loading_states:[]},compliance_checks:[]};
}

test('snapshot is independent of future parameter and result mutations', () => {
  const input=result(), saved=core.snapshot(input,'Wariant bazowy');
  input.params.name='Nowa nazwa'; input.geometry.wing.S=20;
  assert.equal(saved.name,'Wariant bazowy');
  assert.equal(saved.params.name,'=Nazwa; "test"');
  assert.equal(saved.metrics.area,12);
  assert.equal(saved.metrics.thrust,null);
});

test('a sailplane never exposes its model placeholder Vmax as powered level-flight speed', () => {
  const input=result();input.params.engine_type='none';
  assert.equal(core.snapshot(input).metrics.vmax,null);
});

test('CSV handles semicolons, quotes, UTF-8, missing data and spreadsheet formulas', () => {
  const text=core.csv([['A;B','"cytat"','zażółć',null],['=1+1',' \t@bad','-tekst',-2.5]]);
  assert.ok(text.startsWith('\uFEFF'));
  assert.ok(text.includes('"A;B";"""cytat""";"zażółć";""\r\n'));
  assert.ok(text.includes('"\'=1+1"'));
  assert.ok(text.includes('"\' \t@bad"'));
  assert.ok(text.includes('"\'-tekst";"-2,5"'));
});

test('export uses actual Schrenk coordinates and protects the project name', () => {
  const text=core.csv(core.resultRows(result()));
  assert.ok(text.includes('"Projekt";"Nazwa";"\'=Nazwa; ""test"""'));
  assert.ok(text.includes('"Schrenk";"y; c_schrenk";"0";"m"'));
  assert.ok(!text.includes('undefined'));
});

test('blocked browser storage retains working data in memory and reports the failure', () => {
  const states=[];
  const store=core.createStore({getItem(){throw Error('blocked');},setItem(){throw Error('quota');}},ok=>states.push(ok));
  assert.deepEqual(store.read('projects',[]),[]);
  assert.equal(store.write('projects',[{id:1}]),false);
  assert.deepEqual(store.read('projects',[]),[{id:1}]);
  assert.equal(store.persistent,false);
  assert.ok(states.includes(false));
});

test('corrupt persisted projects are preserved instead of being overwritten by defaults', () => {
  const values=new Map([['projects','{broken json']]);
  const store=core.createStore({getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)});
  assert.deepEqual(store.read('projects',[]),[]);
  assert.equal(store.write('projects',[{id:2}]),false);
  assert.equal(values.get('projects'),'{broken json');
  assert.deepEqual(store.read('projects',[]),[{id:2}]);
  store.write('other',{ok:true});
  assert.equal(store.persistent,false);
});

test('stored values are detached from callers and persist after a store reload', () => {
  const values=new Map(), backend={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)};
  const store=core.createStore(backend);
  assert.equal(store.write('variants',[{name:'A'}]),true);
  const list=store.read('variants',[]);list[0].name='B';
  assert.equal(store.read('variants',[])[0].name,'A');
  assert.equal(core.createStore(backend).read('variants',[])[0].name,'A');
});

test('export filenames retain Polish letters without path separators', () => {
  assert.equal(core.filename('../../Łabędź <test>'), 'Łabędź-test');
  assert.equal(core.filename('///'),'projekt-bipol');
});

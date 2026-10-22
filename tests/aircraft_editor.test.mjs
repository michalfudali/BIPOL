import test from 'node:test';
import assert from 'node:assert/strict';
import editor from '../static/js/aircraft-editor.js';

test('blank optional values clear existing observations without becoming zero', () => {
  const data = editor.payload({model:'Test',engine_type:'prop',m0:'1200',range_km:'',year:''},{source_id:'fast',range_km:800,year:1999});
  assert.equal(data.range_km,null);
  assert.equal(data.year,null);
  assert.equal(data.me,null);
  assert.equal(data.m0,1200);
  assert.equal(data.source_id,'fast');
});

test('changing propulsion clears incompatible ratings and preserves zero engines', () => {
  const glider = editor.payload({engine_type:'none',p_kw:'100',t_kn:'10',n_engines:'1'});
  assert.equal(glider.p_kw,null);
  assert.equal(glider.t_kn,null);
  assert.equal(glider.n_engines,0);
  const jet = editor.payload({engine_type:'jet',p_kw:'100',t_kn:'10'});
  assert.equal(jet.p_kw,null);
  assert.equal(jet.t_kn,10);
});

test('nonfinite numbers are rejected and measured zero remains a value', () => {
  assert.throws(()=>editor.payload({m0:'Infinity'}));
  assert.throws(()=>editor.payload({m0:'abc'}));
  assert.equal(editor.payload({climb_rate_ms:'0'}).climb_rate_ms,0);
});

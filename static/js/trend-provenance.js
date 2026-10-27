/* Where a BIPOL_1 trend suggestion comes from; shared by the P1 panel, the wizard and the input panel. */
(function (root) {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const num = (value, digits = 3) => Number.isFinite(value) ? value.toLocaleString('pl-PL', {maximumFractionDigits: digits}) : '—';
  const unit = s => s.unit && s.unit !== '−' ? ` ${esc(s.unit)}` : '';

  function observations(p, s) {
    if (!p.observations?.length) return '';
    const rows = p.observations.map(o => `<tr><td>${esc(o.model)}</td>${p.x_label ? `<td>${num(o.x, 0)}</td>` : ''}<td>${num(o.value, 4)}</td><td>${num(o.weight, 3)}</td><td>${esc(String(o.source || '').toUpperCase())}</td></tr>`).join('');
    return `<details class="trend-provenance-data"><summary>Dane wejściowe: ${p.observations.length} obserwacji</summary><div class="trend-table-scroll"><table class="b-table"><thead><tr><th>Konstrukcja</th>${p.x_label ? `<th>${esc(p.x_label)}</th>` : ''}<th>${esc(s.symbol)}${s.unit !== '−' ? ` [${esc(s.unit)}]` : ''}</th><th>Waga wᵢ</th><th>Źródło</th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
  }

  function render(s, {alternatives = false} = {}) {
    const p = s?.provenance;
    if (!p) return '<div class="trend-provenance"><p>Ta wielkość nie dotyczy wybranego rodzaju napędu.</p></div>';
    const value = s.suggested_value != null ? ` → ${esc(s.symbol)} = <strong>${num(s.suggested_value, 4)}</strong>${unit(s)}` : '';
    const alt = (p.alternatives || []).map(a => `<p>Wartość alternatywna — ${esc(a.label)}: <strong>${num(a.value, 4)}</strong>${unit(s)}${alternatives ? ` <button type="button" class="btn btn-outline btn-sm" data-trend-alternative="${esc(s.key)}" data-value="${a.value}">Zastosuj tę wartość</button>` : ''}</p>`).join('');
    return `<div class="trend-provenance">
      <p><strong>${esc(p.method)}</strong>${value}</p>
      <p class="trend-provenance-basis">Podstawa: ${esc(p.basis)}</p>
      <p>Próba: ${esc(p.sample.description)} — ${p.sample.selected_n} wariantów, ${p.sample.families_n} rodzin.</p>
      ${p.formula ? `<p class="studio-equation">${esc(p.formula)}</p>` : ''}
      ${p.steps?.length ? `<ol>${p.steps.map(step => `<li>${esc(step)}</li>`).join('')}</ol>` : ''}
      ${alt}
      ${p.warnings?.length ? `<ul class="trend-provenance-warnings">${p.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
      ${observations(p, s)}
    </div>`;
  }

  async function fetchSuggestions(query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) if (value) params.set(key, value);
    const response = await fetch(`/api/trends/suggestions?${params}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'Nie udało się pobrać analizy trendów.');
    return data;
  }

  // Wizard: apply the chosen suggestions and show where each value came from.
  async function applyInWizard(button, box, keys, assign) {
    const original = button.textContent;
    button.disabled = true; button.textContent = 'Ładowanie…';
    const field = id => document.getElementById(id)?.value;
    try {
      const data = await fetchSuggestions({aircraft_type: field('wiz_aircraft_type') || 'piston_ga',
        engine_type: field('wiz_engine_type'), wing_configuration: field('wiz_wing_config')});
      const used = keys.map(key => data.suggestions[key]).filter(s => s?.suggested_value != null);
      used.forEach(s => assign(s.key, s.suggested_value));
      const missing = keys.filter(key => data.suggestions[key]?.provenance && data.suggestions[key].suggested_value == null);
      box.hidden = false;
      box.innerHTML = (used.length ? `<p role="status">Zastosowano z analizy trendów (prognozy na ${data.forecast_year} r.): ${used.map(s => `${esc(s.symbol)} = ${num(s.suggested_value, 4)}${unit(s)}`).join(', ')}.</p>` : '<p role="status">Brak danych w bazie dla tej klasy; wartości nie zmieniono.</p>') +
        (missing.length ? `<p>Bez zmian (brak danych w próbie): ${missing.map(key => esc(data.suggestions[key].symbol)).join(', ')}.</p>` : '') +
        used.map(s => `<details><summary>Skąd ${esc(s.symbol)} = ${num(s.suggested_value, 4)}${unit(s)}?</summary>${render(s, {alternatives: true})}</details>`).join('');
      box.querySelectorAll('[data-trend-alternative]').forEach(alt => alt.addEventListener('click', () => {
        assign(alt.dataset.trendAlternative, Number(alt.dataset.value));
        alt.textContent = 'Zastosowano'; alt.disabled = true;
      }));
    } catch (error) {
      box.hidden = false; box.textContent = error.message;
    } finally {
      button.disabled = false; button.textContent = original;
    }
  }

  let previewSeq = 0;
  async function previewInWizard() {
    const basisEl = typeof document !== 'undefined' ? document.getElementById('wizTrendPreviewBasis') : null;
    const geomEl = typeof document !== 'undefined' ? document.getElementById('wizTrendPreviewGeometry') : null;
    if (!basisEl && !geomEl) return;
    const seq = ++previewSeq;
    const field = id => document.getElementById(id)?.value;
    try {
      const data = await fetchSuggestions({
        aircraft_type: field('wiz_aircraft_type') || 'piston_ga',
        engine_type: field('wiz_engine_type'),
        wing_configuration: field('wiz_wing_config')
      });
      if (seq !== previewSeq) return;
      const ar = data.suggestions?.ar;
      if (basisEl) {
        basisEl.innerHTML = ar?.suggested_value != null
          ? ` — <strong>AR &approx; ${num(ar.suggested_value, 2)}</strong> (próba n = ${ar.provenance?.sample?.selected_n ?? '?'})`
          : '';
      }
      if (geomEl) {
        const parts = ['ar', 'vh', 'v_v', 'dihedral_deg']
          .map(k => data.suggestions?.[k])
          .filter(s => s?.suggested_value != null)
          .map(s => `${esc(s.symbol)} &approx; ${num(s.suggested_value, s.key === 'v_v' ? 3 : 2)}${unit(s)}`);
        geomEl.innerHTML = parts.length ? ` — <strong>${parts.join(' &middot; ')}</strong>` : '';
      }
    } catch (_) {
      if (seq !== previewSeq) return;
      if (basisEl) basisEl.textContent = '';
      if (geomEl) geomEl.textContent = '';
    }
  }

  const api = {render, fetchSuggestions, applyInWizard, previewInWizard};
  root.BipolTrendProvenance = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

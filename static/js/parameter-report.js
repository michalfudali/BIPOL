/* Raport wybranych parametrów: lista wielkości arkusza obliczeń, wyszukiwanie i wybór. */
(function (root) {
  'use strict';
  const ORDER = ['const', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6'];
  const QUICK = {
    aspect: ['AR'], mass: ['@mass'], m0: ['m0'], area: ['S'], polar: ['Cx0', 'k', 'Kmax'], loads: ['n_ult_p', 'n_ult_m']
  };
  const selection = new Set();
  let catalog = null, signature = '';
  const $ = id => document.getElementById(id);
  const esc = text => String(text ?? '').replace(/[&<>"']/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch]));
  const plain = text => String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l').toLowerCase();

  function tex(source, displayMode = false) {
    if (!root.katex) return esc(source);
    try { return root.katex.renderToString(source, {throwOnError: false, strict: 'ignore', displayMode}); }
    catch (error) { return esc(source); }
  }

  function known() {
    if (!catalog) return new Set();
    return new Set([...catalog.sections.flatMap(s => s.items.map(i => i.key)), ...catalog.blocks.map(b => b.key)]);
  }

  async function load(result) {
    const next = JSON.stringify(result.params);
    if (catalog && next === signature) { render(); return catalog; }
    $('paramCatalog').innerHTML = '<p class="studio-fine-print">Wczytywanie listy parametrów…</p>';
    const response = await fetch('/api/report/catalog', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: next
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Nie udało się wczytać listy parametrów.');
    catalog = data; signature = next;
    const available = known();
    [...selection].forEach(key => { if (!available.has(key)) selection.delete(key); });
    render();
    return catalog;
  }

  function itemHtml(item, query) {
    const text = plain(`${item.label} ${item.key}`);
    if (query && !text.includes(query)) return '';
    const value = item.kind === 'table' ? 'wzór tabelaryczny' : tex(`${item.sym} = ${item.value_tex}`);
    return `<label class="param-item${item.kind === 'given' ? ' param-given' : ''}"><input type="checkbox" value="${esc(item.key)}"${selection.has(item.key) ? ' checked' : ''}>`
      + `<span class="param-label">${esc(item.label)}</span><span class="param-value">${value}</span>`
      + `${item.kind === 'given' ? '<span class="param-kind">dana</span>' : ''}</label>`;
  }

  function render() {
    const box = $('paramCatalog');
    if (!box || !catalog) return;
    const query = plain($('paramSearch')?.value.trim());
    const html = ORDER.map(project => {
      const blocks = catalog.blocks.filter(b => b.project === project && (!query || plain(b.title).includes(query) || 'schemat iteracji masy'.includes(query)));
      const sections = catalog.sections.filter(s => s.project === project).map(section => {
        const items = section.items.map(item => itemHtml(item, query)).join('');
        if (!items && !(query && plain(section.title).includes(query))) return '';
        const all = items || section.items.map(item => itemHtml(item, '')).join('');
        return `<div class="param-section"><h4><label><input type="checkbox" data-param-section="${esc(section.key)}"> ${esc(section.title)}</label></h4>${all}</div>`;
      }).join('');
      if (!sections && !blocks.length) return '';
      const count = catalog.sections.filter(s => s.project === project).flatMap(s => s.items).filter(i => selection.has(i.key)).length
        + catalog.blocks.filter(b => b.project === project && selection.has(b.key)).length;
      const blockHtml = blocks.map(b => `<label class="param-item param-block"><input type="checkbox" value="${esc(b.key)}"${selection.has(b.key) ? ' checked' : ''}>`
        + `<span class="param-label"><strong>${esc(b.title)}</strong></span><span class="param-kind">${esc(b.note)}</span></label>`).join('');
      return `<details class="param-project"${query || count ? ' open' : ''}><summary>${esc(catalog.projects[project] || project)}`
        + `${count ? ` <span class="param-count">${count} wybr.</span>` : ''}</summary>${blockHtml}${sections}</details>`;
    }).join('');
    box.innerHTML = html || '<p class="studio-fine-print">Brak parametrów pasujących do wyszukiwania.</p>';
    box.querySelectorAll('[data-param-section]').forEach(input => {
      const keys = sectionKeys(input.dataset.paramSection);
      input.checked = keys.length && keys.every(k => selection.has(k));
      input.indeterminate = !input.checked && keys.some(k => selection.has(k));
    });
    status();
  }

  function sectionKeys(key) {
    return catalog.sections.find(s => s.key === key)?.items.map(i => i.key) || [];
  }

  function status() {
    const el = $('paramSelectionStatus');
    if (!el) return;
    const names = [...selection].map(key => {
      if (key.startsWith('@')) return catalog?.blocks.find(b => b.key === key)?.title || key;
      return catalog?.sections.flatMap(s => s.items).find(i => i.key === key)?.label || key;
    });
    el.textContent = names.length ? `Wybrano ${names.length}: ${names.slice(0, 6).join('; ')}${names.length > 6 ? '; …' : ''}.` : 'Nie wybrano parametrów.';
  }

  function quick(name) {
    if (!catalog) return;
    const keys = (QUICK[name] || []).map(key => key === '@mass' ? catalog.blocks[0]?.key : key).filter(Boolean);
    const available = known();
    keys.filter(key => available.has(key)).forEach(key => selection.add(key));
    render();
  }

  function options() {
    return {
      keys: [...selection],
      chain: document.querySelector('[name="param-chain"]:checked')?.value || '1',
      iterations: document.querySelector('[name="param-iterations"]:checked')?.value || 'all',
      start: $('paramIterStart')?.value
    };
  }

  document.addEventListener('DOMContentLoaded', () => {
    const box = $('paramCatalog');
    if (!box) return;
    box.addEventListener('change', event => {
      const input = event.target;
      if (input.dataset.paramSection) {
        sectionKeys(input.dataset.paramSection).forEach(key => input.checked ? selection.add(key) : selection.delete(key));
      } else if (input.value) {
        if (input.checked) selection.add(input.value); else selection.delete(input.value);
      }
      render();
    });
    $('paramSearch').addEventListener('input', render);
    document.querySelectorAll('[data-param-quick]').forEach(button => button.addEventListener('click', () => quick(button.dataset.paramQuick)));
    $('paramClear').addEventListener('click', () => { selection.clear(); render(); });
  });

  root.BipolParamReport = {load, options, render, selection};
})(window);

/* Poprawki autora w oknie raportu i eksport do edytowalnego pliku Word (DOCX).
   Poprawki zapisują się w tej przeglądarce (IndexedDB) i wracają po ponownym otwarciu tego samego
   raportu. Jeśli od zapisu zmieniły się wyniki, autor decyduje, czy wczytać dawną wersję tekstu. */
(() => {
  const DATABASE = 'bipol-report-edits';
  const STYLE_PROPS = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-opacity',
    'stroke-linecap', 'stroke-linejoin', 'opacity', 'font-family', 'font-size', 'font-weight', 'font-style',
    'text-anchor', 'dominant-baseline', 'visibility', 'display', 'marker-start', 'marker-mid', 'marker-end'];
  const PX_TO_MM = 25.4 / 96;
  let resolveReady;
  const api = window.BipolReportEditor = {ready: new Promise(resolve => { resolveReady = resolve; })};

  const hash = text => {
    let h = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 0x01000193); }
    return `${(h >>> 0).toString(16)}:${text.length}`;
  };
  const texOf = el => el.querySelector('annotation[encoding="application/x-tex"]')?.textContent ?? '';
  const mathOptions = () => window.BIPOL_MATH_OPTIONS || {
    delimiters: [{left: '\\[', right: '\\]', display: true}, {left: '\\(', right: '\\)', display: false}],
    throwOnError: false, strict: 'ignore'};

  // Wzory jako zapis TeX: krótszy zapis i ponowne składanie aktualnym KaTeX.
  function dehydrate(root) {
    root.querySelectorAll('.katex-display').forEach(el => el.replaceWith(`\\[${texOf(el)}\\]`));
    root.querySelectorAll('.katex').forEach(el => el.replaceWith(`\\(${texOf(el)}\\)`));
    root.querySelectorAll('[contenteditable],[spellcheck]').forEach(el => { el.removeAttribute('contenteditable'); el.removeAttribute('spellcheck'); });
    return root;
  }

  // Odcisk treści wygenerowanej: bez danych ze strony tytułowej i rysunków.
  function fingerprint(root) {
    const copy = dehydrate(root.cloneNode(true));
    copy.querySelectorAll('svg, .legend, [data-report-meta]').forEach(el => el.remove());
    return hash(copy.textContent.replace(/\s+/g, ' ').trim());
  }

  const store = (() => {
    let opening;
    const open = () => opening ??= new Promise((resolve, reject) => {
      const request = indexedDB.open(DATABASE, 1);
      request.onupgradeneeded = () => request.result.createObjectStore('edits');
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(new Error('Baza poprawek jest zablokowana.'));
    });
    const run = (mode, task) => open().then(db => new Promise((resolve, reject) => {
      const tx = db.transaction('edits', mode), request = task(tx.objectStore('edits'));
      tx.oncomplete = () => resolve(request.result);
      tx.onerror = tx.onabort = () => reject(tx.error);
    }));
    return {
      get: key => run('readonly', s => s.get(key)),
      put: (key, value) => run('readwrite', s => s.put(value, key)),
      remove: key => run('readwrite', s => s.delete(key)),
    };
  })();

  // ── rysunki: SVG z legendą jako PNG w rozdzielczości do druku ──
  function legendOf(svg) {
    const legend = svg.nextElementSibling;
    if (!legend?.classList.contains('legend')) return [];
    return [...legend.querySelectorAll('span')].map(span => ({
      color: span.querySelector('i') ? getComputedStyle(span.querySelector('i')).backgroundColor : '#222',
      text: span.textContent.trim()}));
  }

  function legendLayout(ctx, entries, width) {
    ctx.font = '10.5px Arial, sans-serif';
    const lines = [[]];
    let used = 0;
    for (const entry of entries) {
      const w = 26 + ctx.measureText(entry.text).width;
      if (used && used + 16 + w > width) { lines.push([]); used = 0; }
      used += (used ? 16 : 0) + w;
      lines.at(-1).push({...entry, w});
    }
    return lines;
  }

  async function rasterize(svg) {
    const box = svg.getBoundingClientRect();
    if (!box.width || !box.height) return null;
    const copy = svg.cloneNode(true);
    const from = [svg, ...svg.querySelectorAll('*')], to = [copy, ...copy.querySelectorAll('*')];
    from.forEach((el, i) => {
      const style = getComputedStyle(el);
      to[i].setAttribute('style', STYLE_PROPS.map(p => `${p}:${style.getPropertyValue(p)}`).join(';'));
    });
    copy.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    copy.setAttribute('width', box.width);
    copy.setAttribute('height', box.height);
    const legend = legendOf(svg), scale = 3;
    const measure = document.createElement('canvas').getContext('2d');
    const lines = legend.length ? legendLayout(measure, legend, box.width) : [];
    const legendHeight = lines.length ? 8 + lines.length * 15 : 0;
    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)], {type: 'image/svg+xml'}));
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(box.width * scale);
      canvas.height = Math.round((box.height + legendHeight) * scale);
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);
      ctx.drawImage(image, 0, 0, box.width, box.height);
      ctx.font = '10.5px Arial, sans-serif';
      ctx.textBaseline = 'middle';
      lines.forEach((line, row) => {
        const total = line.reduce((sum, e) => sum + e.w, 0) + 16 * (line.length - 1);
        let x = Math.max(0, (box.width - total) / 2);
        const y = box.height + 12 + row * 15;
        for (const entry of line) {
          ctx.fillStyle = entry.color;
          ctx.fillRect(x, y - 1.3, 22, 2.6);
          ctx.fillStyle = '#222';
          ctx.fillText(entry.text, x + 26, y);
          x += entry.w + 16;
        }
      });
      return {src: canvas.toDataURL('image/png'), mm: box.width * PX_TO_MM, legend: lines.length > 0};
    } catch (error) {
      return null;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  const figureSvgs = root => [...root.querySelectorAll('svg')].filter(svg => !svg.closest('.katex') && !svg.parentElement?.closest('svg'));

  function filename() {
    const base = document.title.replace(/\s+—\s+BIPOL I\s*$/, '').replace(/\s+—\s+/g, ' - ');
    return `${base.replace(/[<>:"/\\|?*\u0000-\u001f]+/g, '').replace(/\s+/g, '-').slice(0, 120) || 'raport'}.docx`;
  }

  document.addEventListener('DOMContentLoaded', async () => {
    const doc = document.querySelector('.document');
    const $ = id => document.getElementById(id);
    const editButton = $('edit-report'), docxButton = $('download-docx');
    const status = $('edit-status'), restoreButton = $('restore-edits'), discardButton = $('discard-edits'), resetButton = $('reset-edits');
    if (!doc) { resolveReady(); return; }

    const original = doc.innerHTML;
    const generated = fingerprint(doc);
    const structure = [...doc.querySelectorAll('[data-report-section],[data-calc],[data-sheet-section],h3[id^="block-"]')]
      .map(n => n.dataset.reportSection || n.dataset.calc || n.dataset.sheetSection || n.id).join(',');
    const key = `${document.title}|${hash(structure)}`;
    let editing = false, saveTimer = null, stored = null;

    const say = text => { if (status) status.textContent = text; };
    const when = time => new Date(time).toLocaleString('pl-PL', {dateStyle: 'short', timeStyle: 'short'});
    const show = (button, visible) => { if (button) button.hidden = !visible; };
    const lockAtomic = () => doc.querySelectorAll('.katex, .katex-display, svg, .legend')
      .forEach(el => el.setAttribute('contenteditable', 'false'));

    function replaceContent(html) {
      doc.innerHTML = html;
      if (window.renderMathInElement) renderMathInElement(doc, mathOptions());
      if (editing) lockAtomic();
      document.dispatchEvent(new CustomEvent('bipol:report-replaced'));
    }

    async function save() {
      clearTimeout(saveTimer);
      saveTimer = null;
      try {
        await store.put(key, {fingerprint: generated, html: dehydrate(doc.cloneNode(true)).innerHTML, savedAt: Date.now()});
        say(`Poprawki zapisane w tej przeglądarce (${when(Date.now())}). Przenoszą się do wydruku i pliku DOCX.`);
      } catch (error) {
        say('Nie udało się zapisać poprawek w przeglądarce. Pobierz DOCX lub wydrukuj raport przed zamknięciem okna.');
      }
    }

    function changed() {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(save, 600);
      show(resetButton, true);
      show(restoreButton, false);
      show(discardButton, false);
    }

    function setEditing(on) {
      editing = on;
      if (on) { doc.setAttribute('contenteditable', 'true'); doc.spellcheck = true; lockAtomic(); }
      else doc.removeAttribute('contenteditable');
      document.body.classList.toggle('editing', on);
      if (editButton) {
        editButton.setAttribute('aria-pressed', String(on));
        editButton.textContent = on ? 'Zakończ edycję' : 'Edytuj treść';
      }
      if (on) say('Kliknij tekst, aby go poprawić. Kliknij wzór, aby zmienić jego zapis TeX. Poprawki zapisują się same.');
      else if (saveTimer) save();
    }

    // Edytor zapisu wzoru: TeX z podglądem na żywo.
    const dialog = document.createElement('dialog');
    dialog.className = 'tex-editor no-print';
    dialog.setAttribute('aria-labelledby', 'tex-editor-title');
    dialog.innerHTML = '<form method="dialog"><h2 id="tex-editor-title">Zapis wzoru (TeX)</h2>'
      + '<textarea rows="6" spellcheck="false" aria-label="Zapis wzoru w TeX"></textarea>'
      + '<p class="tex-editor-label">Podgląd</p><div class="tex-preview" aria-live="polite"></div>'
      + '<div class="toolbar-row"><span></span><button value="cancel" class="secondary">Anuluj</button><button value="apply">Zastosuj</button></div></form>';
    document.body.append(dialog);
    const texInput = dialog.querySelector('textarea'), preview = dialog.querySelector('.tex-preview');
    let texTarget = null;
    const renderTex = (tex, target, displayMode) => katex.render(tex, target, {displayMode, throwOnError: false, strict: 'ignore'});
    texInput.addEventListener('input', () => renderTex(texInput.value, preview, texTarget?.classList.contains('katex-display')));
    dialog.addEventListener('close', () => {
      const target = texTarget;
      texTarget = null;
      if (dialog.returnValue !== 'apply' || !target?.isConnected || texInput.value === texOf(target)) return;
      const holder = document.createElement('span');
      renderTex(texInput.value, holder, target.classList.contains('katex-display'));
      const fresh = holder.firstElementChild;
      if (!fresh) return;
      fresh.setAttribute('contenteditable', 'false');
      fresh.querySelectorAll('.katex').forEach(el => el.setAttribute('contenteditable', 'false'));
      target.replaceWith(fresh);
      changed();
    });
    doc.addEventListener('click', event => {
      if (!editing || !window.katex) return;
      const target = event.target.closest('.katex-display') || event.target.closest('.katex');
      if (!target || !doc.contains(target)) return;
      event.preventDefault();
      texTarget = target;
      texInput.value = texOf(target);
      renderTex(texInput.value, preview, target.classList.contains('katex-display'));
      dialog.returnValue = '';
      dialog.showModal();
      texInput.focus();
    });

    doc.addEventListener('input', () => { if (editing) changed(); });
    doc.addEventListener('paste', event => {
      if (!editing) return;
      event.preventDefault();  // tylko czysty tekst: bez stylów i obcych znaczników
      document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
    });
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && saveTimer) save(); });
    editButton?.addEventListener('click', () => setEditing(!editing));

    restoreButton?.addEventListener('click', () => {
      if (!stored) return;
      replaceContent(stored.html);
      changed();
      say(`Wczytano poprawki z ${when(stored.savedAt)}. Sprawdź liczby — wyniki projektu zmieniły się od tamtego zapisu.`);
    });
    discardButton?.addEventListener('click', async () => {
      try { await store.remove(key); } catch (error) { /* brak bazy: nie ma czego usuwać */ }
      stored = null;
      show(restoreButton, false); show(discardButton, false);
      say('Odrzucono poprawki do wcześniejszej wersji raportu.');
    });
    resetButton?.addEventListener('click', async () => {
      if (!confirm('Usunąć wszystkie poprawki i przywrócić raport wygenerowany przez aplikację?')) return;
      clearTimeout(saveTimer);
      saveTimer = null;
      replaceContent(original);
      try { await store.remove(key); } catch (error) { /* brak bazy */ }
      show(resetButton, false);
      say('Przywrócono wersję wygenerowaną przez aplikację.');
    });

    api.setEditing = setEditing;

    // Eksport: bieżąca treść (z poprawkami) → serwer składa DOCX z równaniami Worda.
    api.buildDocx = async () => {
      if (saveTimer) await save();
      const svgs = figureSvgs(doc), images = [];
      for (const svg of svgs) images.push(await rasterize(svg));
      const hidden = [...doc.querySelectorAll('section, div, p, table, tr, td, th, figure, li, ul, ol, span, h2, h3, h4, caption, figcaption, header, nav')]
        .filter(el => !el.closest('.katex') && getComputedStyle(el).display === 'none');
      hidden.forEach(el => el.setAttribute('data-docx-hidden', ''));
      const clone = doc.cloneNode(true);
      hidden.forEach(el => el.removeAttribute('data-docx-hidden'));
      clone.querySelectorAll('[data-docx-hidden], .no-print').forEach(el => el.remove());
      figureSvgs(clone).forEach((svg, i) => {
        const image = images[i], legend = svg.nextElementSibling?.classList.contains('legend') ? svg.nextElementSibling : null;
        if (!image) { svg.remove(); return; }
        const img = document.createElement('img');
        img.src = image.src;
        img.dataset.widthMm = image.mm.toFixed(1);
        img.alt = svg.getAttribute('aria-label') || '';
        svg.replaceWith(img);
        if (image.legend) legend?.remove();
      });
      clone.querySelectorAll('.katex-display').forEach(el => {
        const math = el.querySelector('math');
        if (!math) return;
        const copy = math.cloneNode(true);
        copy.setAttribute('display', 'block');
        el.replaceWith(copy);
      });
      clone.querySelectorAll('.katex').forEach(el => { const math = el.querySelector('math'); if (math) el.replaceWith(math.cloneNode(true)); });
      clone.querySelectorAll('[contenteditable]').forEach(el => el.removeAttribute('contenteditable'));
      const author = doc.querySelector('[data-report-meta="student_name"]')?.textContent.trim() || '';
      let response;
      try {
        const base = [document.baseURI, location.href, window.opener?.location?.href, window.parent?.location?.href]
          .find(u => typeof u === 'string' && /^https?:/i.test(u));
        if (!base) throw new Error('offline');
        response = await fetch(new URL('/report/docx', base), {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({html: clone.innerHTML, title: document.title, author})});
      } catch (error) {
        throw new Error('Plik DOCX składa aplikacja: otwórz raport z działającej aplikacji (run.bat), nie z zapisanego pliku HTML.');
      }
      if (!response.ok) {
        let message = 'Nie udało się przygotować pliku DOCX.';
        try { message = (await response.json()).message || message; } catch (error) { /* odpowiedź bez JSON */ }
        throw new Error(message);
      }
      return {blob: await response.blob(), filename: filename()};
    };

    api.downloadDocx = async () => {
      const {blob, filename: name} = await api.buildDocx();
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = name;
      document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      return name;
    };

    docxButton?.addEventListener('click', async () => {
      docxButton.disabled = true;
      say('Przygotowywanie pliku DOCX…');
      try { say(`Pobrano ${await api.downloadDocx()}. Wzory są równaniami Worda, numeracja tabel, rysunków i wzorów aktualizuje się w Wordzie (F9).`); }
      catch (error) { say(error.message); }
      finally { docxButton.disabled = false; }
    });

    try {
      stored = await store.get(key);
    } catch (error) {
      stored = null;
      say('Ta przeglądarka nie pozwala zapisać poprawek. Edytować można, ale przed zamknięciem okna pobierz DOCX.');
    }
    if (stored?.html && stored.fingerprint === generated) {
      replaceContent(stored.html);
      show(resetButton, true);
      say(`Wczytano Twoje poprawki z ${when(stored.savedAt)}.`);
    } else if (stored?.html) {
      show(restoreButton, true); show(discardButton, true);
      say(`Masz poprawki z ${when(stored.savedAt)} do wcześniejszej wersji tego raportu. Od tamtej pory zmieniły się wyniki lub dane projektu.`);
    }
    resolveReady();
  });
})();

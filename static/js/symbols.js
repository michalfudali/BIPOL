/**
 * BiPOL Requiem - skład indeksów w symbolach technicznych.
 * Zapisy tekstowe (V_S0, VS0, Cz_max, wy_max, m₀, x^C) stają się prawdziwymi
 * indeksami dolnymi i górnymi w HTML, SVG i na wykresach canvas. Dotyczy to
 * również komunikatów z backendu, bo moduł obserwuje zmiany dokumentu.
 */
(function (global) {
  'use strict';

  const UNICODE_SUB = {
    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
    'ₐ': 'a', 'ₑ': 'e', 'ₒ': 'o', 'ₓ': 'x', 'ₕ': 'h', 'ₖ': 'k', 'ₗ': 'l', 'ₘ': 'm', 'ₙ': 'n',
    'ₚ': 'p', 'ₛ': 's', 'ₜ': 't', 'ᵢ': 'i', 'ⱼ': 'j', 'ᵣ': 'r', 'ᵤ': 'u', 'ᵥ': 'v',
    'ᵦ': 'β', 'ᵧ': 'γ', 'ᵨ': 'ρ', 'ᵩ': 'φ', 'ᵪ': 'χ', '₊': '+', '₋': '−'
  };
  const SUB_CHARS = Object.keys(UNICODE_SUB).join('');
  const WORD = '[\\p{L}\\p{Nd}∞]+';
  const INDEX = `${WORD}(?:,${WORD})*`;               // S0, max, x,szk,min
  const END = '(?![\\p{L}\\p{Nd}_])';
  // Zgodnie z CS-23/CS-VLA: V_S0, V_S1, V_NE ...; małe indeksy opisowe pozostają małe.
  const V_SPEEDS = 'S0|SO|S1|SF|NE|NO|MO|LOF|LO|LE|FE|TD|REF|MC|MU|S|A|B|C|D|F|G|H|R|X|Y|s0|so|s1|s|cr|app|min|max|opt|ekon|ek|tr';
  // Dwuliterowe zapisy, które same zawierają indeks: Cz_max → C_{z,max}, wy_max → w_{y,max}.
  const COMPACT_BASE = { Cx: ['C', 'x'], Cz: ['C', 'z'], Cm: ['C', 'm'], Cd: ['C', 'd'], wy: ['w', 'y'], Vs: ['V', 'S'], VS: ['V', 'S'] };
  const PREFILTER = new RegExp(`[_^${SUB_CHARS}]|V[A-Zs]|C['′]?[xzmd]|K(?:max|min|vs|cr)|Swet|MMO|V(?:cr|app|min|max|opt|ek|tr)`, 'u');
  const TEX = /\\[()[\]]|\$\$/;
  const SKIP = 'script,style,textarea,select,option,pre,kbd,samp,title,desc,.katex,.sym,[data-symbols="off"],[contenteditable="true"],[contenteditable=""]';
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const SMALL = 0.72, SUB_SHIFT = 0.28, SUP_SHIFT = -0.38;     // w em pisma bazowego

  const text = value => ({ kind: 'text', text: value });
  const sub = value => ({ kind: 'sub', text: value });
  const sup = value => ({ kind: 'sup', text: value });

  function speedIndex(index) {
    return index.replace(/^[sS][oO0](?=,|$)/, 'S0').replace(/^s(1?)(?=,|$)/, 'S$1');
  }

  function coefficientIndex(match, prime, axis, prime2, suffix = '', rest) {
    suffix = suffix.trim();
    const joined = { '0': '0', '₀': '0', i: 'i', H: 'H', V: 'V', '∞': '∞', 'V∞': 'V∞' }[suffix] ?? (suffix && `,${suffix}`);
    return [text('C' + prime + prime2), sub(axis + joined + rest)];
  }

  function explicitIndex(match, delta, base, prime, braced, plain) {
    let index = braced ?? plain;
    // Oznaczenia typu PW_118, GP_7270 (silniki w bazie) nie są symbolami.
    if (/^\p{Lu}{2}$/u.test(base) && /^\d/.test(index)) return [text(match)];
    const compact = COMPACT_BASE[base];
    if (compact) { [base, index] = [compact[0], `${compact[1]},${index}`]; }
    if (base === 'V') index = speedIndex(index);
    return [text(delta + base + prime), sub(index)];
  }

  const RULES = [
    // Jawny indeks: V_S0, C_x,szk, Λ_e, ΔC_x, C'_x,szk; w nawiasach także po cyfrze: 3C_{x0}.
    // Bez nawiasów cyfra przed literą wyklucza symbol (JT3D_1, A3Z_formatka.pdf).
    [new RegExp(`(?<![\\p{L}_.\\\\@'])(Δ?)(\\p{L}{1,2})(['′]?)_\\{([^{}]+)\\}${END}`, 'gu'), explicitIndex],
    [new RegExp(`(?<![\\p{L}\\p{N}_.\\\\@'])(Δ?)(\\p{L}{1,2})(['′]?)_(${INDEX})${END}`, 'gu'),
      (m, delta, base, prime, plain) => explicitIndex(m, delta, base, prime, undefined, plain)],
    // Indeks całego nawiasu: (C_x,szk)_min.
    [new RegExp(`\\)_(?:\\{([^{}]+)\\}|(${INDEX}))${END}`, 'gu'), (m, braced, plain) => [text(')'), sub(braced ?? plain)]],
    // Prędkości charakterystyczne pisane łącznie: VS0, Vs1, VC,min, Vcr.
    [new RegExp(`(?<![\\p{L}\\p{N}_.\\-\\\\@'])V(${V_SPEEDS})((?:,${WORD})*)${END}`, 'gu'),
      (m, index, rest) => [text('V'), sub(speedIndex(index) + rest)]],
    [new RegExp(`(?<![\\p{L}\\p{N}_])M(MO)${END}`, 'gu'), (m, index) => [text('M'), sub(index)]],
    // Współczynniki aerodynamiczne pisane łącznie: Cz, Cx0, Cx₀, CzH, Cz max, Czmax,ląd, Cd,min, ΔCz, 3Cx₀, C'z, Cx∞.
    [new RegExp(`(?<=^|[^\\p{L}_'\\\\]|Δ)C(['′]?)([xzmd])(['′]?)(0|₀|i|H|V∞|V|∞|max|min| max| min)?((?:,${WORD})*)(?![\\p{L}\\p{Nd}_${SUB_CHARS}])`, 'gu'), coefficientIndex],
    [new RegExp(`(?<![\\p{L}\\p{N}_])(?:K(max|min|vs|cr)|S(wet))${END}`, 'gu'), (m, k, s) => [text(k ? 'K' : 'S'), sub(k ?? s)]],
    // Indeksy zapisane znakami Unicode: m₀, wᵢ, W₀,₁, χ₂₅.
    [new RegExp(`(\\p{L})([${SUB_CHARS}]+(?:,[${SUB_CHARS}]+)*)`, 'gu'),
      (m, base, index) => [text(base), sub([...index].map(ch => UNICODE_SUB[ch] ?? ch).join(''))]],
    // Wykładnik: x₁^C, m₀^0,3658, (ρ/ρ₀)^0.85, Cz^(3/2).
    [/(?<!\s)\^(?:\{([^{}]+)\}|\(([^()]+)\)|([-−+]?[\p{L}\p{Nd}]+(?:[.,]\p{Nd}+)*))/gu,
      (m, braced, grouped, plain) => [sup(braced ?? grouped ?? plain)]],
  ];

  function applyRule([pattern, build], value) {
    const out = [];
    let last = 0;
    for (const match of value.matchAll(pattern)) {
      if (match.index > last) out.push(text(value.slice(last, match.index)));
      out.push(...build(...match));
      last = match.index + match[0].length;
    }
    if (last < value.length) out.push(text(value.slice(last)));
    return out;
  }

  /** Dzieli tekst na fragmenty {kind: 'text'|'sub'|'sup', text}. */
  function parse(value) {
    value = String(value ?? '');
    if (!PREFILTER.test(value)) return [text(value)];
    let parts = [text(value)];
    for (const rule of RULES) parts = parts.flatMap(part => part.kind === 'text' && part.text ? applyRule(rule, part.text) : [part]);
    return parts.filter(part => part.text).reduce((merged, part) => {
      const previous = merged[merged.length - 1];
      if (previous && previous.kind === 'text' && part.kind === 'text') previous.text += part.text;
      else merged.push({ ...part });
      return merged;
    }, []);
  }

  const isPlain = parts => parts.length <= 1 && (!parts.length || parts[0].kind === 'text');

  function htmlFragment(parts) {
    const fragment = document.createDocumentFragment();
    for (const part of parts) {
      if (part.kind === 'text') { fragment.append(part.text); continue; }
      const el = document.createElement(part.kind);
      el.className = 'sym';
      el.textContent = part.text;
      fragment.append(el);
    }
    return fragment;
  }

  function svgFragment(parts) {
    // dy zamiast baseline-shift, bo dy działa we wszystkich przeglądarkach i w eksporcie SVG.
    const fragment = document.createDocumentFragment();
    let shift = 0;
    const span = (content, dy, small) => {
      const el = document.createElementNS(SVG_NS, 'tspan');
      el.setAttribute('class', 'sym');
      if (dy) el.setAttribute('dy', `${+dy.toFixed(3)}em`);
      if (small) el.setAttribute('font-size', `${SMALL * 100}%`);
      el.textContent = content;
      return el;
    };
    for (const part of parts) {
      if (part.kind === 'text') {
        fragment.append(shift ? span(part.text, -shift) : part.text);
        shift = 0;
      } else {
        const target = part.kind === 'sub' ? SUB_SHIFT : SUP_SHIFT;
        fragment.append(span(part.text, (target - shift) / SMALL, true));
        shift = target;
      }
    }
    if (shift) fragment.append(span('\u200b', -shift));
    return fragment;
  }

  function typesetText(node) {
    const parent = node.parentNode;
    if (!parent || parent.nodeType !== 1 || !PREFILTER.test(node.data) || TEX.test(node.data) || parent.closest(SKIP)) return;
    const parts = parse(node.data);
    if (isPlain(parts)) return;
    node.replaceWith(parent.namespaceURI === SVG_NS ? svgFragment(parts) : htmlFragment(parts));
  }

  /** Składa indeksy we wszystkich węzłach tekstowych poddrzewa. */
  function typeset(root) {
    if (!root) return;
    if (root.nodeType === 3) { typesetText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 11) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(typesetText);
  }

  /** Składa poddrzewo i każdą późniejszą zmianę w nim (renderowanie przez innerHTML/textContent). */
  function watch(root) {
    typeset(root);
    new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'characterData') { if (record.target.isConnected) typesetText(record.target); }
        else record.addedNodes.forEach(node => { if (node.isConnected) typeset(node); });
      }
    }).observe(root, { childList: true, subtree: true, characterData: true });
  }

  /**
   * Tekst poddrzewa z indeksami zapisanymi jako _{…} i ^{…}. W odróżnieniu od textContent
   * (które daje „wy” z w<sub>y</sub>) kopia wstawiona w inne miejsce złoży się tak samo.
   */
  function source(node) {
    if (!node) return '';
    if (node.nodeType === 3) return node.data;
    if (node.nodeType !== 1 && node.nodeType !== 11) return '';
    if (node.nodeType === 1 && node.classList.contains('sym') && (node.localName === 'sub' || node.localName === 'sup'))
      return `${node.localName === 'sub' ? '_' : '^'}{${node.textContent}}`;
    return [...node.childNodes].map(source).join('');
  }

  /** Odpowiednik ctx.fillText z indeksami; respektuje textAlign i maxWidth. */
  function fillText(ctx, value, x, y, maxWidth) {
    const parts = parse(value);
    if (isPlain(parts)) {
      if (maxWidth === undefined) ctx.fillText(String(value), x, y);
      else ctx.fillText(String(value), x, y, maxWidth);
      return;
    }
    const font = ctx.font;
    const size = parseFloat((/(\d+(?:\.\d+)?)px/.exec(font) || [, 10])[1]);
    const small = font.replace(/(\d+(?:\.\d+)?)px/, `${(size * SMALL).toFixed(2)}px`);
    const widths = parts.map(part => { ctx.font = part.kind === 'text' ? font : small; return ctx.measureText(part.text).width; });
    const total = widths.reduce((sum, width) => sum + width, 0);
    const align = ctx.textAlign;
    let cursor = align === 'center' ? -total / 2 : align === 'right' || align === 'end' ? -total : 0;
    ctx.save();
    ctx.translate(x, y);
    if (maxWidth !== undefined && total > maxWidth) ctx.scale(maxWidth / total, 1);
    ctx.textAlign = 'left';
    parts.forEach((part, i) => {
      ctx.font = part.kind === 'text' ? font : small;
      ctx.fillText(part.text, cursor, part.kind === 'sub' ? size * SUB_SHIFT : part.kind === 'sup' ? size * SUP_SHIFT : 0);
      cursor += widths[i];
    });
    ctx.restore();
  }

  global.BipolSymbols = { parse, typeset, watch, fillText, source };
  // W raportach skrypt jest w <head>, w aplikacji na końcu <body>.
  if (document.body) watch(document.body);
  else document.addEventListener('DOMContentLoaded', () => watch(document.body));
})(window);

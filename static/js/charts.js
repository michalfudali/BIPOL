/**
 * BIPOL Studio - Standalone Aerospace Chart & Blueprint Graphics Engine
 * Wydział MEiL PW - Zakład Samolotów i Śmigłowców
 */

// Helper to setup retina-sharp canvas without layout growth on high-DPI screens
function initCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const parent = canvas.parentElement;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  const cssWidth = (parent ? parent.clientWidth : canvas.clientWidth) || 460;
  const cssHeight = 260;

  canvas.style.width = cssWidth + 'px';
  canvas.style.height = cssHeight + 'px';
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { canvas, ctx, width: cssWidth, height: cssHeight };
}

// 1. MATCHING CHART (W/S vs T/W or P/W)
function drawMatchingChart(canvasId, sizing) {
  const c = initCanvas(canvasId);
  if (!c) return;
  const { ctx, width, height } = c;
  if (sizing.engine_type === 'none') {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#526b77'; ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Szybowiec bez napędu', width / 2, height / 2 - 12);
    ctx.fillText('Diagram doboru mocy nie ma zastosowania.', width / 2, height / 2 + 12);
    return;
  }

  
  const pad = { top: 30, right: 30, bottom: 45, left: 60 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  
  ctx.clearRect(0, 0, width, height);
  
  const wsVals = sizing.ws_values;
  const xMin = Math.min(...wsVals);
  const xMax = Math.max(...wsVals);
  
  const isJet = sizing.engine_type === 'jet';
  const allY = [...sizing.curve_takeoff, ...sizing.curve_climb, ...sizing.curve_cruise];
  const yMin = 0;
  const yMax = Math.max(1, ...allY.filter(Number.isFinite)) * 1.15;
  
  function toX(val) { return pad.left + ((val - xMin) / (xMax - xMin)) * plotW; }
  function toY(val) { return pad.top + plotH - ((val - yMin) / (yMax - yMin)) * plotH; }
  
  // Grid lines
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const yVal = yMin + (i / 5) * (yMax - yMin);
    const y = toY(yVal);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(yVal.toFixed(isJet ? 2 : 1), pad.left - 8, y + 4);
  }
  
  for (let i = 0; i <= 5; i++) {
    const xVal = xMin + (i / 5) * (xMax - xMin);
    const x = toX(xVal);
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + plotH);
    ctx.stroke();
    
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(Math.round(xVal), x, pad.top + plotH + 18);
  }
  
  // Axes labels
  ctx.fillStyle = '#334155';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Obciążenie powierzchni W/S [N/m²]', pad.left + plotW / 2, height - 10);
  
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(isJet ? 'Obciążenie ciągu T/W [-]' : 'Obciążenie mocy P/W [W/N]', 0, 0);
  ctx.restore();
  
  // Draw Curves
  function drawLine(yArr, color, label) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    let pen = false;
    wsVals.forEach((ws, idx) => {
      if(!Number.isFinite(yArr[idx])) {pen=false;return;}
      const x = toX(ws);
      const y = toY(yArr[idx]);
      if (!pen) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      pen=true;
    });
    ctx.stroke();
  }
  
  drawLine(sizing.curve_takeoff, '#dc2626', sizing.takeoff_basis==='15m'?'Start do 15 m':'Rozbieg');
  drawLine(sizing.curve_climb, '#2563eb', 'Wznoszenie');
  drawLine(sizing.curve_cruise, '#059669', 'Przelot');
  
  // Stall vertical limit
  const xStall = toX(sizing.ws_stall_max);
  ctx.strokeStyle = '#9333ea';
  ctx.setLineDash([4, 4]);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(xStall, pad.top);
  ctx.lineTo(xStall, pad.top + plotH);
  ctx.stroke();
  ctx.setLineDash([]);
  
  // Design Point
  const dp = sizing.design_point;
  const dpX = toX(dp.ws);
  const dpY = toY(isJet ? dp.tw : dp.pw);
  
  ctx.fillStyle = '#d97706';
  ctx.beginPath();
  ctx.arc(dpX, dpY, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.stroke();
  
  ctx.fillStyle = '#b45309';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(`Punkt projektowy (${dp.ws} N/m²)`, dpX + 8, dpY - 6);
  
  // Legend
  const leg = [
    { label: 'Rozbieg (Sto)', color: '#dc2626' },
    { label: 'Wznoszenie (wy)', color: '#2563eb' },
    { label: 'Przelot (Vcr)', color: '#059669' },
    { label: 'Granica przeciągnięcia', color: '#9333ea' }
  ];
  let legX = pad.left + 10;
  leg.forEach((item) => {
    ctx.fillStyle = item.color;
    ctx.fillRect(legX, pad.top + 6, 12, 4);
    ctx.fillStyle = '#475569';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(item.label, legX + 16, pad.top + 10);
    legX += ctx.measureText(item.label).width + 28;
  });
}

// 2. POLAR CHART Cz vs Cx
function drawPolarChart(canvasId, aero) {
  const c = initCanvas(canvasId);
  if (!c) return;
  const { ctx, width, height } = c;
  
  const pad = { top: 25, right: 30, bottom: 45, left: 55 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  
  ctx.clearRect(0, 0, width, height);
  
  const pts = aero.polar_points;
  const xMin = 0;
  const xMax = 0.25;
  const yMin = -0.2;
  const yMax = aero.cz_max_lnd * 1.1;
  
  function toX(val) { return pad.left + ((val - xMin) / (xMax - xMin)) * plotW; }
  function toY(val) { return pad.top + plotH - ((val - yMin) / (yMax - yMin)) * plotH; }
  
  // Grid
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const yVal = yMin + (i / 5) * (yMax - yMin);
    const y = toY(yVal);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(yVal.toFixed(1), pad.left - 6, y + 4);
  }
  
  for (let i = 0; i <= 5; i++) {
    const xVal = xMin + (i / 5) * (xMax - xMin);
    const x = toX(xVal);
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + plotH);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(xVal.toFixed(2), x, pad.top + plotH + 18);
  }
  
  ctx.fillStyle = '#334155';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Współczynnik oporu Cx [-]', pad.left + plotW / 2, height - 10);
  
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('Współczynnik siły nośnej Cz [-]', 0, 0);
  ctx.restore();
  
  // Draw Curves: Clean, TO, LND
  function drawPolar(key, color, maxCz) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    let started = false;
    pts.forEach(p => {
      const cx = p[key];
      if (cx !== null && p.cz <= maxCz) {
        const x = toX(cx);
        const y = toY(p.cz);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
  }
  
  drawPolar('cx_clean', '#0284c7', aero.cz_max_clean);
  drawPolar('cx_to', '#d97706', aero.cz_max_to);
  drawPolar('cx_lnd', '#dc2626', aero.cz_max_lnd);
  
  // Tangent line for K_max
  const cxOpt = 2 * aero.cx0_clean;
  const xOpt = toX(cxOpt);
  const yOpt = toY(aero.cz_opt);
  ctx.strokeStyle = '#10b981';
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(toX(0), toY(0));
  ctx.lineTo(xOpt * 1.4, yOpt * 1.4);
  ctx.stroke();
  ctx.setLineDash([]);
  
  ctx.fillStyle = '#059669';
  ctx.beginPath();
  ctx.arc(xOpt, yOpt, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillText(`K_max = ${aero.k_max}`, xOpt + 8, yOpt + 4);
}

// 3. SCHRENK LIFT DISTRIBUTION
function drawSchrenkChart(canvasId, schrenkData) {
  const c = initCanvas(canvasId);
  if (!c) return;
  const { ctx, width, height } = c;
  
  const pad = { top: 25, right: 30, bottom: 45, left: 55 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  
  ctx.clearRect(0, 0, width, height);
  
  const ySpanMax = 1.0;
  const cMax = Math.max(...schrenkData.map(d => Math.max(d.c_geom, d.c_ellip))) * 1.15;
  
  function toX(val) { return pad.left + (val / ySpanMax) * plotW; }
  function toY(val) { return pad.top + plotH - (val / cMax) * plotH; }
  
  // Grid
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const yVal = (i / 5) * cMax;
    const y = toY(yVal);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(yVal.toFixed(2), pad.left - 6, y + 4);
  }
  
  for (let i = 0; i <= 5; i++) {
    const xVal = i / 5;
    const x = toX(xVal);
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + plotH);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(xVal.toFixed(1), x, pad.top + plotH + 18);
  }
  
  ctx.fillStyle = '#334155';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Względna półrozpiętość η = y / (b/2) [-]', pad.left + plotW / 2, height - 10);
  
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('Cięciwa c(y) [m]', 0, 0);
  ctx.restore();
  
  function drawKrzywa(key, color, isDashed = false, width = 2) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    if (isDashed) ctx.setLineDash([4, 4]);
    else ctx.setLineDash([]);
    ctx.beginPath();
    schrenkData.forEach((d, idx) => {
      const x = toX(d.eta_span);
      const y = toY(d[key]);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }
  
  drawKrzywa('c_geom', '#64748b', true, 1.8);
  drawKrzywa('c_ellip', '#0284c7', true, 1.8);
  drawKrzywa('c_schrenk', '#dc2626', false, 2.8);
}

// 4. RATE OF CLIMB wy(V)
function drawClimbChart(canvasId, climbData) {
  const c = initCanvas(canvasId);
  if (!c) return;
  const { ctx, width, height } = c;
  
  const pad = { top: 25, right: 30, bottom: 45, left: 55 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  
  ctx.clearRect(0, 0, width, height);
  
  const curve = climbData.climb_curve || [];
  if (!curve.length) {
    const message = 'Brak krzywej wznoszenia.';
    document.getElementById(canvasId)?.setAttribute('aria-label', message);
    ctx.fillStyle = '#526d79'; ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(message, width / 2, height / 2 - 10, width - 30);
    ctx.fillText('Lot bez napędu: sprawdź moduł „Lot szybowy”.', width / 2, height / 2 + 16, width - 30);
    return;
  }
  const xMin = curve[0].v_kmh * 0.9;
  const xMax = curve[curve.length - 1].v_kmh * 1.05;
  const yMax = Math.max(climbData.wy_max_ms * 1.25, 6.0);
  
  function toX(val) { return pad.left + ((val - xMin) / (xMax - xMin)) * plotW; }
  function toY(val) { return pad.top + plotH - (val / yMax) * plotH; }
  
  // Grid
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const yVal = (i / 5) * yMax;
    const y = toY(yVal);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(yVal.toFixed(1), pad.left - 6, y + 4);
  }
  
  ctx.fillStyle = '#334155';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Prędkość lotu V [km/h]', pad.left + plotW / 2, height - 10);
  
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('Prędkość wznoszenia wy [m/s]', 0, 0);
  ctx.restore();
  
  // Curve
  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  curve.forEach((p, idx) => {
    const x = toX(p.v_kmh);
    const y = toY(Math.max(0, p.wy_ms));
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  
  // wy_max point
  const pMaxX = toX(climbData.v_wy_max_kmh);
  const pMaxY = toY(climbData.wy_max_ms);
  ctx.fillStyle = '#dc2626';
  ctx.beginPath();
  ctx.arc(pMaxX, pMaxY, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillText(`wy_max = ${climbData.wy_max_ms} m/s`, pMaxX - 20, pMaxY - 10);
}

// 5. VN ENVELOPE (CS-23 / CS-25)
function drawVnEnvelope(canvasId, env) {
  const c = initCanvas(canvasId);
  if (!c) return;
  const { ctx, width, height } = c;
  
  const pad = { top: 25, right: 30, bottom: 45, left: 55 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  
  ctx.clearRect(0, 0, width, height);
  
  const vMax = env.speeds.v_d_kmh * 1.15;
  const nMin = env.limits.n_min * 1.3;
  const nMax = env.limits.n_max * 1.25;
  
  function toX(val) { return pad.left + (val / vMax) * plotW; }
  function toY(val) { return pad.top + plotH - ((val - nMin) / (nMax - nMin)) * plotH; }
  
  // Grid
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  const nZeroY = toY(0);
  ctx.beginPath();
  ctx.moveTo(pad.left, nZeroY);
  ctx.lineTo(pad.left + plotW, nZeroY);
  ctx.stroke();
  
  ctx.fillStyle = '#334155';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Prędkość przyrządowa V [km/h]', pad.left + plotW / 2, height - 10);
  
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('Współczynnik przeciążenia n [-]', 0, 0);
  ctx.restore();
  
  // Maneuver Polygon
  const poly = env.maneuver_polygon;
  ctx.fillStyle = 'rgba(2, 132, 199, 0.08)';
  ctx.strokeStyle = '#0284c7';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  poly.forEach((pt, idx) => {
    const x = toX(pt.v_kmh);
    const y = toY(pt.n);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  
  // Gust lines
  ctx.strokeStyle = '#f59e0b';
  ctx.setLineDash([3, 3]);
  ctx.lineWidth = 1.8;
  
  ctx.beginPath();
  env.gust_pos.forEach((p, idx) => {
    const x = toX(p.v_kmh);
    const y = toY(p.n);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  
  ctx.beginPath();
  env.gust_neg.forEach((p, idx) => {
    const x = toX(p.v_kmh);
    const y = toY(p.n);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.setLineDash([]);
  
  // Characteristic speeds markers
  const spds = [
    { label: 'Vs', val: env.speeds.v_s_kmh },
    { label: 'VA', val: env.speeds.v_a_kmh },
    { label: 'VC', val: env.speeds.v_c_kmh },
    { label: 'VD', val: env.speeds.v_d_kmh }
  ];
  spds.forEach(s => {
    const x = toX(s.val);
    ctx.strokeStyle = '#cbd5e1';
    ctx.setLineDash([2, 2]);
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
    
    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(s.label, x, pad.top + plotH + 18);
  });
}

// 6. BALANCE DIAGRAM (CG Travel Envelope)
function drawBalanceDiagram(canvasId, balance) {
  const c = initCanvas(canvasId);
  if (!c) return;
  const { ctx, width, height } = c;
  
  const pad = { top: 30, right: 35, bottom: 45, left: 60 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  
  ctx.clearRect(0, 0, width, height);
  
  const states = balance.loading_states;
  const masses = states.map(s => s.mass_kg);
  const cgs = states.map(s => s.xcg_mac_pct);
  
  const mMin = Math.min(...masses) * 0.9;
  const mMax = Math.max(...masses) * 1.08;
  const cgMin = Math.min(10, Math.min(...cgs) - 5);
  const cgMax = Math.max(balance.neutral_point.x_n_mac_pct + 5, Math.max(...cgs) + 5);
  
  function toX(val) { return pad.left + ((val - cgMin) / (cgMax - cgMin)) * plotW; }
  function toY(val) { return pad.top + plotH - ((val - mMin) / (mMax - mMin)) * plotH; }
  
  // Grid
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const yVal = mMin + (i / 5) * (mMax - mMin);
    const y = toY(yVal);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(Math.round(yVal), pad.left - 6, y + 4);
  }
  
  ctx.fillStyle = '#334155';
  ctx.font = 'bold 11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Położenie ŚM [% ŚDA / MAC]', pad.left + plotW / 2, height - 10);
  
  ctx.save();
  ctx.translate(16, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText('Masa samolotu [kg]', 0, 0);
  ctx.restore();
  
  // Neutral Point vertical line (Stateczność)
  const xNp = toX(balance.neutral_point.x_n_mac_pct);
  ctx.strokeStyle = '#dc2626';
  ctx.lineWidth = 2;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(xNp, pad.top);
  ctx.lineTo(xNp, pad.top + plotH);
  ctx.stroke();
  ctx.setLineDash([]);
  
  ctx.fillStyle = '#dc2626';
  ctx.font = 'bold 10px sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(`Punkt Neutralny (${balance.neutral_point.x_n_mac_pct}%)`, xNp + 5, pad.top + 15);
  
  // Safe CG limits box
  const xFwd = toX(balance.cg_range.forward_pct);
  const xAft = toX(balance.cg_range.aft_pct);
  ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
  ctx.fillRect(xFwd, pad.top, xAft - xFwd, plotH);
  
  // Connecting states line
  ctx.strokeStyle = '#0284c7';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  states.forEach((s, idx) => {
    const x = toX(s.xcg_mac_pct);
    const y = toY(s.mass_kg);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  
  // State points
  states.forEach(s => {
    const x = toX(s.xcg_mac_pct);
    const y = toY(s.mass_kg);
    ctx.fillStyle = '#0284c7';
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#0f172a';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`${s.name} (${s.xcg_mac_pct}%)`, x + 7, y - 4);
  });
}

// 7. GENERATOR RYSUNKU TECHNICZNEGO 3-RZUTOWEGO WG POLSKICH NORM (PN-EN ISO 128, 129, 5456-2, 5457, 5455, EN ISO 6433) ORAZ FORMATKI A3Z ZPK MEiL PW
function render3ViewBlueprint(containerId, geom, fullResults = null) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Wymiary rzeczywiste w metrach [m] -> przeliczane na milimetry [mm] zgodnie z normą PN-EN ISO 129 (bez miana mm na rysunku!)
  const b = Number(geom.wing.b);
  const l = Number(geom.fuselage.length);
  const d = Number(geom.fuselage.diameter);
  const cr = Number(geom.wing.cr);
  const ct = Number(geom.wing.ct);
  const mac = Number(geom.wing.mac);
  const yMac = Number(geom.wing.y_mac);
  const sweepDeg = Number(geom.wing.sweep_quarter_deg || geom.wing.sweep_deg || 0);
  const dihedralDeg = Number(geom.wing.dihedral_deg || 3);

  const wingConfig = (fullResults && fullResults.params && fullResults.params.wing_config) || geom.wing.wing_config || 'low';
  const engineLoc = (fullResults && fullResults.params && fullResults.params.engine_location) || 'nose';
  const engineType = (fullResults && fullResults.params && fullResults.params.engine_type) || 'prop';
  const acType = (fullResults && fullResults.params && fullResults.params.aircraft_type) || 'piston_ga';

  const bh = Number(geom.horizontal_tail.b_h);
  const ch = Number(geom.horizontal_tail.cr_h || geom.horizontal_tail.c_h || (geom.horizontal_tail.S_h / bh));
  const hv = Number(geom.vertical_tail.h_v);
  const cv = Number(geom.vertical_tail.cr_v || geom.vertical_tail.c_v || (geom.vertical_tail.S_v / hv));

  // Wymiary w milimetrach [mm] zaokrąglone do pełnych mm (zgodnie z zasadą ZPK CAD1)
  const b_mm = Math.round(b * 1000);
  const l_mm = Math.round(l * 1000);
  const d_mm = Math.round(d * 1000);
  const cr_mm = Math.round(cr * 1000);
  const ct_mm = Math.round(ct * 1000);
  const bh_mm = Math.round(bh * 1000);
  const hv_mm = Math.round(hv * 1000);
  const mac_mm = Math.round(mac * 1000);

  const h_tot_m = d * 1.35 + hv * 0.90;
  const h_tot_mm = Math.round(h_tot_m * 1000);
  const prop_d_m = engineType === 'prop' ? Math.max(1.4, Math.min(d * 1.45, 2.8)) : 0;
  const prop_d_mm = Math.round(prop_d_m * 1000);
  const wheel_track_m = (geom.gear && geom.gear.track) ? Number(geom.gear.track) : Math.max(d * 1.65, b * 0.22);
  const wheel_track_mm = Math.round(wheel_track_m * 1000);
  const wheelbase_m = (geom.gear && geom.gear.wheelbase) ? Number(geom.gear.wheelbase) : l * 0.28;
  const wheelbase_mm = Math.round(wheelbase_m * 1000);

  // Arkusz A3 (420 mm x 297 mm) w przeliczeniu 1 mm arkusza = 3 px -> 1260 x 891 px
  const sheetW = 1260;
  const sheetH = 891;

  // Ramka rysunkowa wg PN-EN ISO 5457 oraz formatki ZPK MEiL PW A3Z:
  // Margines lewy na wpięcie = 20 mm (60 px), pozostałe marginesy = 10 mm (30 px)
  const frameL = 60;
  const frameT = 30;
  const frameR = 1230;
  const frameB = 861;

  // Skalowanie geometrii płatowca na arkusz:
  // Maksymalna szerokość na rzut z boku / długość kadłuba L: ~480 px
  // Maksymalna wysokość na rzut z góry / rozpiętość b: ~295 px
  // Maksymalna szerokość na rzut z przodu / rozpiętość b: ~430 px
  const availW_L = 480;
  const availH_B_top = 295;
  const availW_B_front = 430;
  const pxPerMeter = Math.min(availW_L / l, availH_B_top / b, availW_B_front / b, 45.0);

  // Dobór znormalizowanej podziałki rysunkowej wg PN-EN ISO 5455 (1:10, 1:20, 1:25, 1:50, 1:100, 1:200, 1:500)
  const realScaleDenom = Math.round(3000 / pxPerMeter);
  let isoScale = 50;
  if (realScaleDenom <= 15) isoScale = 10;
  else if (realScaleDenom <= 22) isoScale = 20;
  else if (realScaleDenom <= 35) isoScale = 25;
  else if (realScaleDenom <= 75) isoScale = 50;
  else if (realScaleDenom <= 150) isoScale = 100;
  else if (realScaleDenom <= 350) isoScale = 200;
  else isoScale = 500;
  const scaleLabel = `1:${isoScale}`;

  const lPx = l * pxPerMeter;
  const bPx = b * pxPerMeter;
  const dPx = Math.max(d * pxPerMeter, 20);
  const crPx = cr * pxPerMeter;
  const ctPx = ct * pxPerMeter;
  const bhPx = bh * pxPerMeter;
  const chPx = Math.max(ch * pxPerMeter, 18);
  const hvPx = Math.max(hv * pxPerMeter, 32);
  const cvPx = Math.max(cv * pxPerMeter, 24);
  const macPx = mac * pxPerMeter;
  const yMacPx = yMac * pxPerMeter;
  const propR = (prop_d_m * pxPerMeter) / 2;
  const trackPx = wheel_track_m * pxPerMeter;
  const wheelbasePx = wheelbase_m * pxPerMeter;

  // Położenie skrzydła wzdłuż kadłuba
  const xWingLE = lPx * 0.30;
  const sweepOffsetPx = (bPx / 2) * Math.tan((sweepDeg * Math.PI) / 180);
  const dihedralOffsetPx = (bPx / 2) * Math.sin((dihedralDeg * Math.PI) / 180);

  // =========================================================================
  // UKŁAD RZUTÓW WG METODY EUROPEJSKIEJ "E" (PIERWSZEGO KĄTA, PN-EN ISO 5456-2):
  // 1. Rzut główny (Widok z lewego boku) -> Lewa górna ćwiartka arkusza
  // 2. Rzut z góry (Widok z góry) -> DOKŁADNIE POD rzutem głównym (wspólna baza osi X!)
  // 3. Rzut z lewej strony (Widok od przodu) -> PO PRAWEJ STRONIE rzutu głównego (wspólna baza osi Y!)
  // =========================================================================
  const xNose = 135;        // Wspólna współrzędna X dziobu dla rzutu głównego i rzutu z góry
  const ySideAxis = 205;    // Wspólna współrzędna Y osi kadłuba dla rzutu głównego i rzutu z przodu
  const yTopAxis = 605;     // Oś symetrii kadłuba na rzucie z góry
  const xFrontAxis = Math.min(1210 - bPx / 2, Math.max(xNose + lPx + 200, 930)); // Oś symetrii na rzucie z przodu

  // Bezwzględne współrzędne usterzenia (ściśle przy ogonie kadłuba xNose + lPx)
  const xTailTE = xNose + lPx;
  const cvRootPx = cvPx;
  const cvTipPx = cvPx * 0.58;
  const xFinLE_root = xTailTE - cvRootPx;
  const xFinDorsal = xFinLE_root - cvRootPx * 0.35;
  const xFinLE_tip = xTailTE - cvTipPx;

  const chRootPx = chPx;
  const chTipPx = chPx * 0.60;
  const xH_root_LE = xTailTE - chRootPx;
  const xH_root_TE = xTailTE;
  const xH_tip_LE = xH_root_LE + chRootPx * 0.20;
  const xH_tip_TE = xH_tip_LE + chTipPx;

  // Poziom zamocowania skrzydła (dolnopłat / średniopłat / górnopłat)
  const wingY_rel = wingConfig === 'high' || wingConfig === 'braced_high' ? -dPx * 0.44 : (wingConfig === 'mid' ? 0 : dPx * 0.38);
  const groundY_rel = dPx * 0.52 + dPx * 0.40; // Linia kół podwozia względem osi kadłuba
  const wheelR = Math.max(6.5, dPx * 0.16);
  const xNoseGear = xNose + lPx * 0.14;
  const xMainGear = xNoseGear + wheelbasePx;

  // Geometria powierzchni sterowych spływu: Klapy (Flaps) i Lotki (Ailerons)
  const cs = (geom && geom.control_surfaces) ? geom.control_surfaces : null;
  const isFlaperon = cs ? Boolean(cs.is_flaperon) : false;
  const eta_f_in = cs ? Number(cs.flaps.eta_in) : Math.max(0.08, d / b);
  const eta_f_out = cs ? Number(cs.flaps.eta_out) : 0.70;
  const cf_c = cs ? Number(cs.flaps.cf_over_c) : 0.25;

  const eta_a_in = cs ? Number(cs.ailerons.eta_in) : (eta_f_out + 0.015);
  const eta_a_out = cs ? Number(cs.ailerons.eta_out) : 0.96;
  const ca_c = cs ? Number(cs.ailerons.ca_over_c) : 0.22;

  function wLE_X(etaVal) {
    return xNose + xWingLE + etaVal * sweepOffsetPx;
  }
  function wChord(etaVal) {
    return crPx + etaVal * (ctPx - crPx);
  }
  function wTE_X(etaVal) {
    return wLE_X(etaVal) + wChord(etaVal);
  }
  function flapH_X(etaVal) {
    return wLE_X(etaVal) + (1.0 - cf_c) * wChord(etaVal);
  }
  function aileronH_X(etaVal) {
    return wLE_X(etaVal) + (1.0 - ca_c) * wChord(etaVal);
  }

  // Środek Ciężkości (ŚM) z bilansu masowego
  const xCgRel = (fullResults && fullResults.balance && fullResults.balance.x_lemac_m)
    ? (fullResults.balance.x_lemac_m - (fullResults.balance.x_le_wing_m || 0) + mac * 0.28) * pxPerMeter
    : (xWingLE + macPx * 0.28);
  const xCgAbs = xNose + (fullResults && fullResults.balance && fullResults.balance.arms && fullResults.balance.arms.wing
    ? fullResults.balance.arms.wing * pxPerMeter
    : (xWingLE + macPx * 0.28));

  // Funkcja pomocnicza: Linia wymiarowa pozioma zgodna z PN-EN ISO 129
  // Pomocnicze linie wystają 2.5 mm (7.5 px) poza grot, brak jednostki mm, liczba wymiarowa 1.5 mm nad linią
  function dimHorizontal(x1, x2, yCont1, yCont2, yDim, textVal, isDiameter = false) {
    const ext = 7.5;
    const s1 = yDim > yCont1 ? 1 : -1;
    const s2 = yDim > yCont2 ? 1 : -1;
    const xm = (x1 + x2) / 2;
    const dispVal = isDiameter ? `⌀${textVal}` : `${textVal}`;
    return `
      <g class="iso-dim">
        <line x1="${x1.toFixed(1)}" y1="${yCont1.toFixed(1)}" x2="${x1.toFixed(1)}" y2="${(yDim + s1 * ext).toFixed(1)}" stroke="#000" stroke-width="0.8"/>
        <line x1="${x2.toFixed(1)}" y1="${yCont2.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${(yDim + s2 * ext).toFixed(1)}" stroke="#000" stroke-width="0.8"/>
        <line x1="${x1.toFixed(1)}" y1="${yDim.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${yDim.toFixed(1)}" stroke="#000" stroke-width="0.8" marker-start="url(#iso-arrow-start)" marker-end="url(#iso-arrow-end)"/>
        <text x="${xm.toFixed(1)}" y="${(yDim - 4.5).toFixed(1)}" text-anchor="middle" font-size="11.5" font-style="italic" font-family="'ISOCPEUR', 'Arial', sans-serif" fill="#000">${dispVal}</text>
      </g>`;
  }

  // Funkcja pomocnicza: Linia wymiarowa pionowa zgodna z PN-EN ISO 129
  // Liczba obrócona o 90° w lewo, czytana od dołu do góry
  function dimVertical(y1, y2, xCont1, xCont2, xDim, textVal, isDiameter = false) {
    const ext = 7.5;
    const s1 = xDim > xCont1 ? 1 : -1;
    const s2 = xDim > xCont2 ? 1 : -1;
    const ym = (y1 + y2) / 2;
    const dispVal = isDiameter ? `⌀${textVal}` : `${textVal}`;
    return `
      <g class="iso-dim">
        <line x1="${xCont1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${(xDim + s1 * ext).toFixed(1)}" y2="${y1.toFixed(1)}" stroke="#000" stroke-width="0.8"/>
        <line x1="${xCont2.toFixed(1)}" y1="${y2.toFixed(1)}" x2="${(xDim + s2 * ext).toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#000" stroke-width="0.8"/>
        <line x1="${xDim.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${xDim.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#000" stroke-width="0.8" marker-start="url(#iso-arrow-start)" marker-end="url(#iso-arrow-end)"/>
        <text x="${(xDim - 5).toFixed(1)}" y="${ym.toFixed(1)}" text-anchor="middle" font-size="11.5" font-style="italic" font-family="'ISOCPEUR', 'Arial', sans-serif" fill="#000" transform="rotate(-90, ${(xDim - 5).toFixed(1)}, ${ym.toFixed(1)})">${dispVal}</text>
      </g>`;
  }

  // Funkcja pomocnicza: Odnośnik pozycji wg EN ISO 6433 (ZUT / MEiL PW)
  // Koło o stałej średnicy 24 px (8 mm) z cienką linią, linia odniesienia zakończona czarną kropką na części
  function bubbleCallout(itemNum, dotX, dotY, bubbleX, bubbleY) {
    const r = 11.5;
    // Wektor od środka kółka do kropki
    const dx = dotX - bubbleX;
    const dy = dotY - bubbleY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const borderX = bubbleX + (dx / dist) * r;
    const borderY = bubbleY + (dy / dist) * r;
    return `
      <g class="iso-balloon">
        <line x1="${dotX.toFixed(1)}" y1="${dotY.toFixed(1)}" x2="${borderX.toFixed(1)}" y2="${borderY.toFixed(1)}" stroke="#000" stroke-width="0.8"/>
        <circle cx="${dotX.toFixed(1)}" cy="${dotY.toFixed(1)}" r="2.2" fill="#000"/>
        <circle cx="${bubbleX.toFixed(1)}" cy="${bubbleY.toFixed(1)}" r="${r}" fill="#ffffff" stroke="#000" stroke-width="0.9"/>
        <text x="${bubbleX.toFixed(1)}" y="${(bubbleY + 4).toFixed(1)}" text-anchor="middle" font-size="11" font-weight="bold" font-family="'ISOCPEUR', 'Arial', sans-serif" fill="#000">${itemNum}</text>
      </g>`;
  }

  // Dane projektu do tabliczki rysunkowej
  const projTitle = (fullResults && fullResults.params && fullResults.params.name) ? fullResults.params.name : "Samolot projektowy BIPOL I";
  const m0_val = (fullResults && fullResults.mass && fullResults.mass.m0) ? fullResults.mass.m0 : 0;
  const m0_str = m0_val > 0 ? `${m0_val.toFixed(1)} kg` : "--- kg";
  const brk = (fullResults && fullResults.mass && fullResults.mass.breakdown) ? fullResults.mass.breakdown : {
    m_wing: 120, m_fuselage: 110, m_tail: 25, m_propulsion: 140, m_gear: 45, m_systems: 60
  };
  const todayStr = new Date().toISOString().slice(0, 10);
  const studentName = (fullResults && fullResults.params && fullResults.params.student_name) ? fullResults.params.student_name : "Inż. Projektant BIPOL";

  // Wymiary tabliczki ZPK MEiL PW A3Z (180 mm szerokości = 540 px, 62 mm tabliczka główna = 186 px, 49 mm wykaz części = 147 px)
  const tbW = 540;
  const tbH_main = 186;
  const tbH_bom = 147;
  const tbX = frameR - tbW; // 1230 - 540 = 690
  const tbY = frameB - tbH_main; // 861 - 186 = 675
  const bomY = tbY - tbH_bom; // 675 - 147 = 528

  const svgContent = `
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; width:100%; margin-bottom:0.5rem; padding:0.45rem 0.75rem; background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; font-size:0.8rem; color:#1e293b;">
    <div>
      <strong>Normy:</strong> PN-EN ISO 128 (linie) &bull; PN-EN ISO 129 (wymiarowanie w <code>[mm]</code> bez miana) &bull; PN-EN ISO 5456-2 (<strong>metoda E</strong>) &bull; EN ISO 6433 (odnośniki części) &bull; Tabliczka złożeniowa <strong>A3Z ZPK MEiL PW</strong>
    </div>
    <div style="display:flex; gap:0.5rem; align-items:center;">
      <span style="font-weight:600; color:#0369a1;">Podziałka: ${scaleLabel}</span>
      <button type="button" onclick="openStandaloneCADWindow()" class="btn" style="padding:0.35rem 0.8rem; font-size:0.76rem; background:#0f172a; color:#fff; border:none; border-radius:4px; cursor:pointer; font-weight:600; white-space:nowrap;">
        🖨️ Otwórz pełny arkusz A3 CAD do druku (PDF)
      </button>
    </div>
  </div>
  <svg id="cadSvgSheet" viewBox="0 0 ${sheetW} ${sheetH}" xmlns="http://www.w3.org/2000/svg" style="display:block; width:100%; height:auto; background:#ffffff; font-family:'ISOCPEUR', 'Arial', sans-serif; border:1px solid #94a3b8; box-shadow:0 2px 8px rgba(0,0,0,0.10);">
    <defs>
      <!-- Groty wymiarowe zamknięte i zaczernione, smukłe 15° wg PN-EN ISO 129 -->
      <marker id="iso-arrow-start" viewBox="0 0 12 6" refX="0" refY="3" markerWidth="10" markerHeight="5" orient="auto">
        <path d="M 0 3 L 11 0.6 L 11 5.4 Z" fill="#000000"/>
      </marker>
      <marker id="iso-arrow-end" viewBox="0 0 12 6" refX="12" refY="3" markerWidth="10" markerHeight="5" orient="auto">
        <path d="M 12 3 L 1 0.6 L 1 5.4 Z" fill="#000000"/>
      </marker>
    </defs>

    <!-- 1. ARKUSZ A3 (420 x 297 mm) I ZNORMALIZOWANA RAMKA RYSUNKOWA PN-EN ISO 5457 (margines lewy 20 mm, pozostałe 10 mm) -->
    <rect x="0" y="0" width="${sheetW}" height="${sheetH}" fill="#ffffff" stroke="#64748b" stroke-width="1"/>
    <rect x="${frameL}" y="${frameT}" width="${frameR - frameL}" height="${frameB - frameT}" fill="none" stroke="#000000" stroke-width="2.2"/>

    <!-- Znaki centrowania wg PN-EN ISO 5457 na 4 krawędziach arkusza -->
    <line x1="630" y1="0" x2="630" y2="15" stroke="#000" stroke-width="1.8"/>
    <line x1="630" y1="876" x2="630" y2="891" stroke="#000" stroke-width="1.8"/>
    <line x1="0" y1="445.5" x2="15" y2="445.5" stroke="#000" stroke-width="1.8"/>
    <line x1="1245" y1="445.5" x2="1260" y2="445.5" stroke="#000" stroke-width="1.8"/>

    <!-- Znaki przycięcia arkusza w 4 narożach -->
    <path d="M 0,15 L 15,15 L 15,0" fill="none" stroke="#64748b" stroke-width="0.8"/>
    <path d="M 1260,15 L 1245,15 L 1245,0" fill="none" stroke="#64748b" stroke-width="0.8"/>
    <path d="M 0,876 L 15,876 L 15,891" fill="none" stroke="#64748b" stroke-width="0.8"/>
    <path d="M 1260,876 L 1245,876 L 1245,891" fill="none" stroke="#64748b" stroke-width="0.8"/>

    <!-- Siatka stref podziałowych arkusza wg ISO 5457 (kolumny 1..8 u góry/dołu, wiersze A..F po bokach) -->
    <g font-size="8" fill="#475569" text-anchor="middle">
      <text x="135" y="22">1</text><text x="285" y="22">2</text><text x="435" y="22">3</text><text x="585" y="22">4</text>
      <text x="735" y="22">5</text><text x="885" y="22">6</text><text x="1035" y="22">7</text><text x="1185" y="22">8</text>
      <text x="35" y="105">A</text><text x="35" y="255">B</text><text x="35" y="405">C</text>
      <text x="35" y="555">D</text><text x="35" y="705">E</text><text x="35" y="835">F</text>
    </g>

    <!-- ========================================================================= -->
    <!-- RZUT 1: RZUT GŁÓWNY (WIDOK Z LEWEGO BOKU) - Góra Lewo                     -->
    <!-- ========================================================================= -->
    <g id="view-side">
      <!-- Oś symetrii kadłuba (linia punktowa cienka wystająca dokładnie 4 mm = 12 px za kontur) -->
      <line x1="${xNose - 12}" y1="${ySideAxis}" x2="${xNose + lPx + 12}" y2="${ySideAxis}" stroke="#000" stroke-width="0.8" stroke-dasharray="22,3,2,3"/>

      <!-- Zarys kadłuba (linia ciągła gruba 2.2 px) -->
      <path d="M ${xNose} ${ySideAxis + dPx * 0.08}
               Q ${xNose + lPx * 0.06} ${ySideAxis - dPx * 0.36}, ${xNose + lPx * 0.16} ${ySideAxis - dPx * 0.38}
               L ${xNose + lPx * 0.25} ${ySideAxis - dPx * 0.56}
               L ${xNose + lPx * 0.44} ${ySideAxis - dPx * 0.52}
               L ${xNose + lPx} ${ySideAxis - dPx * 0.15}
               L ${xNose + lPx} ${ySideAxis + dPx * 0.08}
               L ${xNose + lPx * 0.48} ${ySideAxis + dPx * 0.48}
               L ${xNose + lPx * 0.12} ${ySideAxis + dPx * 0.48}
               Q ${xNose + lPx * 0.03} ${ySideAxis + dPx * 0.40}, ${xNose} ${ySideAxis + dPx * 0.08} Z"
            fill="#ffffff" stroke="#000000" stroke-width="2.2" stroke-linejoin="round"/>

      <!-- Oszklenie kabiny i podział owiewki (linia cienka) -->
      <path d="M ${xNose + lPx * 0.16} ${ySideAxis - dPx * 0.38}
               L ${xNose + lPx * 0.25} ${ySideAxis - dPx * 0.56}
               L ${xNose + lPx * 0.42} ${ySideAxis - dPx * 0.52}
               L ${xNose + lPx * 0.40} ${ySideAxis - dPx * 0.20}
               L ${xNose + lPx * 0.16} ${ySideAxis - dPx * 0.20} Z"
            fill="none" stroke="#000000" stroke-width="1.0"/>
      <line x1="${xNose + lPx * 0.26}" y1="${ySideAxis - dPx * 0.55}" x2="${xNose + lPx * 0.26}" y2="${ySideAxis - dPx * 0.20}" stroke="#000" stroke-width="0.9"/>

      <!-- Profil usterzenia poziomego na rzucie z boku -->
      <polygon points="${xH_root_LE.toFixed(1)},${(ySideAxis - dPx * 0.16).toFixed(1)}
                       ${(xH_root_LE + chRootPx * 0.30).toFixed(1)},${(ySideAxis - dPx * 0.16 - chRootPx * 0.08).toFixed(1)}
                       ${xH_root_TE.toFixed(1)},${(ySideAxis - dPx * 0.16).toFixed(1)}
                       ${(xH_root_LE + chRootPx * 0.35).toFixed(1)},${(ySideAxis - dPx * 0.16 + chRootPx * 0.04).toFixed(1)}"
               fill="#ffffff" stroke="#000000" stroke-width="1.8"/>

      <!-- Usterzenie pionowe (statecznik + ster kierunku z płetwą grzbietową na ogonie) -->
      <polygon points="${xFinDorsal.toFixed(1)},${(ySideAxis - dPx * 0.20).toFixed(1)}
                       ${xFinLE_root.toFixed(1)},${(ySideAxis - dPx * 0.26).toFixed(1)}
                       ${xFinLE_tip.toFixed(1)},${(ySideAxis - dPx * 0.20 - hvPx).toFixed(1)}
                       ${xTailTE.toFixed(1)},${(ySideAxis - dPx * 0.20 - hvPx).toFixed(1)}
                       ${xTailTE.toFixed(1)},${(ySideAxis - dPx * 0.15).toFixed(1)}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2" stroke-linejoin="round"/>
      <!-- Linia zawiasu steru kierunku -->
      <line x1="${(xTailTE - cvTipPx * 0.40).toFixed(1)}" y1="${(ySideAxis - dPx * 0.20 - hvPx).toFixed(1)}"
            x2="${(xTailTE - cvRootPx * 0.35).toFixed(1)}" y2="${(ySideAxis - dPx * 0.15).toFixed(1)}" stroke="#000" stroke-width="0.9"/>
      <!-- Klapka wyważająca steru kierunku (trymer) -->
      <rect x="${(xTailTE - 2.5).toFixed(1)}" y="${(ySideAxis - dPx * 0.20 - hvPx * 0.65).toFixed(1)}" width="2.5" height="${(hvPx * 0.30).toFixed(1)}" fill="#000" stroke="#000"/>

      <!-- Profil skrzydła na rzucie z boku -->
      <path d="M ${xNose + xWingLE} ${ySideAxis + wingY_rel}
               Q ${xNose + xWingLE + crPx * 0.30} ${ySideAxis + wingY_rel - crPx * 0.15}, ${xNose + xWingLE + crPx} ${ySideAxis + wingY_rel + crPx * 0.02}
               Q ${xNose + xWingLE + crPx * 0.35} ${ySideAxis + wingY_rel + crPx * 0.06}, ${xNose + xWingLE} ${ySideAxis + wingY_rel} Z"
            fill="#ffffff" stroke="#000000" stroke-width="2.2"/>

      <!-- Zastrzał skrzydła (jeśli górnopłat zastrzałowy) -->
      ${wingConfig === 'braced_high' ? `
        <line x1="${xNose + xWingLE + crPx * 0.38}" y1="${ySideAxis + dPx * 0.44}" x2="${xNose + xWingLE + crPx * 0.38}" y2="${ySideAxis + wingY_rel}" stroke="#000" stroke-width="2.0"/>
      ` : ''}

      <!-- Oznaczenie Środka Ciężkości (ŚM) z symbolem 4-ćwiartkowym -->
      <g transform="translate(${(xNose + xCgRel).toFixed(1)}, ${(ySideAxis + wingY_rel + 3).toFixed(1)})">
        <circle cx="0" cy="0" r="6" fill="#fff" stroke="#000" stroke-width="0.9"/>
        <path d="M 0,0 L 0,-6 A 6,6 0 0,1 6,0 Z" fill="#000"/>
        <path d="M 0,0 L -6,0 A 6,6 0 0,1 0,6 Z" fill="#000"/>
        <line x1="0" y1="-14" x2="0" y2="14" stroke="#000" stroke-width="0.8" stroke-dasharray="4,2"/>
        <text x="9" y="-4" font-size="8.5" font-weight="bold" fill="#000">ŚM</text>
      </g>

      <!-- Podwozie przednie i koło z osiami punktowymi -->
      <line x1="${xNoseGear}" y1="${ySideAxis + dPx * 0.44}" x2="${xNoseGear}" y2="${ySideAxis + groundY_rel}" stroke="#000" stroke-width="2.0"/>
      <circle cx="${xNoseGear}" cy="${ySideAxis + groundY_rel}" r="${wheelR * 0.85}" fill="#ffffff" stroke="#000" stroke-width="2.0"/>
      <circle cx="${xNoseGear}" cy="${ySideAxis + groundY_rel}" r="${wheelR * 0.35}" fill="#ffffff" stroke="#000" stroke-width="1.0"/>
      <line x1="${xNoseGear - wheelR - 5}" y1="${ySideAxis + groundY_rel}" x2="${xNoseGear + wheelR + 5}" y2="${ySideAxis + groundY_rel}" stroke="#000" stroke-width="0.75" stroke-dasharray="8,2,1.5,2"/>
      <line x1="${xNoseGear}" y1="${ySideAxis + groundY_rel - wheelR - 5}" x2="${xNoseGear}" y2="${ySideAxis + groundY_rel + wheelR + 5}" stroke="#000" stroke-width="0.75" stroke-dasharray="8,2,1.5,2"/>

      <!-- Podwozie główne i koło z osiami punktowymi -->
      <line x1="${xMainGear - 5}" y1="${ySideAxis + dPx * 0.46}" x2="${xMainGear}" y2="${ySideAxis + groundY_rel}" stroke="#000" stroke-width="2.2"/>
      <circle cx="${xMainGear}" cy="${ySideAxis + groundY_rel}" r="${wheelR}" fill="#ffffff" stroke="#000" stroke-width="2.2"/>
      <circle cx="${xMainGear}" cy="${ySideAxis + groundY_rel}" r="${wheelR * 0.4}" fill="#ffffff" stroke="#000" stroke-width="1.0"/>
      <line x1="${xMainGear - wheelR - 5}" y1="${ySideAxis + groundY_rel}" x2="${xMainGear + wheelR + 5}" y2="${ySideAxis + groundY_rel}" stroke="#000" stroke-width="0.75" stroke-dasharray="8,2,1.5,2"/>
      <line x1="${xMainGear}" y1="${ySideAxis + groundY_rel - wheelR - 5}" x2="${xMainGear}" y2="${ySideAxis + groundY_rel + wheelR + 5}" stroke="#000" stroke-width="0.75" stroke-dasharray="8,2,1.5,2"/>

      <!-- Linia bazowa ziemi (poziom postojowy) -->
      <line x1="${xNoseGear - 28}" y1="${ySideAxis + groundY_rel + wheelR}" x2="${xMainGear + 45}" y2="${ySideAxis + groundY_rel + wheelR}" stroke="#64748b" stroke-width="0.8" stroke-dasharray="6,3"/>

      <!-- Zespół napędowy zależnie od umiejscowienia i typu -->
      ${engineLoc === 'nose' ? `
        <!-- Kołpak śmigła i tarcza obrotu na dziobie -->
        <polygon points="${xNose},${ySideAxis - 6} ${xNose - 12},${ySideAxis} ${xNose},${ySideAxis + 6}" fill="#fff" stroke="#000" stroke-width="1.8"/>
        <line x1="${xNose - 4}" y1="${ySideAxis - propR}" x2="${xNose - 4}" y2="${ySideAxis + propR}" stroke="#000" stroke-width="1.6" stroke-dasharray="14,3,2,3"/>
      ` : (engineLoc === 'wing' ? `
        <!-- Gondola silnika na skrzydle -->
        <rect x="${xNose + xWingLE - crPx * 0.18}" y="${ySideAxis + wingY_rel - dPx * 0.15}" width="${crPx * 0.95}" height="${dPx * 0.45}" rx="${dPx * 0.2}" fill="#fff" stroke="#000" stroke-width="2.0"/>
        <polygon points="${xNose + xWingLE - crPx * 0.18},${ySideAxis + wingY_rel - 4} ${xNose + xWingLE - crPx * 0.18 - 8},${ySideAxis + wingY_rel + dPx * 0.08} ${xNose + xWingLE - crPx * 0.18},${ySideAxis + wingY_rel + dPx * 0.16}" fill="#fff" stroke="#000" stroke-width="1.6"/>
      ` : `
        <!-- Gondola tylna przy kadłubie -->
        <rect x="${xNose + lPx * 0.65}" y="${ySideAxis - dPx * 0.55}" width="${lPx * 0.22}" height="${dPx * 0.38}" rx="${dPx * 0.15}" fill="#fff" stroke="#000" stroke-width="2.0"/>
      `)}

      <!-- Wymiary na rzucie głównym wg PN-EN ISO 129 -->
      <!-- Baza podwozia Lp -->
      ${dimHorizontal(xNoseGear, xMainGear, ySideAxis + groundY_rel + wheelR, ySideAxis + groundY_rel + wheelR, ySideAxis + groundY_rel + wheelR + 28, wheelbase_mm)}
      <!-- Długość całkowita L u góry -->
      ${dimHorizontal(xNose, xNose + lPx, ySideAxis, ySideAxis - dPx * 0.20 - hvPx, ySideAxis - dPx * 0.20 - hvPx - 34, l_mm)}
      <!-- Wysokość całkowita Htot z lewej strony -->
      ${dimVertical(ySideAxis - dPx * 0.20 - hvPx, ySideAxis + groundY_rel + wheelR, xNose, xNoseGear, xNose - 48, h_tot_mm)}

      <!-- Odnośniki pozycji części (EN ISO 6433 & ZUT) -->
      ${bubbleCallout(2, xNose + lPx * 0.52, ySideAxis, xNose + lPx * 0.52 - 35, ySideAxis - 65)}
      ${bubbleCallout(3, xTailTE - cvRootPx * 0.35, ySideAxis - dPx * 0.20 - hvPx * 0.55, xTailTE + 38, ySideAxis - dPx * 0.20 - hvPx * 0.55)}
      ${bubbleCallout(4, engineLoc === 'nose' ? xNose - 2 : xNose + xWingLE, ySideAxis, xNose - 42, ySideAxis - 48)}
      ${bubbleCallout(5, xMainGear, ySideAxis + groundY_rel, xMainGear + 45, ySideAxis + groundY_rel + 30)}
      ${bubbleCallout(6, xNose + lPx * 0.32, ySideAxis - dPx * 0.42, xNose + lPx * 0.32, ySideAxis - dPx * 0.56 - 32)}
    </g>

    <!-- ========================================================================= -->
    <!-- RZUT 2: RZUT Z GÓRY - DOKŁADNIE POD rzutem głównym (wspólna baza osi X!)   -->
    <!-- ========================================================================= -->
    <g id="view-top">
      <!-- Oś symetrii podłużna kadłuba (linia punktowa cienka wystająca 12 px za dziób i ogon) -->
      <line x1="${xNose - 12}" y1="${yTopAxis}" x2="${xNose + lPx + 12}" y2="${yTopAxis}" stroke="#000" stroke-width="0.8" stroke-dasharray="22,3,2,3"/>

      <!-- Skrzydło lewe i prawe (obrys trapezowy z mechanizacją) -->
      <!-- Prawe skrzydło (górna połowa na rysunku) -->
      <polygon points="${xNose + xWingLE},${yTopAxis}
                       ${xNose + xWingLE + sweepOffsetPx},${yTopAxis - bPx / 2}
                       ${xNose + xWingLE + sweepOffsetPx + ctPx},${yTopAxis - bPx / 2}
                       ${xNose + xWingLE + crPx},${yTopAxis}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2" stroke-linejoin="round"/>
      <!-- Lewe skrzydło (dolna połowa na rysunku) -->
      <polygon points="${xNose + xWingLE},${yTopAxis}
                       ${xNose + xWingLE + sweepOffsetPx},${yTopAxis + bPx / 2}
                       ${xNose + xWingLE + sweepOffsetPx + ctPx},${yTopAxis + bPx / 2}
                       ${xNose + xWingLE + crPx},${yTopAxis}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2" stroke-linejoin="round"/>

      <!-- Główny dźwigar skrzydła (linia kreskowa cienka w 25% cięciwy) -->
      <line x1="${xNose + xWingLE + crPx * 0.25}" y1="${yTopAxis - bPx / 2}"
            x2="${xNose + xWingLE + sweepOffsetPx + ctPx * 0.25}" y2="${yTopAxis - bPx / 2}" stroke="#000" stroke-width="0.8" stroke-dasharray="6,3"/>
      <line x1="${xNose + xWingLE + crPx * 0.25}" y1="${yTopAxis + bPx / 2}"
            x2="${xNose + xWingLE + sweepOffsetPx + ctPx * 0.25}" y2="${yTopAxis + bPx / 2}" stroke="#000" stroke-width="0.8" stroke-dasharray="6,3"/>

      <!-- Mechanizacja krawędzi spływu: Klapy wewnętrzne i lotki zewnętrzne (PN-EN ISO 128 linie cienkie 0.9 px) -->
      <!-- Prawe skrzydło (góra) -->
      <!-- 1. Klapa wewnętrzna (od kadłuba eta_f_in do eta_f_out) -->
      <line x1="${flapH_X(eta_f_in).toFixed(1)}" y1="${(yTopAxis - eta_f_in * bPx / 2).toFixed(1)}"
            x2="${flapH_X(eta_f_out).toFixed(1)}" y2="${(yTopAxis - eta_f_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="1.0"/>
      <line x1="${flapH_X(eta_f_in).toFixed(1)}" y1="${(yTopAxis - eta_f_in * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_f_in).toFixed(1)}" y2="${(yTopAxis - eta_f_in * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>
      <line x1="${flapH_X(eta_f_out).toFixed(1)}" y1="${(yTopAxis - eta_f_out * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_f_out).toFixed(1)}" y2="${(yTopAxis - eta_f_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>

      <!-- 2. Lotka zewnętrzna (od eta_a_in do eta_a_out) -->
      <line x1="${aileronH_X(eta_a_in).toFixed(1)}" y1="${(yTopAxis - eta_a_in * bPx / 2).toFixed(1)}"
            x2="${aileronH_X(eta_a_out).toFixed(1)}" y2="${(yTopAxis - eta_a_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="1.0"/>
      <line x1="${aileronH_X(eta_a_in).toFixed(1)}" y1="${(yTopAxis - eta_a_in * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_a_in).toFixed(1)}" y2="${(yTopAxis - eta_a_in * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>
      <line x1="${aileronH_X(eta_a_out).toFixed(1)}" y1="${(yTopAxis - eta_a_out * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_a_out).toFixed(1)}" y2="${(yTopAxis - eta_a_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>

      <!-- Napisy techniczne na prawym skrzydle -->
      ${!isFlaperon ? `
        <text x="${((flapH_X(eta_f_in) + flapH_X(eta_f_out))/2 + 6).toFixed(1)}" y="${(yTopAxis - (eta_f_in + eta_f_out) * bPx / 4 + 3).toFixed(1)}" font-size="7.5" font-style="italic" fill="#0f172a" text-anchor="middle">Klapa</text>
        <text x="${((aileronH_X(eta_a_in) + aileronH_X(eta_a_out))/2 + 6).toFixed(1)}" y="${(yTopAxis - (eta_a_in + eta_a_out) * bPx / 4 + 3).toFixed(1)}" font-size="7.5" font-style="italic" fill="#0f172a" text-anchor="middle">Lotka</text>
      ` : `
        <text x="${((flapH_X(eta_f_in) + flapH_X(eta_f_out))/2 + 6).toFixed(1)}" y="${(yTopAxis - (eta_f_in + eta_f_out) * bPx / 4 + 3).toFixed(1)}" font-size="7.5" font-style="italic" fill="#5b21b6" text-anchor="middle">Klapolotka (Flaperon)</text>
      `}

      <!-- Lewe skrzydło (dół - symetria) -->
      <!-- 1. Klapa wewnętrzna -->
      <line x1="${flapH_X(eta_f_in).toFixed(1)}" y1="${(yTopAxis + eta_f_in * bPx / 2).toFixed(1)}"
            x2="${flapH_X(eta_f_out).toFixed(1)}" y2="${(yTopAxis + eta_f_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="1.0"/>
      <line x1="${flapH_X(eta_f_in).toFixed(1)}" y1="${(yTopAxis + eta_f_in * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_f_in).toFixed(1)}" y2="${(yTopAxis + eta_f_in * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>
      <line x1="${flapH_X(eta_f_out).toFixed(1)}" y1="${(yTopAxis + eta_f_out * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_f_out).toFixed(1)}" y2="${(yTopAxis + eta_f_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>

      <!-- 2. Lotka zewnętrzna -->
      <line x1="${aileronH_X(eta_a_in).toFixed(1)}" y1="${(yTopAxis + eta_a_in * bPx / 2).toFixed(1)}"
            x2="${aileronH_X(eta_a_out).toFixed(1)}" y2="${(yTopAxis + eta_a_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="1.0"/>
      <line x1="${aileronH_X(eta_a_in).toFixed(1)}" y1="${(yTopAxis + eta_a_in * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_a_in).toFixed(1)}" y2="${(yTopAxis + eta_a_in * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>
      <line x1="${aileronH_X(eta_a_out).toFixed(1)}" y1="${(yTopAxis + eta_a_out * bPx / 2).toFixed(1)}"
            x2="${wTE_X(eta_a_out).toFixed(1)}" y2="${(yTopAxis + eta_a_out * bPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>

      <!-- Wyznaczenie Średniej Cięciwy Aerodynamicznej (ŚDA / MAC) na lewym skrzydle -->
      <g>
        <line x1="${xNose + xWingLE + sweepOffsetPx * (yMac / (b / 2))}" y1="${yTopAxis + yMacPx}"
              x2="${xNose + xWingLE + sweepOffsetPx * (yMac / (b / 2)) + macPx}" y2="${yTopAxis + yMacPx}" stroke="#0284c7" stroke-width="1.6"/>
        <circle cx="${xNose + xWingLE + sweepOffsetPx * (yMac / (b / 2)) + macPx * 0.25}" cy="${yTopAxis + yMacPx}" r="2.5" fill="#0284c7"/>
        <text x="${xNose + xWingLE + sweepOffsetPx * (yMac / (b / 2)) + macPx * 0.5}" y="${yTopAxis + yMacPx - 4}" font-size="8" font-style="italic" fill="#0284c7">ŚDA (${mac_mm})</text>
      </g>

      <!-- Usterzenie poziome (prawe i lewe) na rzucie z góry -->
      <polygon points="${xH_root_LE.toFixed(1)},${yTopAxis}
                       ${xH_tip_LE.toFixed(1)},${(yTopAxis - bhPx / 2).toFixed(1)}
                       ${xH_tip_TE.toFixed(1)},${(yTopAxis - bhPx / 2).toFixed(1)}
                       ${xH_root_TE.toFixed(1)},${yTopAxis}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2" stroke-linejoin="round"/>
      <polygon points="${xH_root_LE.toFixed(1)},${yTopAxis}
                       ${xH_tip_LE.toFixed(1)},${(yTopAxis + bhPx / 2).toFixed(1)}
                       ${xH_tip_TE.toFixed(1)},${(yTopAxis + bhPx / 2).toFixed(1)}
                       ${xH_root_TE.toFixed(1)},${yTopAxis}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2" stroke-linejoin="round"/>
      <!-- Linia zawiasu steru wysokości -->
      <line x1="${(xH_root_LE + chRootPx * 0.65).toFixed(1)}" y1="${(yTopAxis - bhPx / 2).toFixed(1)}"
            x2="${(xH_root_LE + chRootPx * 0.65).toFixed(1)}" y2="${(yTopAxis + bhPx / 2).toFixed(1)}" stroke="#000" stroke-width="0.9"/>

      <!-- Kadłub w rzucie z góry (nakładany na nasadę skrzydła) -->
      <path d="M ${xNose} ${yTopAxis}
               C ${xNose + lPx * 0.08} ${yTopAxis - dPx * 0.52}, ${xNose + lPx * 0.38} ${yTopAxis - dPx * 0.52}, ${xNose + lPx} ${yTopAxis - dPx * 0.08}
               L ${xNose + lPx} ${yTopAxis + dPx * 0.08}
               C ${xNose + lPx * 0.38} ${yTopAxis + dPx * 0.52}, ${xNose + lPx * 0.08} ${yTopAxis + dPx * 0.52}, ${xNose} ${yTopAxis} Z"
            fill="#ffffff" stroke="#000000" stroke-width="2.2"/>

      <!-- Zarys usterzenia pionowego w osi kadłuba -->
      <line x1="${xFinLE_root.toFixed(1)}" y1="${yTopAxis}" x2="${xTailTE.toFixed(1)}" y2="${yTopAxis}" stroke="#000" stroke-width="2.6"/>

      <!-- Ponowne nałożenie osi symetrii na wierzchu kadłuba -->
      <line x1="${xNose - 12}" y1="${yTopAxis}" x2="${xNose + lPx + 12}" y2="${yTopAxis}" stroke="#000" stroke-width="0.8" stroke-dasharray="22,3,2,3"/>

      <!-- Wymiary na rzucie z góry wg PN-EN ISO 129 -->
      <!-- Rozpiętość b z lewej strony -->
      ${dimVertical(yTopAxis - bPx / 2, yTopAxis + bPx / 2, xNose + xWingLE + sweepOffsetPx, xNose + xWingLE + sweepOffsetPx, xNose - 48, b_mm)}
      <!-- Cięciwa końcowa ct nad górną końcówką -->
      ${dimHorizontal(xNose + xWingLE + sweepOffsetPx, xNose + xWingLE + sweepOffsetPx + ctPx, yTopAxis - bPx / 2, yTopAxis - bPx / 2, yTopAxis - bPx / 2 - 24, ct_mm)}
      <!-- Cięciwa przykadłubowa cr pod dolną końcówką -->
      ${dimHorizontal(xNose + xWingLE, xNose + xWingLE + crPx, yTopAxis + bPx / 2, yTopAxis + bPx / 2, yTopAxis + bPx / 2 + 28, cr_mm)}
      <!-- Rozpiętość usterzenia poziomego bh z prawej strony -->
      ${dimVertical(yTopAxis - bhPx / 2, yTopAxis + bhPx / 2, xH_tip_TE, xH_tip_TE, xTailTE + 30, bh_mm)}
      <!-- Średnica kadłuba D (ze znakiem ⌀) -->
      ${dimVertical(yTopAxis - dPx * 0.5, yTopAxis + dPx * 0.5, xNose + lPx * 0.22, xNose + lPx * 0.22, xNose + lPx * 0.22 - 38, d_mm, true)}

      <!-- Odnośnik pozycji 1 (Skrzydło) -->
      ${bubbleCallout(1, xNose + xWingLE + crPx * 0.45, yTopAxis - bPx * 0.28, xNose + xWingLE - 35, yTopAxis - bPx * 0.28 - 35)}
    </g>

    <!-- ========================================================================= -->
    <!-- RZUT 3: RZUT Z LEWEJ STRONY (WIDOK OD PRZODU) - Góra Prawo                -->
    <!-- ========================================================================= -->
    <g id="view-front">
      <!-- Osie symetrii: pionowa i pozioma kadłuba (przecinające się długimi kreskami w środku kadłuba) -->
      <line x1="${xFrontAxis}" y1="${ySideAxis - dPx * 0.20 - hvPx - 14}" x2="${xFrontAxis}" y2="${ySideAxis + groundY_rel + wheelR + 14}" stroke="#000" stroke-width="0.8" stroke-dasharray="22,3,2,3"/>
      <line x1="${xFrontAxis - bPx / 2 - 14}" y1="${ySideAxis}" x2="${xFrontAxis + bPx / 2 + 14}" y2="${ySideAxis}" stroke="#000" stroke-width="0.8" stroke-dasharray="22,3,2,3"/>

      <!-- Statecznik pionowy z przodu -->
      <polygon points="${xFrontAxis - 2.8},${ySideAxis - dPx * 0.35}
                       ${xFrontAxis - 1.5},${ySideAxis - dPx * 0.20 - hvPx}
                       ${xFrontAxis + 1.5},${ySideAxis - dPx * 0.20 - hvPx}
                       ${xFrontAxis + 2.8},${ySideAxis - dPx * 0.35}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2"/>

      <!-- Statecznik poziomy z przodu -->
      <rect x="${xFrontAxis - bhPx / 2}" y="${ySideAxis - dPx * 0.20}" width="${bhPx}" height="4.5" fill="#ffffff" stroke="#000000" stroke-width="2.0"/>

      <!-- Skrzydła z uwzględnieniem kąta wzniosu Gamma -->
      <!-- Lewe skrzydło (na rysunku z prawej strony osi) -->
      <polygon points="${xFrontAxis},${ySideAxis + wingY_rel - 3.5}
                       ${xFrontAxis + bPx / 2},${ySideAxis + wingY_rel - dihedralOffsetPx - 2}
                       ${xFrontAxis + bPx / 2},${ySideAxis + wingY_rel - dihedralOffsetPx + 2}
                       ${xFrontAxis},${ySideAxis + wingY_rel + 3.5}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2"/>
      <!-- Prawe skrzydło (na rysunku z lewej strony osi) -->
      <polygon points="${xFrontAxis},${ySideAxis + wingY_rel - 3.5}
                       ${xFrontAxis - bPx / 2},${ySideAxis + wingY_rel - dihedralOffsetPx - 2}
                       ${xFrontAxis - bPx / 2},${ySideAxis + wingY_rel - dihedralOffsetPx + 2}
                       ${xFrontAxis},${ySideAxis + wingY_rel + 3.5}"
               fill="#ffffff" stroke="#000000" stroke-width="2.2"/>

      <!-- Zastrzały w rzucie z przodu (jeśli górnopłat zastrzałowy) -->
      ${wingConfig === 'braced_high' ? `
        <line x1="${xFrontAxis - dPx * 0.45}" y1="${ySideAxis + dPx * 0.42}" x2="${xFrontAxis - bPx * 0.26}" y2="${ySideAxis + wingY_rel - dihedralOffsetPx * 0.5}" stroke="#000" stroke-width="2.0"/>
        <line x1="${xFrontAxis + dPx * 0.45}" y1="${ySideAxis + dPx * 0.42}" x2="${xFrontAxis + bPx * 0.26}" y2="${ySideAxis + wingY_rel - dihedralOffsetPx * 0.5}" stroke="#000" stroke-width="2.0"/>
      ` : ''}

      <!-- Przekrój kadłuba z przodu -->
      <ellipse cx="${xFrontAxis}" cy="${ySideAxis}" rx="${dPx * 0.5}" ry="${dPx * 0.54}" fill="#ffffff" stroke="#000000" stroke-width="2.2"/>
      <line x1="${xFrontAxis - dPx * 0.65}" y1="${ySideAxis}" x2="${xFrontAxis + dPx * 0.65}" y2="${ySideAxis}" stroke="#000" stroke-width="0.8" stroke-dasharray="16,3,2,3"/>

      <!-- Golenie i koła podwozia głównego z przodu -->
      <line x1="${xFrontAxis - dPx * 0.35}" y1="${ySideAxis + dPx * 0.40}" x2="${xFrontAxis - trackPx / 2}" y2="${ySideAxis + groundY_rel}" stroke="#000" stroke-width="2.2"/>
      <line x1="${xFrontAxis + dPx * 0.35}" y1="${ySideAxis + dPx * 0.40}" x2="${xFrontAxis + trackPx / 2}" y2="${ySideAxis + groundY_rel}" stroke="#000" stroke-width="2.2"/>
      <rect x="${xFrontAxis - trackPx / 2 - 3.5}" y="${ySideAxis + groundY_rel - wheelR}" width="7" height="${wheelR * 2}" rx="2" fill="#fff" stroke="#000" stroke-width="2.0"/>
      <rect x="${xFrontAxis + trackPx / 2 - 3.5}" y="${ySideAxis + groundY_rel - wheelR}" width="7" height="${wheelR * 2}" rx="2" fill="#fff" stroke="#000" stroke-width="2.0"/>
      <!-- Koło przednie na osi -->
      <rect x="${xFrontAxis - 2.8}" y="${ySideAxis + groundY_rel - wheelR * 0.85}" width="5.6" height="${wheelR * 1.7}" rx="1.5" fill="#fff" stroke="#000" stroke-width="1.8"/>

      <!-- Śmigło na rzucie z przodu -->
      ${engineType === 'prop' ? `
        <circle cx="${xFrontAxis}" cy="${ySideAxis}" r="${propR}" fill="none" stroke="#000" stroke-width="0.8" stroke-dasharray="12,3,2,3"/>
        <polygon points="${xFrontAxis - 2.5},${ySideAxis - propR * 0.95} ${xFrontAxis + 2.5},${ySideAxis - propR * 0.95} ${xFrontAxis + 3.5},${ySideAxis} ${xFrontAxis - 3.5},${ySideAxis}" fill="#fff" stroke="#000" stroke-width="1.6"/>
        <polygon points="${xFrontAxis - 2.5},${ySideAxis + propR * 0.95} ${xFrontAxis + 2.5},${ySideAxis + propR * 0.95} ${xFrontAxis + 3.5},${ySideAxis} ${xFrontAxis - 3.5},${ySideAxis}" fill="#fff" stroke="#000" stroke-width="1.6"/>
        <circle cx="${xFrontAxis}" cy="${ySideAxis}" r="6.5" fill="#fff" stroke="#000" stroke-width="1.8"/>
      ` : `
        <circle cx="${xFrontAxis}" cy="${ySideAxis}" r="${dPx * 0.28}" fill="none" stroke="#000" stroke-width="1.6"/>
        <circle cx="${xFrontAxis}" cy="${ySideAxis}" r="${dPx * 0.10}" fill="#000" stroke="#000"/>
      `}

      <!-- Wymiary na rzucie z przodu wg PN-EN ISO 129 -->
      <!-- Rozstaw kół podwozia głównego Bp (track) -->
      ${dimHorizontal(xFrontAxis - trackPx / 2, xFrontAxis + trackPx / 2, ySideAxis + groundY_rel + wheelR, ySideAxis + groundY_rel + wheelR, ySideAxis + groundY_rel + wheelR + 28, wheel_track_mm)}
      <!-- Średnica śmigła ze znakiem ⌀ -->
      ${engineType === 'prop' ? dimVertical(ySideAxis - propR, ySideAxis + propR, xFrontAxis, xFrontAxis, xFrontAxis + bPx / 2 + 26, prop_d_mm, true) : ''}
    </g>

    <!-- ========================================================================= -->
    <!-- TABLICZKA RYSUNKOWA ZPK MEiL PW (Formatka A3Z_formatka.pdf)                -->
    <!-- Położenie: prawy dolny róg, x: 690..1230 (szer. 540 = 180mm), y: 528..861 -->
    <!-- ========================================================================= -->
    <g id="zpk-title-block-a3z" transform="translate(${tbX}, ${bomY})">
      <!-- Obramowanie zewnętrzne całego bloku (Wykaz części + Tabliczka główna) -->
      <rect x="0" y="0" width="${tbW}" height="${tbH_main + tbH_bom}" fill="#ffffff" stroke="#000000" stroke-width="2.0"/>

      <!-- ======================================================================= -->
      <!-- CZĘŚĆ GÓRNA: WYKAZ CZĘŚCI (ZŁOŻENIOWY A3Z) - Pozycje rosną w górę!     -->
      <!-- y od 0 do 147 (6 wierszy części po 21 px + nagłówek 21 px)             -->
      <!-- ======================================================================= -->
      <!-- Poziome linie podziału wierszy wykazu części -->
      <line x1="0" y1="21" x2="${tbW}" y2="21" stroke="#000" stroke-width="0.8"/>
      <line x1="0" y1="42" x2="${tbW}" y2="42" stroke="#000" stroke-width="0.8"/>
      <line x1="0" y1="63" x2="${tbW}" y2="63" stroke="#000" stroke-width="0.8"/>
      <line x1="0" y1="84" x2="${tbW}" y2="84" stroke="#000" stroke-width="0.8"/>
      <line x1="0" y1="105" x2="${tbW}" y2="105" stroke="#000" stroke-width="0.8"/>
      <line x1="0" y1="126" x2="${tbW}" y2="126" stroke="#000" stroke-width="1.2"/>
      <line x1="0" y1="147" x2="${tbW}" y2="147" stroke="#000" stroke-width="2.0"/>

      <!-- Pionowe linie kolumn wykazu części wg A3Z_formatka.pdf -->
      <!-- x: 28.5 (Nr), 178.5 (Nazwa), 207 (Zm.), 295.5 (Nr rys.), 331.5 (Lb.szt), 448.5 (Materiał), 540 (Uwagi) -->
      <line x1="28.5" y1="0" x2="28.5" y2="147" stroke="#000" stroke-width="0.9"/>
      <line x1="178.5" y1="0" x2="178.5" y2="147" stroke="#000" stroke-width="0.9"/>
      <line x1="207.0" y1="0" x2="207.0" y2="147" stroke="#000" stroke-width="0.9"/>
      <line x1="295.5" y1="0" x2="295.5" y2="147" stroke="#000" stroke-width="0.9"/>
      <line x1="331.5" y1="0" x2="331.5" y2="147" stroke="#000" stroke-width="0.9"/>
      <line x1="448.5" y1="0" x2="448.5" y2="147" stroke="#000" stroke-width="0.9"/>

      <!-- Nagłówek kolumn wykazu części (y: 126..147) -->
      <g font-size="7.5" font-style="italic" text-anchor="middle" fill="#000">
        <text x="14.25" y="135">Nr/</text><text x="14.25" y="144">Order</text>
        <text x="103.5" y="135">Nazwa części/</text><text x="103.5" y="144">Title</text>
        <text x="192.75" y="135">Zm./</text><text x="192.75" y="144">Rev.</text>
        <text x="251.25" y="135">Nr rys. lub normy/</text><text x="251.25" y="144">Drawing no. or standard</text>
        <text x="313.5" y="135">Lb. szt./</text><text x="313.5" y="144">No. of items</text>
        <text x="390" y="135">Materiał/</text><text x="390" y="144">Material</text>
        <text x="494" y="135">Uwagi/</text><text x="494" y="144">Comments</text>
      </g>

      <!-- Pozycje wykazu części 1..6 (rosną od dołu do góry!) -->
      <g font-size="8.8" fill="#000">
        <!-- Poz. 6 (y: 0..21) -->
        <text x="14.25" y="15" text-anchor="middle">6</text>
        <text x="34" y="15">Wyposażenie i sterowanie</text>
        <text x="192.75" y="15" text-anchor="middle">-</text>
        <text x="251.25" y="15" text-anchor="middle">BIPOL-I-01.06</text>
        <text x="313.5" y="15" text-anchor="middle">1 kpl.</text>
        <text x="390" y="15" text-anchor="middle">Dural / Wiązki / Awionika</text>
        <text x="494" y="15" text-anchor="middle">${(brk.m_systems || 40).toFixed(1)} kg</text>

        <!-- Poz. 5 (y: 21..42) -->
        <text x="14.25" y="36" text-anchor="middle">5</text>
        <text x="34" y="36">Podwozie przednie i główne</text>
        <text x="192.75" y="36" text-anchor="middle">-</text>
        <text x="251.25" y="36" text-anchor="middle">BIPOL-I-01.05</text>
        <text x="313.5" y="36" text-anchor="middle">1 kpl.</text>
        <text x="390" y="36" text-anchor="middle">Stal 30HGSA / Guma</text>
        <text x="494" y="36" text-anchor="middle">${(brk.m_gear || 45).toFixed(1)} kg</text>

        <!-- Poz. 4 (y: 42..63) -->
        <text x="14.25" y="57" text-anchor="middle">4</text>
        <text x="34" y="57">Zespół napędowy z łożem</text>
        <text x="192.75" y="57" text-anchor="middle">-</text>
        <text x="251.25" y="57" text-anchor="middle">BIPOL-I-01.04</text>
        <text x="313.5" y="57" text-anchor="middle">1 kpl.</text>
        <text x="390" y="57" text-anchor="middle">Stop Al / Stal 30HGSA</text>
        <text x="494" y="57" text-anchor="middle">${(brk.m_propulsion || 100).toFixed(1)} kg</text>

        <!-- Poz. 3 (y: 63..84) -->
        <text x="14.25" y="78" text-anchor="middle">3</text>
        <text x="34" y="78">Usterzenie poziome i pionowe</text>
        <text x="192.75" y="78" text-anchor="middle">-</text>
        <text x="251.25" y="78" text-anchor="middle">BIPOL-I-01.03</text>
        <text x="313.5" y="78" text-anchor="middle">1 kpl.</text>
        <text x="390" y="78" text-anchor="middle">Dural PA7 (EN AW-2024)</text>
        <text x="494" y="78" text-anchor="middle">${(brk.m_tail || 25).toFixed(1)} kg</text>

        <!-- Poz. 2 (y: 84..105) -->
        <text x="14.25" y="99" text-anchor="middle">2</text>
        <text x="34" y="99">Kadłub półskorupowy</text>
        <text x="192.75" y="99" text-anchor="middle">-</text>
        <text x="251.25" y="99" text-anchor="middle">BIPOL-I-01.02</text>
        <text x="313.5" y="99" text-anchor="middle">1 kpl.</text>
        <text x="390" y="99" text-anchor="middle">Dural PA7 / Kompozyt</text>
        <text x="494" y="99" text-anchor="middle">${(brk.m_fuselage || 95).toFixed(1)} kg</text>

        <!-- Poz. 1 (y: 105..126) -->
        <text x="14.25" y="120" text-anchor="middle">1</text>
        <text x="34" y="120">Skrzydło (klapy wewn. + lotki zewn.)</text>
        <text x="192.75" y="120" text-anchor="middle">-</text>
        <text x="251.25" y="120" text-anchor="middle">BIPOL-I-01.01</text>
        <text x="313.5" y="120" text-anchor="middle">1 kpl.</text>
        <text x="390" y="120" text-anchor="middle">Dural PA7 (2024-T3) / CFRP</text>
        <text x="494" y="120" text-anchor="middle">${(brk.m_wing || 115).toFixed(1)} kg</text>
      </g>

      <!-- ======================================================================= -->
      <!-- CZĘŚĆ DOLNA: GŁÓWNA TABLICZKA RYSUNKOWA ZPK MEiL PW (y: 147..333)       -->
      <!-- ======================================================================= -->
      <g transform="translate(0, 147)">
        <!-- Linie poziome -->
        <line x1="0" y1="18" x2="444" y2="18" stroke="#000" stroke-width="0.8"/>
        <line x1="0" y1="33" x2="444" y2="33" stroke="#000" stroke-width="0.8"/>
        <line x1="0" y1="48" x2="${tbW}" y2="48" stroke="#000" stroke-width="1.2"/>
        <line x1="0" y1="63" x2="306" y2="63" stroke="#000" stroke-width="0.8"/>
        <line x1="0" y1="78" x2="306" y2="78" stroke="#000" stroke-width="0.8"/>
        <line x1="0" y1="93" x2="306" y2="93" stroke="#000" stroke-width="0.8"/>
        <line x1="0" y1="108" x2="${tbW}" y2="108" stroke="#000" stroke-width="1.2"/>
        <line x1="0" y1="126" x2="306" y2="126" stroke="#000" stroke-width="1.2"/>
        <line x1="306" y1="147" x2="${tbW}" y2="147" stroke="#000" stroke-width="1.2"/>

        <!-- Linie pionowe -->
        <line x1="81" y1="0" x2="81" y2="126" stroke="#000" stroke-width="0.8"/>
        <line x1="132" y1="0" x2="132" y2="126" stroke="#000" stroke-width="0.8"/>
        <line x1="255" y1="0" x2="255" y2="126" stroke="#000" stroke-width="0.8"/>
        <line x1="306" y1="48" x2="306" y2="186" stroke="#000" stroke-width="1.6"/>
        <line x1="369" y1="48" x2="369" y2="108" stroke="#000" stroke-width="0.8"/>
        <line x1="444" y1="0" x2="444" y2="108" stroke="#000" stroke-width="1.2"/>
        <line x1="504" y1="48" x2="504" y2="108" stroke="#000" stroke-width="0.8"/>
        <line x1="504" y1="147" x2="504" y2="186" stroke="#000" stroke-width="0.8"/>

        <!-- Nagłówki sekcji zmian (lewa góra) -->
        <g font-size="6.8" font-style="italic" fill="#000">
          <text x="3" y="10">Nr karty zmiany/</text><text x="3" y="16">No. of revision</text>
          <text x="84" y="10">Ozn. zmiany/</text><text x="84" y="16">Sign. of rev.</text>
          <text x="145" y="10">Zamiast/</text><text x="145" y="16">Instead of</text>
          <text x="260" y="10">Powinno być/</text><text x="260" y="16">Should be</text>
          <text x="375" y="10">Podpis/</text><text x="375" y="16">Signature</text>
          <text x="415" y="10">Data/</text><text x="415" y="16">Date</text>

          <text x="3" y="60">Konstruował/Design by</text>
          <text x="3" y="75">Kreślił/Drawn by</text>
          <text x="3" y="90">Sprawdził/Checked by</text>
          <text x="3" y="105">Zatwierdził/Approved by</text>

          <text x="106" y="121" text-anchor="middle">Data/Date</text>
          <text x="193" y="121" text-anchor="middle">Imię i Nazwisko/Name and Surname</text>
          <text x="280" y="121" text-anchor="middle">Podpis/Signature</text>
        </g>

        <!-- Wpisy personelu projektowego -->
        <g font-size="8.5" fill="#000">
          <text x="84" y="60">${todayStr}</text>
          <text x="136" y="60">${studentName.slice(0, 24)}</text>
          <text x="84" y="75">${todayStr}</text>
          <text x="136" y="75">BIPOL Studio CAD</text>
          <text x="136" y="90">dr inż. / Zakład Samolotów MEiL</text>
          <text x="136" y="105">prof. dr hab. inż. / MEiL PW</text>
        </g>

        <!-- Nazwa uczelni i instytutu (zgodnie z A3Z_formatka.pdf) -->
        <g text-anchor="middle" font-style="italic" fill="#000">
          <text x="153" y="142" font-size="10.5" font-weight="bold">POLITECHNIKA WARSZAWSKA</text>
          <text x="153" y="154" font-size="8.5">Instytut Techn. Lotn. i Mech. Stosowanej</text>
          <text x="153" y="168" font-size="9.5" font-weight="bold">WARSAW UNIVERSITY OF TECHNOLOGY</text>
          <text x="153" y="179" font-size="8.2">Institute of Aeronautics and Applied Mech.</text>
        </g>

        <!-- Prawa strona: Metoda E, Materiał, Masa, Tolerancja, Format, Skala -->
        <!-- Symbol rzutowania metody Europejskiej "E" (PN-EN ISO 5456-2) -->
        <g transform="translate(444, 0)">
          <text x="48" y="12" text-anchor="middle" font-size="7.5" font-style="italic" fill="#000">metoda E</text>
          <!-- Stożek ścięty -->
          <polygon points="12,32 34,25 34,45 12,38" fill="none" stroke="#000" stroke-width="1.2"/>
          <!-- Dwa okręgi współśrodkowe -->
          <circle cx="62" cy="35" r="4.5" fill="none" stroke="#000" stroke-width="1.2"/>
          <circle cx="62" cy="35" r="9.5" fill="none" stroke="#000" stroke-width="1.2"/>
          <!-- Osie punktowe symbolu metody E -->
          <line x1="6" y1="35" x2="78" y2="35" stroke="#000" stroke-width="0.7" stroke-dasharray="10,2,1.5,2"/>
          <line x1="62" y1="21" x2="62" y2="49" stroke="#000" stroke-width="0.7" stroke-dasharray="10,2,1.5,2"/>
        </g>

        <!-- Materiał / Masa / Tolerancja / Format -->
        <g font-size="7.0" font-style="italic" fill="#000">
          <text x="337" y="58" text-anchor="middle">Materiał/Material</text>
          <text x="406" y="58" text-anchor="middle">Masa/Mass</text>
          <text x="406" y="80" text-anchor="middle">Tol. ogólna/Tolerance</text>
          <text x="474" y="58" text-anchor="middle">Format/Size</text>
          <text x="522" y="58" text-anchor="middle">Podz./Scale</text>
        </g>
        <text x="337" y="78" text-anchor="middle" font-size="8.5" font-weight="bold" fill="#000">Dural PA7</text>
        <text x="406" y="71" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#000">${m0_str}</text>
        <text x="406" y="97" text-anchor="middle" font-size="8.2" fill="#000">ISO 2768-m</text>
        <text x="474" y="80" text-anchor="middle" font-size="11" font-weight="bold" fill="#000">A3</text>
        <text x="522" y="80" text-anchor="middle" font-size="12" font-weight="bold" fill="#000">${scaleLabel}</text>

        <!-- Nazwa części / Title -->
        <text x="312" y="117" font-size="7.2" font-style="italic" fill="#000">Nazwa części/Title</text>
        <text x="423" y="131" text-anchor="middle" font-size="10.5" font-weight="bold" fill="#000">${projTitle.slice(0, 36)}</text>
        <text x="423" y="142" text-anchor="middle" font-size="8.2" fill="#000">Samolot - Rysunek Zestawieniowy (3 Rzuty)</text>

        <!-- Numer rysunku i Arkusz -->
        <text x="312" y="157" font-size="7.2" font-style="italic" fill="#000">Numer rysunku/Drawing no.</text>
        <text x="405" y="174" text-anchor="middle" font-size="12.5" font-weight="bold" fill="#000">BIPOL-I-01.00</text>
        <text x="522" y="157" text-anchor="middle" font-size="6.8" font-style="italic" fill="#000">Arkusz/Sheet</text>
        <text x="522" y="174" text-anchor="middle" font-size="11.5" font-weight="bold" fill="#000">1/1</text>
      </g>
    </g>
  </svg>
  `;
  container.innerHTML = svgContent;
}

// Otwarcie samodzielnego okna z rysunkiem technicznym A3 gotowym do wydruku / zapisu PDF w pełnej skali
function openStandaloneCADWindow() {
  const svgEl = document.getElementById('cadSvgSheet');
  if (!svgEl) return;
  const win = window.open('', '_blank');
  win.document.write(`
    <!DOCTYPE html>
    <html lang="pl">
    <head>
      <meta charset="UTF-8">
      <title>Rysunek Techniczny A3Z - ZPK MEiL PW (PN-EN ISO 128 / 129 / 5456-2)</title>
      <style>
        @page { size: A3 landscape; margin: 0; }
        body { margin: 0; padding: 0; background: #e2e8f0; display: flex; flex-direction: column; align-items: center; font-family: sans-serif; }
        .toolbar { background: #0f172a; color: #fff; width: 100%; padding: 10px 24px; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; }
        .sheet-wrap { width: 96vw; max-width: 1480px; margin: 16px auto; background: #fff; box-shadow: 0 10px 25px rgba(0,0,0,0.25); }
        @media print {
          body { background: #fff; }
          .toolbar { display: none; }
          .sheet-wrap { width: 100vw; height: 100vh; margin: 0; box-shadow: none; }
        }
      </style>
    </head>
    <body>
      <div class="toolbar">
        <div><strong>Politechnika Warszawska MEiL</strong> &bull; Rysunek Zestawieniowy A3Z wg PN-EN ISO 128 / 129 / 5456-2 (metoda E)</div>
        <button onclick="window.print()" style="background:#10b981; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; cursor:pointer;">🖨️ Drukuj / Zapisz jako PDF (Format A3 Poziomo)</button>
      </div>
      <div class="sheet-wrap">${svgEl.outerHTML}</div>
    </body>
    </html>
  `);
  win.document.close();
}


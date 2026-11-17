// Shared kit for every Wasl screen: helpers, a hand-drawn pixel font, a hand-drawn sprite set, the desert scene.
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
// H('#id').html = x  only touches the DOM when x changed, so polling never restarts animations or eats typing
const H = s => { const el = $(s); return {set html(v) { if (el.__h !== v) { el.__h = v; el.innerHTML = v; } }}; };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const pad = n => String(n).padStart(2, '0');
const hm = t => { const d = new Date(t * 1000); return pad(d.getHours()) + ':' + pad(d.getMinutes()); };
function when(t, L = 'en') {
  const d = new Date(t * 1000), n = new Date();
  if (d.toDateString() === n.toDateString()) return hm(t);
  return d.toLocaleDateString(L === 'ar' ? 'ar' : 'en', {weekday: 'short'}) + ' ' + hm(t);
}
function dur(s, L = 'en') {
  const m = Math.max(1, Math.round(s / 60));
  if (m < 60) return L === 'ar' ? `${m} دقيقة` : `${m} min`;
  if (m < 36 * 60) {
    let h = Math.floor(m / 60), mm = Math.round((m % 60) / 5) * 5;
    if (mm === 60) { h++; mm = 0; }
    return L === 'ar' ? `${h} س${mm ? ` ${mm} د` : ''}` : `${h} h${mm ? ` ${mm} min` : ''}`;
  }
  const d = Math.round(m / 1440 * 2) / 2;
  return L === 'ar' ? `${d} يوم` : `${d} days`;
}
const kb = n => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(n < 10240 ? 1 : 0) + ' KB' : (n / 1048576).toFixed(1) + ' MB';

// ?bare strips the skin so only structure is left
const BARE = new URLSearchParams(location.search).has('bare');
if (BARE) $$('link[data-skin]').forEach(l => l.remove());

// ---------- palette (locked: every sprite and the scene use only these) ----------
const PAL = {k: '#1d1a16', w: '#fffaf0', c: '#e9d9b4', s: '#dba463', d: '#b5673a', t: '#8c3b24', r: '#cf3b2b', o: '#eaa22c', y: '#f3cf4f',
  g: '#3e8a56', G: '#25593a', b: '#3b8ea5', B: '#1f3050', l: '#9fd3df', m: '#8b8478', M: '#4b453d'};
const PRI_COLOR = [PAL.r, PAL.o, PAL.y, PAL.b, PAL.b, PAL.m];

// ---------- sprites: drawn by hand, one character per pixel, ink outline on everything ----------
const SPR = {
aid: `................ ..kkkkkkkkkkkk.. .kwwwwwwwwwwwwk. .kwwwwwrrwwwwwk. .kwwwwwrrwwwwwk. .kwwwwwrrwwwwwk. .kwwrrrrrrrrwwk. .kwwrrrrrrrrwwk. .kwwwwwrrwwwwwk. .kwwwwwrrwwwwwk. .kwwwwwrrwwwwwk. .kwwwwwwwwwwwwk. .kcccccccccccck. ..kkkkkkkkkkkk.. ................ ................`,
sick: `................ ......kkkk...... .....kwwwwk..... .....kwrwwk..... .....kwrwwk.kk.. .....kwrwwk..... .....kwrwwk.kk.. .....kwrwwk..... .....kwrwwk.kk.. .....kwrwwk..... ....kwrrrrwk.... ...kwrrrrrrwk... ...kwrrrrrrwk... ....kwrrrrwk.... .....kkkkkk..... ................`,
water: `................ .......kk....... ......kbbk...... ......kbbk...... .....kbbbbk..... .....kblbbk..... ....kblbbbbk.... ....kblbbbbk.... ...kblbbbbbbk... ...kblbbbbbbk... ...kbbbbbbbbk... ...kbbbbbbbBk... ....kbbbbbBk.... .....kkkkkk..... ................ ................`,
car: `................ ................ ................ ....kkkkkkk..... ...kollkollk.... ...kollkollk.... .kkkoooooooookk. kooooooooooooook kooooooooooooyok kookkkoooookkkok .kkMMMkkkkkMMMk. ..kMmMk...kMmMk. ..kMMMk...kMMMk. ...kkk.....kkk.. ................ ................`,
camel: `................ ................ .kk.....kk...... kddk...kddk..... kdkdk.kddddk.... .kddkkddddddk... ..kddddddddddkk. ..kddddddddddddk ..kdddddddddddkk ...kddddddddkdk. ...kdkdkkdkdk... ...kdkdk.kdkdk.. ...kdkdk.kdkdk.. ...kdkdk.kdkdk.. ...kkkkk.kkkkk.. ................`,
compass: `................ .....kkkkkk..... ...kkwwwwwwkk... ..kwwwwwwwrwwk.. .kwwwwwwwrrwwwk. .kwwwwwwrrwwwwk. kwwwwwwrrwwwwwwk kwwwwwwkkwwwwwwk kwwwwwwkkwwwwwwk kwwwwwbbwwwwwwwk .kwwwwbbwwwwwwk. .kwwwbbwwwwwwwk. ..kwwbwwwwwwwk.. ...kkwwwwwwkk... .....kkkkkk..... ................`,
mail: `................ ................ ................ kkkkkkkkkkkkkkkk kkwwwwwwwwwwwwkk kwkwwwwwwwwwwkwk kwwkwwwwwwwwkwwk kwwwkwwwwwwkwwwk kwwwwkwwwwkwwwwk kwwwwwkkkkwwwwwk kwwwwwwwwwwwwwwk kwwwwwwwwwwwwwwk kkkkkkkkkkkkkkkk ................ ................ ................`,
camera: `................ ................ ....kkkk........ ...kMMMMk....... kkkkkkkkkkkkkkkk kMMMMMMMMMMMMyMk kMMMMkkkkkMMMMMk kMMMkllllbkMMMMk kMMMklwllbkMMMMk kMMMkllllbkMMMMk kMMMkbbbbbkMMMMk kMMMMkkkkkMMMMMk kkkkkkkkkkkkkkkk ................ ................ ................`,
alert: `................ .......kk....... ......kyyk...... ......kyyk...... .....kyyyyk..... .....kykkyk..... ....kyykkyyk.... ....kyykkyyk.... ...kyyykkyyyk... ...kyyykkyyyk... ..kyyyyyyyyyyk.. ..kyyyykkyyyyk.. .kyyyyykkyyyyyk. .kyyyyyyyyyyyyk. .kkkkkkkkkkkkkk. ................`,
stop: `................ ....kkkkkkkk.... ...krrrrrrrrk... ..krrrrrrrrrrk.. .krrrrrrrrrrrrk. .krrrrrrrrrrrrk. .krwwwwwwwwwwrk. .krwwwwwwwwwwrk. .krwwwwwwwwwwrk. .krrrrrrrrrrrrk. .krrrrrrrrrrrrk. ..krrrrrrrrrrk.. ...krrrrrrrrk... ....kkkkkkkk.... ................ ................`,
sun: `................ .......oo....... ..o....oo....o.. ...o........o... .....kkkkkk..... ....kyyyyyyk.... ...kyyyyyyyyk... .ookyyyyyyyyko.. .ookyyyyyyyyko.. ...kyyyyyyyyk... ....kyyyyyyk.... .....kkkkkk..... ...o........o... ..o....oo....o.. .......oo....... ................`,
phone: `............ .kkkkkkkkkk. .kMMMMMMMMk. .kllllllllk. .kllllllllk. .kllwwllllk. .kllwwllllk. .kllllllllk. .kllllllllk. .kllllllllk. .kllllllllk. .kllllllllk. .kMMMMMMMMk. .kMMMkkMMMk. .kkkkkkkkkk. ............`,
truck: `................................ ................................ ....kkkkkkkkkkkkkkk............. ..kkwwwwwwwwwwwwwwwkk........... .kwwwwwwwwwwwwwwwwwwwk.kkkkkk... .kwwwwwwwwwwwwwwwwwwwk.kslllsk.. .kbbbbbbbbbbbbbbbbbbbk.kslllssk. .kbbbbbbbbbbbbbbbbbbbk.ksssssssk .kwwwwwwwwwwwwwwwwwwwk.kssssssyk ..kkcccccccccccccccckk.ksssssssk kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk ...kkkkk...kkkkk......kkkkk..... ..kMMmMMk.kMMmMMk....kMMmMMk.... ..kMmmmMk.kMmmmMk....kMmmmMk.... ..kMMmMMk.kMMmMMk....kMMmMMk.... ...kkkkk...kkkkk......kkkkk.....`,
tent: `................ .......kr....... .......krr...... .......k........ ......ksk....... .....kssdk...... ....ksssddk..... ...kssssdddk.... ..ksssskddddk... .kssssskkddddk.. kssssskkkkddddk. kkkkkkkkkkkkkkkk`,
clinic: `................ ..kkkkkkkkkkkk.. ..kwwwwwwwwwwk.. ..kwwwwrrwwwwk.. ..kwwrrrrrrwwk.. ..kwwrrrrrrwwk.. ..kwwwwrrwwwwk.. ..kwwwwwwwwwwk.. ..kwllwwwwllwk.. ..kwllwwwwllwk.. ..kwwwwwwwwwwk.. ..kwwwwkkwwwwk.. ..kwwwwkkwwwwk.. ..kwwwwkkwwwwk.. kkkkkkkkkkkkkkkk ................`,
mast: `...g... ..ggg.. ...g... ...k... ..kkk.. ...k... ...k... ..kkk.. ...k... ...k... ...k... ...k... ...k... ...k... ..kkk.. .kkkkk.`,
palm: `....GG..GG.. ..GGGGGGGGG. .GGgGGGGgGGG GG..GGGG..GG G...kGGk...G ....kddk.... .....dd..... .....dd..... ....kdd..... ....dd...... ....dd...... ....ddk..... .....dd..... .....dd..... ....kddk.... ...kkkkkk...`,
moon: `..www... .ww..... ww...... ww...... ww...... ww....w. .ww..ww. ..wwww..`,
speaker: `.....kk..... ....kwk..k.. kkkkwwk...k. kwwwwwk.k.k. kwwwwwk.k.k. kwwwwwk.k.k. kkkkwwk...k. ....kwk..k.. .....kk.....`,
tentmini: `...k... ..ksk.. .kssdk. kssdddk kkkkkkk`,
};
const IMG = {}, SPURL = {};
for (const [name, src] of Object.entries(SPR)) {
  const rows = src.trim().split(/\s+/), w = Math.max(...rows.map(r => r.length)), c = document.createElement('canvas');
  c.width = w; c.height = rows.length; const g = c.getContext('2d');
  rows.forEach((r, y) => [...r].forEach((ch, x) => { if (PAL[ch]) { g.fillStyle = PAL[ch]; g.fillRect(x, y, 1, 1); } }));
  IMG[name] = c; SPURL[name] = c.toDataURL();
}
/** A sprite as an <img>, scaled by a whole number of pixels. */
const sp = (name, s = 3, cls = '') => IMG[name] ? `<img class="sp ${cls}" src="${SPURL[name]}" width="${IMG[name].width * s}" height="${IMG[name].height * s}" alt="">` : '';

// ---------- pixel font: 5x7, drawn by hand, trimmed per glyph so it sets proportionally ----------
const FONT = {A: [14, 17, 17, 31, 17, 17, 17], B: [30, 17, 17, 30, 17, 17, 30], C: [14, 17, 16, 16, 16, 17, 14], D: [30, 17, 17, 17, 17, 17, 30],
  E: [31, 16, 16, 30, 16, 16, 31], F: [31, 16, 16, 30, 16, 16, 16], G: [14, 17, 16, 23, 17, 17, 14], H: [17, 17, 17, 31, 17, 17, 17],
  I: [14, 4, 4, 4, 4, 4, 14], J: [7, 2, 2, 2, 2, 18, 12], K: [17, 18, 20, 24, 20, 18, 17], L: [16, 16, 16, 16, 16, 16, 31],
  M: [17, 27, 21, 21, 17, 17, 17], N: [17, 25, 21, 19, 17, 17, 17], O: [14, 17, 17, 17, 17, 17, 14], P: [30, 17, 17, 30, 16, 16, 16],
  Q: [14, 17, 17, 17, 21, 18, 13], R: [30, 17, 17, 30, 20, 18, 17], S: [15, 16, 16, 14, 1, 1, 30], T: [31, 4, 4, 4, 4, 4, 4],
  U: [17, 17, 17, 17, 17, 17, 14], V: [17, 17, 17, 17, 17, 10, 4], W: [17, 17, 17, 21, 21, 27, 17], X: [17, 17, 10, 4, 10, 17, 17],
  Y: [17, 17, 10, 4, 4, 4, 4], Z: [31, 1, 2, 4, 8, 16, 31],
  0: [14, 17, 19, 21, 25, 17, 14], 1: [4, 12, 4, 4, 4, 4, 14], 2: [14, 17, 1, 2, 4, 8, 31], 3: [30, 1, 1, 14, 1, 1, 30], 4: [2, 6, 10, 18, 31, 2, 2],
  5: [31, 16, 30, 1, 1, 17, 14], 6: [14, 16, 16, 30, 17, 17, 14], 7: [31, 1, 2, 4, 8, 8, 8], 8: [14, 17, 17, 14, 17, 17, 14], 9: [14, 17, 17, 15, 1, 1, 14],
  '.': [0, 0, 0, 0, 0, 0, 4], ',': [0, 0, 0, 0, 0, 4, 8], ':': [0, 0, 4, 0, 0, 4, 0], '!': [4, 4, 4, 4, 4, 0, 4], '?': [14, 17, 1, 2, 4, 0, 4],
  '-': [0, 0, 0, 14, 0, 0, 0], '+': [0, 4, 4, 31, 4, 4, 0], '/': [1, 1, 2, 4, 8, 16, 16], '%': [25, 25, 2, 4, 8, 19, 19], "'": [4, 4, 0, 0, 0, 0, 0],
  '·': [0, 0, 0, 4, 0, 0, 0], '>': [0, 4, 2, 31, 2, 4, 0], '(': [2, 4, 4, 4, 4, 4, 2], ')': [8, 4, 4, 4, 4, 4, 8], '~': [0, 0, 8, 21, 2, 0, 0],
  '✓': [0, 1, 2, 2, 20, 20, 8], '×': [0, 17, 10, 4, 10, 17, 0], '#': [10, 10, 31, 10, 31, 10, 10], '=': [0, 0, 31, 0, 31, 0, 0]};
const GLYPH = {};
for (const [ch, rows] of Object.entries(FONT)) {       // trim empty columns, keep as 7 rows of booleans
  let lo = 4, hi = 0;
  rows.forEach(r => { for (let c = 0; c < 5; c++) if (r & (16 >> c)) { lo = Math.min(lo, c); hi = Math.max(hi, c); } });
  GLYPH[ch] = rows.map(r => { const o = []; for (let c = lo; c <= hi; c++) o.push(!!(r & (16 >> c))); return o; });
}
function wordRows(word) {
  const up = word.toUpperCase();
  if ([...up].every(ch => GLYPH[ch])) {
    const rows = [[], [], [], [], [], [], []];
    [...up].forEach((ch, i) => GLYPH[ch].forEach((r, y) => { if (i) rows[y].push(false); rows[y].push(...r); }));
    return {rows, own: true};
  }
  // anything the font cannot spell (Arabic, accents): rasterise the system font small and keep only solid pixels
  const c = document.createElement('canvas'), g = c.getContext('2d'), f = '700 12px system-ui,"Geeza Pro","Noto Sans Arabic",sans-serif';
  g.font = f; const w = Math.ceil(g.measureText(word).width) + 2; c.width = w; c.height = 16;
  g.font = f; g.fillStyle = '#000'; g.textBaseline = 'alphabetic';
  // right-to-left words must be laid out right-to-left, or their punctuation lands on the wrong side
  if (/[\u0600-\u06FF]/.test(word)) { g.direction = 'rtl'; g.textAlign = 'right'; g.fillText(word, w - 1, 12); } else g.fillText(word, 1, 12);
  const d = g.getImageData(0, 0, w, 16).data, rows = [];
  for (let y = 0; y < 16; y++) { rows.push([]); for (let x = 0; x < w; x++) rows[y].push(d[(y * w + x) * 4 + 3] > 96); }
  return {rows, own: false};
}
const WCACHE = {};
function wordSvg(word, s) {
  const key = word + '|' + s; if (WCACHE[key]) return WCACHE[key];
  const {rows, own} = wordRows(word), k = own ? s : Math.max(1, Math.round(s * .55)), W = rows[0].length, Hh = rows.length;
  let d = '';
  rows.forEach((r, y) => { for (let x = 0; x < W; x++) if (r[x]) { let n = 1; while (r[x + n]) n++; d += `M${x} ${y}h${n}v1h-${n}z`; x += n; } });
  return WCACHE[key] = `<svg width="${W * k}" height="${Hh * k}" viewBox="0 0 ${W} ${Hh}"><path d="${d}"/></svg>`;
}
/** Text set in the pixel font. s = pixel size. Words stay separate so lines wrap. */
function px(text, s = 2) {
  text = String(text ?? '');
  if (BARE || !text.trim()) return esc(text);
  const rtl = /[\u0600-\u06FF]/.test(text) ? ' dir="rtl"' : '';
  return `<span class="px"${rtl} role="text" aria-label="${esc(text)}" style="font-size:${s * 7}px;line-height:${s * 11}px">${text.trim().split(/\s+/).map(w => wordSvg(w, s)).join(' ')}</span>`;
}
/** Draw pixel text straight onto a canvas. Returns the width used. */
function ptext(g, text, x, y, color, s = 1) {
  let cx = x; g.fillStyle = color;
  for (const ch of String(text).toUpperCase()) {
    const gl = GLYPH[ch]; if (!gl) { cx += 3 * s; continue; }
    gl.forEach((r, yy) => r.forEach((on, xx) => { if (on) g.fillRect(cx + xx * s, y + yy * s, s, s); }));
    cx += (gl[0].length + 1) * s;
  }
  return cx - x;
}
const pbar = (pct, n = 10) => `<span class="pbar">${Array.from({length: n}, (_, i) => `<i class="${i < Math.round(pct / 100 * n) ? 'on' : ''}"></i>`).join('')}</span>`;
const brandHtml = (s = 3) => `<span class="brand">${px('WASL', s)}<span style="color:var(--clay)">${px('وصل', s + 1)}</span></span>`;
function upgrade(root = document) { $$('[data-px]', root).forEach(el => { el.innerHTML = px(el.textContent, +el.dataset.px || 2); el.removeAttribute('data-px'); });
  $$('[data-sp]', root).forEach(el => { const [n, s] = el.dataset.sp.split(','); el.innerHTML = sp(n, +s || 3); el.removeAttribute('data-sp'); });
  $$('[data-brand]', root).forEach(el => { el.innerHTML = brandHtml(+el.dataset.brand || 3); el.removeAttribute('data-brand'); }); }

// ---------- the desert scene: low-res canvas, scaled up without smoothing ----------
function blit(g, name, x, y, flip) {
  const im = IMG[name]; if (!im) return; x = Math.round(x); y = Math.round(y);
  if (flip) { g.save(); g.translate(x + im.width, y); g.scale(-1, 1); g.drawImage(im, 0, 0); g.restore(); } else g.drawImage(im, x, y);
}
function Scene(cv, mode) {
  const route = mode === 'route', W = route ? 240 : 128, HH = route ? 62 : 60, F = HH - 8;      // F = floor line
  cv.width = W; cv.height = HH;
  const g = cv.getContext('2d'), st = {on: false, weak: false, pos: 'road', x: route ? 104 : W + 8, dir: 1, f: 0};
  const NIGHT = {sky: ['#131d33', '#1a2947', '#1f3050', '#2b4168'], far: '#2b4168', near: '#1f3050', gnd: '#131d33', road: '#2b4168'};
  const DAY = {sky: ['#6fb6cf', '#9fd3df', '#f1dfa4', '#f3cf4f'], far: '#dba463', near: '#b5673a', gnd: '#8c3b24', road: '#b5673a'};
  const stars = [[9, 5], [23, 13], [38, 4], [52, 17], [67, 7], [81, 14], [96, 5], [110, 11], [120, 20], [15, 24], [75, 25], [44, 28], [101, 27]];
  const far = x => F - 11 + Math.round(4 * Math.sin(x / 17) + 3 * Math.sin(x / 7 + 1));
  const near = x => F - 4 + Math.round(2 * Math.sin(x / 23 + 2) + 2 * Math.sin(x / 9));
  function draw() {
    const P = route || st.on ? DAY : NIGHT, bh = Math.ceil((F - 8) / 4);
    P.sky.forEach((c, i) => { g.fillStyle = c; g.fillRect(0, i * bh, W, HH);
      if (i) for (let x = i % 2; x < W; x += 2) g.fillRect(x, i * bh - 1, 1, 1); });            // one dithered row at each seam
    if (P === NIGHT) { g.fillStyle = PAL.w; stars.forEach(([x, y], i) => { if ((st.f + i * 5) % 16 > 2) g.fillRect(x, y, 1, 1); }); blit(g, 'moon', W - 22, 6); }
    else blit(g, 'sun', route ? W / 2 - 8 : W - 32, route ? F - 34 : 8);
    for (let x = 0; x < W; x++) { g.fillStyle = P.far; g.fillRect(x, far(x), 1, HH); g.fillStyle = P.near; g.fillRect(x, near(x), 1, HH); }
    g.fillStyle = P.gnd; g.fillRect(0, F + 1, W, HH);
    g.fillStyle = P.road; for (let x = (st.f % 2) * 0; x < W; x += 8) g.fillRect(x, F + 4, 4, 1);
    if (route) { blit(g, 'tent', 8, F + 1 - 12); blit(g, 'palm', 26, F + 1 - 16); blit(g, 'clinic', W - 42, F + 1 - 15); blit(g, 'mast', W - 20, F + 1 - 16);
      if (st.f % 8 < 4) { g.fillStyle = PAL.r; g.fillRect(W - 17, F - 16, 1, 1); } }
    else { blit(g, 'palm', 6, F + 1 - 16); blit(g, 'tent', 20, F + 1 - 12); }
    const target = route ? ({camp: 38, road: 104, town: 160, free: 104}[st.pos] ?? 104) : st.on ? 62 : W + 8;
    const moving = st.x !== target;
    if (moving) { const dd = target - st.x; st.dir = Math.sign(dd); st.x += st.dir * Math.min(4, Math.abs(dd)); }
    const ty = F + 1 - 16 - (moving && st.f % 2 ? 1 : 0);
    blit(g, 'truck', st.x, ty, st.dir < 0);
    const linked = route ? st.pos !== 'road' : st.on;
    if (linked && !moving) {                                                                   // radio rings, one pixel thick, stepping outward
      g.fillStyle = st.weak ? PAL.o : PAL.g; const cx = st.x + 16, cy = ty + 2, r = 5 + 4 * ((st.f >> 1) % 3);
      for (let a = 195, i = 0; a <= 345; a += 9, i++) { if (st.weak && i % 2) continue; g.fillRect(Math.round(cx + r * Math.cos(a * Math.PI / 180)), Math.round(cy + r * Math.sin(a * Math.PI / 180)), 1, 1); }
    }
  }
  setInterval(() => { st.f++; draw(); }, 110); draw();
  return {set: o => Object.assign(st, o)};
}

// ---------- shared vocabulary ----------
const CATS = {
  injury:  {i: 'aid',     en: 'Someone is hurt', ar: 'شخص مصاب'},
  sick:    {i: 'sick',    en: 'Someone is sick', ar: 'شخص مريض'},
  water:   {i: 'water',   en: 'No water',        ar: 'لا يوجد ماء'},
  vehicle: {i: 'car',     en: 'Vehicle broken',  ar: 'السيارة معطلة'},
  animal:  {i: 'camel',   en: 'Sick animal',     ar: 'حيوان مريض'},
  lost:    {i: 'compass', en: 'Person missing',  ar: 'شخص مفقود'},
};
const SEV = [
  {pri: 0, en: 'Life in danger', ar: 'خطر على الحياة', c: PAL.r},
  {pri: 1, en: 'Urgent',         ar: 'عاجل',           c: PAL.o},
  {pri: 2, en: 'Can wait',       ar: 'يمكن الانتظار',   c: PAL.y},
];
const REPLIES = {
  stay:    {i: 'stop',   en: 'Stay where you are. Help is coming.',               ar: 'ابقَ في مكانك. المساعدة قادمة.'},
  vehicle: {i: 'car',    en: 'A vehicle is on its way to you.',                   ar: 'سيارة في الطريق إليك.'},
  shade:   {i: 'sun',    en: 'Keep them in the shade. Give small sips of water.', ar: 'أبقِه في الظل وأعطه رشفات صغيرة من الماء.'},
  water:   {i: 'water',  en: 'Water is coming on the next truck.',                ar: 'الماء قادم مع الشاحنة القادمة.'},
  photo:   {i: 'camera', en: 'Send a photo if you can.',                          ar: 'أرسل صورة إن استطعت.'},
};
const ALERTS = {
  storm: {i: 'alert', en: 'Sandstorm expected tonight. Stay in camp.',      ar: 'عاصفة رملية متوقعة الليلة. ابقوا في المخيم.'},
  heat:  {i: 'sun',   en: 'Extreme heat tomorrow. Rest between 11 and 4.', ar: 'حرارة شديدة غداً. استريحوا بين ١١ و٤.'},
};
function iconOf(b) {
  const x = b.body || {};
  if (b.kind === 'sos') return (CATS[x.cat] || {}).i || 'alert';
  if (b.kind === 'photo') return 'camera';
  if (b.kind === 'alert') return (ALERTS[x.code] || {}).i || 'alert';
  return (REPLIES[x.code] || {}).i || 'mail';
}
const ico = (b, s = 3) => sp(iconOf(b), s);
function titleOf(b, L = 'en') {
  const x = b.body || {};
  if (b.kind === 'sos') return (CATS[x.cat] || {})[L] || 'SOS';
  if (b.kind === 'photo') return L === 'ar' ? 'صورة' : 'Photo';
  if (b.kind === 'alert') return (ALERTS[x.code] || {})[L] || x.text || '';
  return (REPLIES[x.code] || {})[L] || x.text || '';
}
const sevOf = b => SEV.find(s => s.pri === b.pri);
upgrade();

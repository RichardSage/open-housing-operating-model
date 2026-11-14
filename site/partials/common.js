// Shared by the tool pages: data lookups, escaping, tooltips and specialist provision.
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P = Object.fromEntries(D.patterns.map(p => [p.id, p]));
const U = Object.fromEntries(D.users.map(u => [u.id, u.n]));
const G = Object.fromEntries(D.groups.map(g => [g.id, g.n]));
const SV = Object.fromEntries(D.services.map(s => [s.c, s]));
const RQ = Object.fromEntries(D.services.flatMap(s => s.r.map(r => [r.c, { ...r, s }])));
const SPECS = D.specs || [];
const isCol = s => s.u.length === 1 && s.u[0] === 'colleagues';
const audOk = (s, aud) => aud === 'all' || (aud === 'colleagues' ? isCol(s) : !isCol(s));
const dc = d => d ? 'enab' : 'homes';
const nAct = a => a.s.reduce((m, f) => m + f.a.length, 0);
const pct = (n, d) => d ? Math.round(100 * n / d) : 0;
const suggest = where => D.repo ? `${D.repo}/issues/new?template=suggest-a-change.yml&where=${encodeURIComponent(where)}` : '';
const spNames = sp => (sp || []).map(i => SPECS[i].n).join(', ');
const spBadge = sp => (sp && sp.length) ? `<span class="spb" data-tip="${esc(`<b>Specialist: ${esc(spNames(sp))}</b><small>Only some providers offer this</small>`)}">Specialist</span>` : '';
// Every function and activity, flat, with its area
const FN = [], ACT = {};
D.areas.forEach((a, ai) => a.s.forEach(f => { FN.push({ ...f, a: f.a, area: a, ai }); f.a.forEach((n, k) => { ACT[`${f.c}.${k + 1}`] = { c: `${f.c}.${k + 1}`, n, f, area: a, ai }; }); }));
const FNI = Object.fromEntries(FN.map(f => [f.c, f]));
const layer = id => (D.layers || []).find(l => l.id === id);
const fieldOf = (ly, id) => ly ? ly.fields.findIndex(f => f.id === id) : -1;

// Tooltips: any element with data-tip
document.body.insertAdjacentHTML('beforeend', '<div class="tip" id="tip" hidden></div>');
const tipEl = $('#tip');
document.addEventListener('pointermove', e => {
  const t = e.target.closest && e.target.closest('[data-tip]');
  if (!t) { tipEl.hidden = true; return; }
  tipEl.innerHTML = t.dataset.tip; tipEl.hidden = false;
  const r = tipEl.getBoundingClientRect(); let x = e.clientX + 14, y = e.clientY + 14;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
  tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
});
document.addEventListener('scroll', () => { tipEl.hidden = true; }, { passive: true });

// Segmented controls: <div class="seg" data-seg="name"><button data-v="x" aria-pressed>
function seg(name, onChange) {
  const el = document.querySelector(`[data-seg="${name}"]`);
  el.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    el.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    onChange(b.dataset.v);
  });
  return () => el.querySelector('[aria-pressed="true"]').dataset.v;
}

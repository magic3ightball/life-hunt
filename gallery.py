"""Build gallery.html from results/*.json: rare and unseen objects, animated.

  python3 gallery.py [--rare 100]
"""
import argparse
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Life Hunt</title>
<style>
:root { --bg:#f6f4ef; --card:#fff; --ink:#1d1c1a; --mute:#77736b; --cell:#1d1c1a; --new:#d2452a; --line:#e3dfd6; }
@media (prefers-color-scheme: dark) { :root { --bg:#151514; --card:#1f1f1d; --ink:#ecebe6; --mute:#9a968d; --cell:#f2d27a; --new:#ff7a5c; --line:#2e2d2a; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system, "Apple SD Gothic Neo", sans-serif; }
main { max-width:1100px; margin:0 auto; padding:28px 16px 60px; }
h1 { font-size:26px; margin:0 0 4px; }
.sub { color:var(--mute); margin:0 0 22px; }
.stats { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:26px; }
.stat { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; }
.stat b { display:block; font-size:20px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:14px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }
.card.new { border-color:var(--new); }
canvas { width:100%; aspect-ratio:1; display:block; border-radius:8px; background:var(--bg); }
.tag { display:inline-block; font-size:12px; font-weight:600; padding:1px 8px; border-radius:99px; background:var(--line); margin-top:8px; }
.new .tag { background:var(--new); color:#fff; }
.code { font:12px ui-monospace, monospace; word-break:break-all; color:var(--mute); margin:6px 0; }
a { color:inherit; }
h2 { font-size:18px; margin:34px 0 12px; }
.tabs { display:flex; gap:6px; margin:0 0 20px; }
.tabs button { font:inherit; border:1px solid var(--line); background:var(--card); color:var(--ink); padding:7px 14px; border-radius:99px; cursor:pointer; }
.tabs button.on { background:var(--ink); color:var(--bg); }
.hidden { display:none; }
.flow { width:100%; height:auto; }
.flow rect { fill:var(--card); stroke:var(--line); }
.flow text { fill:var(--ink); font-size:13px; }
.flow .m { fill:var(--mute); font-size:11px; }
.flow path { stroke:var(--mute); fill:none; marker-end:url(#arr); }
.ex { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px,1fr)); gap:14px; }
.ex .card p { margin:6px 0 0; color:var(--mute); font-size:14px; }
.mono { font:13px/1.15 ui-monospace, monospace; white-space:pre; margin:8px 0 0; }
.mono b { color:var(--new); }
</style></head><body><main>
<h1>Life Hunt</h1>
<p class="sub" id="sub"></p>
<div class="tabs"><button class="on" data-t="finds">발견한 물체</button><button data-t="how">어떻게 찾았나</button></div>
<section id="finds">
<div class="stats" id="stats"></div>
<div class="grid" id="grid"></div>
</section>
<section id="how" class="hidden">
<h2 style="margin-top:0">한 번의 검색이 지나가는 길</h2>
<svg class="flow" viewBox="0 0 1060 250" role="img" aria-label="검색 파이프라인">
<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" style="fill:var(--mute);stroke:none"/></marker></defs>
<g><rect x="10" y="20" width="190" height="80" rx="10"/><text x="24" y="50">① 수프 만들기</text><text class="m" x="24" y="72">씨앗 문자열 → SHA-256</text><text class="m" x="24" y="88">→ 16×16 무작위 칸</text></g>
<g><rect x="270" y="20" width="190" height="80" rx="10"/><text x="284" y="50">② 돌리기 (C 엔진)</text><text class="m" x="284" y="72">HighLife: 3·6이웃 탄생</text><text class="m" x="284" y="88">2·3이웃 생존</text></g>
<g><rect x="530" y="20" width="190" height="80" rx="10"/><text x="544" y="50">③ 멈춤 감지</text><text class="m" x="544" y="72">전체 모양의 해시가</text><text class="m" x="544" y="88">p세대마다 반복되면 끝</text></g>
<g><rect x="790" y="20" width="250" height="80" rx="10"/><text x="804" y="50">④ 날아가는 것 떼어내기</text><text class="m" x="804" y="72">반경 80 밖에서 혼자 돌려 보고</text><text class="m" x="804" y="88">평행이동하면 우주선으로 기록</text></g>
<g><rect x="10" y="150" width="250" height="80" rx="10"/><text x="24" y="180">⑤ 물체 나누기</text><text class="m" x="24" y="202">2칸 이내 칸끼리 묶고, 서로 상관없이</text><text class="m" x="24" y="218">안정한 조각이면 다시 쪼갬</text></g>
<g><rect x="330" y="150" width="200" height="80" rx="10"/><text x="344" y="180">⑥ 이름 붙이기</text><text class="m" x="344" y="202">8방향·모든 위상 중 가장</text><text class="m" x="344" y="218">짧은 apgcode가 정식 이름</text></g>
<g><rect x="600" y="150" width="200" height="80" rx="10"/><text x="614" y="180">⑦ 기록과 대조</text><text class="m" x="614" y="202">Catagolue 집계</text><text class="m" x="614" y="218">(수프 18.9억 개)</text></g>
<g><rect x="870" y="150" width="170" height="80" rx="10"/><text x="884" y="180">⑧ 다시 확인</text><text class="m" x="884" y="202">원본 수프를 독립</text><text class="m" x="884" y="218">시뮬레이터로 재현</text></g>
<path d="M200,60 L266,60"/><path d="M460,60 L526,60"/><path d="M720,60 L786,60"/>
<path d="M915,100 L915,125 L135,125 L135,146"/><path d="M260,190 L326,190"/><path d="M530,190 L596,190"/><path d="M800,190 L866,190"/>
</svg>
<div class="ex" style="margin-top:18px">
<div class="card"><b>왜 표준 Life가 아니라 HighLife?</b>
<p>표준 Life는 이미 수프 3.4×10¹⁴개가 검색돼서 노트북으로는 새것이 나올 확률이 사실상 0이에요. HighLife(B36/S23)는 1.9×10⁹개만 검색됐고, 집계에서 1번만 나온 물체 비율로 계산하면 300만 수프마다 새 물체 1개 정도가 기대돼요. 실제로도 1개가 나왔어요.</p></div>
<div class="card"><b>가장 큰 함정: 붙어 있는 두 물체</b>
<div class="mono">.oo....
o..o...
.oo..<b>oo</b>
......<b>o</b>
....<b>o</b>..
....<b>oo</b>.</div>
<p>처음엔 이게 "처음 보는 정물"로 떴어요. 사실은 벌집(왼쪽)과 항공모함(빨강)이 나란히 있는 것뿐이에요. 항공모함은 두 조각이 서로 닿지 않아서 처음 분리기가 깨뜨렸고, 그 바람에 후보 9개 중 8개가 가짜였어요. 지금은 "각자 따로 안정한 조각으로 가장 잘게 나누기"를 전부 시도해서 걸러요.</p></div>
<div class="card"><b>엔진이 맞는지 어떻게 알아?</b>
<p>흔한 물체 12종 모두 "우리 개수 ÷ Catagolue 개수"가 1.55×10⁻³으로, 수프 수 비율과 똑같았어요. 수프도 apgsearch와 같은 방식으로 만들어서, 카드의 "원본 수프" 링크로 누구나 같은 수프를 다시 볼 수 있어요.</p></div>
</div>
</section>
</main>
<script>
const DATA = __DATA__;
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => {
  document.querySelectorAll('.tabs button').forEach(x => x.classList.toggle('on', x === b));
  for (const id of ['finds', 'how']) document.getElementById(id).classList.toggle('hidden', id !== b.dataset.t);
  draw();
});
const kind = c => c.startsWith('xs') ? '정물' : c.startsWith('xp') ? '진동자 p' + c.slice(2).split('_')[0]
  : c.startsWith('xq') ? '우주선 p' + c.slice(2).split('_')[0] : '기타';
function parseRule(r) { const m = r.match(/b(\\d*)s(\\d*)/); return [new Set([...m[1]].map(Number)), new Set([...m[2]].map(Number))]; }
function step(cells, [B, S]) {
  const cnt = new Map(), live = new Set(cells.map(([x, y]) => x + ',' + y));
  for (const [x, y] of cells) for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++)
    if (dx || dy) { const k = (x + dx) + ',' + (y + dy); cnt.set(k, (cnt.get(k) || 0) + 1); }
  const out = [];
  for (const [k, n] of cnt) if (live.has(k) ? S.has(n) : B.has(n)) out.push(k.split(',').map(Number));
  return out;
}
document.getElementById('sub').textContent =
  `규칙 ${DATA.rules.join(', ')} · 흔하지 않거나(Catagolue 집계 < ${DATA.rare}) 처음 보는 물체`;
document.getElementById('stats').innerHTML = [
  ['검색한 수프', DATA.soups.toLocaleString()], ['찾은 물체 종류', DATA.distinct.toLocaleString()],
  ['Catagolue에 없음', DATA.items.filter(i => i.census === 0).length], ['희귀', DATA.items.filter(i => i.census > 0).length],
].map(([k, v]) => `<div class="stat">${k}<b>${v}</b></div>`).join('');
const grid = document.getElementById('grid');
const anims = [];
for (const it of DATA.items) {
  const card = document.createElement('div');
  card.className = 'card' + (it.census === 0 ? ' new' : '');
  const link = `https://catagolue.hatsya.com/hashsoup/C1/${it.soup}/${it.rule}`;
  const obj = `https://catagolue.hatsya.com/object/${it.code}/${it.rule}`;
  card.innerHTML = `<canvas></canvas>
    <span class="tag">${it.census === 0 ? '처음 보는 물체' : 'Catagolue ' + it.census + '회'}</span>
    <div><b>${kind(it.code)}</b> · ${it.cells.length}칸 · 이번에 ${it.count}회</div>
    <div class="code">${it.code}</div>
    <div><a href="${link}" target="_blank">원본 수프</a> · <a href="${obj}" target="_blank">Catagolue</a></div>`;
  grid.appendChild(card);
  const rule = parseRule(it.rule);
  const xs = it.cells.map(c => c[0]), ys = it.cells.map(c => c[1]);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  anims.push({ canvas: card.querySelector('canvas'), cells: it.cells, start: it.cells, rule, cx, cy, ship: it.code.startsWith('xq'),
    span: Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) + 6, t: 0 });
}
function draw() {
  const ink = getComputedStyle(document.body).getPropertyValue('--cell');
  for (const a of anims) {
    const c = a.canvas, d = devicePixelRatio || 1, W = c.clientWidth * d;
    if (c.width !== W) { c.width = W; c.height = W; }
    const g = c.getContext('2d'); g.clearRect(0, 0, W, W);
    const s = W / Math.max(a.span, 10); g.fillStyle = ink;
    let ox = a.cx, oy = a.cy;
    if (a.ship && a.cells.length) { const xs = a.cells.map(q => q[0]), ys = a.cells.map(q => q[1]);
      ox = (Math.min(...xs) + Math.max(...xs)) / 2; oy = (Math.min(...ys) + Math.max(...ys)) / 2; }
    for (const [x, y] of a.cells) g.fillRect(W / 2 + (x - ox - 0.5) * s + 1, W / 2 + (y - oy - 0.5) * s + 1, s - 2, s - 2);
  }
}
setInterval(() => { for (const a of anims) { a.cells = step(a.cells, a.rule); if (!a.cells.length) a.cells = a.start; } draw(); }, 350);
addEventListener('resize', draw); draw();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rare", type=int, default=100)
    a = ap.parse_args()
    items, rules, soups, distinct = [], set(), 0, set()
    for path in sorted(glob.glob(os.path.join(HERE, "results", "*.json"))):
        r = json.load(open(path))
        if r["prefix"].startswith(("test", "hl_test")):
            continue
        rules.add(r["rule"])
        soups += r["soups"]
        for o in r["objects"]:
            distinct.add((r["rule"], o["code"]))
            if o["census"] is not None and o["census"] < a.rare:
                items.append({**o, "rule": r["rule"]})
    items.sort(key=lambda i: (i["census"], -len(i["cells"])))
    data = {"rules": sorted(rules), "soups": soups, "distinct": len(distinct), "rare": a.rare, "items": items}
    html = PAGE.replace("__DATA__", json.dumps(data))
    for out in (os.path.join(HERE, "gallery.html"), os.path.join(HERE, "site", "index.html")):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w").write(html)
        print("wrote", out, len(items), "items")


if __name__ == "__main__":
    main()

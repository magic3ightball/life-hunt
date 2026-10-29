# Life Hunt — handoff

Goal: discover Game-of-Life-family objects that have never been recorded on
Catagolue (the community census of random-soup results).

## How it works
- `soup.c` — C engine. Reads `<index> <sha256 hex>` lines on stdin; the soup is
  apgsearch's C1 16×16 hashsoup layout, so any find can be regenerated at
  `https://catagolue.hatsya.com/hashsoup/C1/<seed>/<rule>`. Runs until periodic
  (period ≤ 240), ejects verified spaceships beyond radius 80, gives up after
  15000 gens or when the mess exceeds 300 cells across (`U` lines).
- `hunt.py` — runs soups in parallel, separates ash into objects (pseudo-object
  splitting by pairwise independence test), computes apgcodes, and compares them
  against Catagolue textcensus per prefix (cached in `census_cache/`).
- `gallery.py` → `gallery.html` — animated cards of rare / unseen objects.

## Commands
```
cc -O3 -march=native -o soup soup.c
python3 hunt.py --rule b36s23 --soups 3000000 --prefix lifehunt_hl_1020_ --chunk 2000 --rare 3
python3 gallery.py --rare 100
```

## Verified
- b3s23, 5000 soups: all 41 distinct apgcodes exist in Catagolue (canonicaliser correct).
- Catagolue hashsoup `k_test123` (b36s23) evolved in C equals an independent Python sim.

## Rule choice (Catagolue C1 soups, 2026-10-20)
- b3s23 ≈ 3.4e14 soups — hopeless on a laptop.
- b36s23 HighLife ≈ 1.9e9 soups, stable, ~1100 soups/s here. Good-Turing on the
  census: unseen-object mass ≈ 5e-8 → about one new object per ~3M soups.
- b37s23 DryLife has only 1e7 soups but is explosive (LifeWiki) — ~1/3 soups grow.
- Uncensused rules tested (b35s236, b3s234, b356s23, b3s235) are explosive.

## Run 1 result (2026-10-20/21, b36s23, 3M soups, prefix lifehunt_hl_1020_, 43 min)
- Object frequencies match Catagolue to 1.55e-3 = soups ratio for all common objects.
- First run deadlocked (stdin/stdout pipes) at 682k; fixed by passing seeds via a temp file
  and adding checkpoints (`results/<rule>_<prefix>.ckpt`, rerun same command to resume).
- 9 "NEW?" flags were mostly pseudo-objects (aircraft carrier xs6_39c is two non-touching
  pieces and broke the old splitter). split_pseudo now does an exact finest-partition search.
- Real find: **xs15_0ggm96z12ko**, strict still life, absent from HighLife C1 census
  (1.9e9 soups); Catagolue has it once, only in an unofficial-symmetry census.
  Soup: https://catagolue.hatsya.com/hashsoup/C1/lifehunt_hl_1020_1672215/b36s23
  (re-verified with an independent Python sim from Catagolue's own RLE).
- Rare (census 2): xs14_4aq453z32, xp2_4apb8ozw3.

## Deploy
- `python3 gallery.py --rare 100` writes gallery.html and site/index.html (with "어떻게 찾았나" tab).
- From site/: `npx vercel@latest deploy --prod --yes --scope magic3ightballs-projects --project life-hunt`
  → https://life-hunt.vercel.app (listed in the deployed-links hub).

## Next
- Optional: run apgsearch itself to submit this haul officially to Catagolue (needs approval:
  downloads/compiles code and publishes results).
- Look at the ~0.4% `U` (never-stabilized) soups for puffers/guns.

## Known gaps
- ~0.2% objects come out `zz_dies` / `zz_noperiod` (ejection edge cases).
- `U` soups (HighLife ~0.4%, mostly replicator growth) are listed but not analysed.
- Nothing is uploaded to Catagolue; that would need apgsearch itself.

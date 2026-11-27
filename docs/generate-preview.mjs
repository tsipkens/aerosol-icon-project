#!/usr/bin/env node
/**
 * Generates a static icon-grid preview for the README.
 *
 *   node scripts/generate-preview.mjs [svgDir] [outDir]
 *
 * Defaults: svgDir = "svg", outDir = "docs"
 * Writes:   docs/icons-light.svg  and  docs/icons-dark.svg
 *
 * No dependencies; needs Node 18+. The layout mirrors the website: a rounded
 * outlined tile per icon with its name underneath, sorted by name.
 */

import { readdirSync, readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { join, relative, basename, sep } from 'node:path';

/* ---------- settings ---------- */
const SVG_DIR = process.argv[2] || 'svg';
const OUT_DIR = process.argv[3] || 'docs';

const COLS = 8;          // icons per row
const TILE = 96;         // tile size in px (square)
const GAP_X = 16;        // horizontal gap between tiles
const GAP_Y = 22;        // extra vertical gap between rows (below the label)
const ICON = 64;         // icon size inside the tile
const RADIUS = 4;       // tile corner radius
const LABEL_SIZE = 10.5; // label font size
const LABEL_GAP = 6;     // tile -> label baseline offset
const LABEL_MAX = 18;    // labels longer than this are truncated with "…"
const FONT = `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif`;

const THEMES = {
  light: { ink: '#15171c', muted: '#6b7080', line: '#dcdee5' },
  dark:  { ink: '#eceef3', muted: '#8d92a3', line: '#30363d' },
};

/* ---------- find icons ---------- */
function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) walk(p, out);
    else if (/\.svg$/i.test(entry.name)) out.push(p);
  }
  return out;
}

try { statSync(SVG_DIR); } catch {
  console.error(`[docs] folder not found: ${SVG_DIR}`);
  process.exit(1);
}

/* ---------- svg normalising (same rules as the website) ---------- */
const attrRe = /([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
const DROP_ROOT = new Set(['width', 'height', 'class', 'style', 'x', 'y', 'id', 'version', 'xmlns']);
const COLOR_ATTRS = ['fill', 'stroke'];
const isNeutral = v => /^(none|currentcolor|url\()/i.test(v.trim());
const escXml = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function normalize(text, uid) {
  const m = text.match(/<svg\b([^>]*)>([\s\S]*)<\/svg\s*>/i);
  if (!m) return null;
  let [, rootAttrs, inner] = m;
  rootAttrs = rootAttrs.replace(/\/\s*$/, '');

  const attrs = {};
  for (const a of rootAttrs.matchAll(attrRe)) attrs[a[1]] = a[2] ?? a[3];

  // viewBox: use the given one, or build it from width/height
  let viewBox = attrs.viewBox;
  if (!viewBox) {
    const w = parseFloat(attrs.width), h = parseFloat(attrs.height);
    if (!(w > 0 && h > 0)) return null;
    viewBox = `0 0 ${w} ${h}`;
  }

  // drop things that don't belong in a docs
  inner = inner
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<(script|metadata|title|desc|style|foreignObject)\b[\s\S]*?<\/\1\s*>/gi, '')
    .replace(/<(script|metadata|title|desc|style)\b[^>]*\/>/gi, '')
    .replace(/\son\w+\s*=\s*(?:"[^"]*"|'[^']*')/gi, '');

  // single-colour icons inherit currentColor so they follow the theme
  const colors = new Set();
  const scan = s => { for (const a of s.matchAll(/\b(fill|stroke)\s*=\s*(?:"([^"]*)"|'([^']*)')/g)) { const v = (a[2] ?? a[3]).trim(); if (!isNeutral(v)) colors.add(v.toLowerCase()); } };
  scan(rootAttrs); scan(inner);
  const recolor = s => s.replace(/\b(fill|stroke)(\s*=\s*)(?:"([^"]*)"|'([^']*)')/g, (all, k, eq, d, sq) => {
    const v = (d ?? sq).trim();
    return isNeutral(v) ? all : `${k}${eq}"currentColor"`;
  });
  const single = colors.size <= 1;

  // keep the remaining root attributes (fill, stroke-width, …) on the nested <svg>
  const kept = Object.entries(attrs)
    .filter(([k]) => !DROP_ROOT.has(k) && !k.startsWith('xmlns') && k !== 'viewBox')
    .map(([k, v]) => `${k}="${escXml(v)}"`)
    .join(' ');
  let keptAttrs = single ? recolor(kept) : kept;
  let body = single ? recolor(inner) : inner;

  // make ids unique across the whole sheet (gradients, clipPaths, …)
  const ids = [...body.matchAll(/\bid\s*=\s*"([^"]+)"/g)].map(x => x[1]);
  for (const id of new Set(ids)) {
    const re = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    body = body
      .replace(new RegExp(`\\bid\\s*=\\s*"${re}"`, 'g'), `id="${uid}-${id}"`)
      .replace(new RegExp(`url\\(\\s*['"]?#${re}['"]?\\s*\\)`, 'g'), `url(#${uid}-${id})`)
      .replace(new RegExp(`((?:xlink:)?href\\s*=\\s*")#${re}"`, 'g'), `$1#${uid}-${id}"`);
  }
  return { viewBox, attrs: keptAttrs, body };
}

/* ---------- load ---------- */
const files = walk(SVG_DIR);
const icons = [];
let skipped = 0;
files.forEach((file, i) => {
  const name = basename(file).replace(/\.svg$/i, '');
  const svg = normalize(readFileSync(file, 'utf8'), `i${i}`);
  if (svg) icons.push({ name, svg, file: relative(SVG_DIR, file).split(sep).join('/') });
  else { skipped++; console.warn(`[docs] skipped (not a valid svg): ${file}`); }
});
icons.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

if (!icons.length) {
  console.error(`[docs] no SVGs found in ${SVG_DIR}`);
  process.exit(1);
}

/* ---------- layout + render ---------- */
const rows = Math.ceil(icons.length / COLS);
const LABEL_H = Math.ceil(LABEL_SIZE * 1.4);
const ROW_H = TILE + LABEL_GAP + LABEL_H + GAP_Y;
const W = COLS * TILE + (COLS - 1) * GAP_X;
const H = rows * ROW_H - GAP_Y;
const PAD = 2; // room for the 1.5px tile stroke

const truncate = s => (s.length > LABEL_MAX ? s.slice(0, LABEL_MAX - 1) + '…' : s);

function render(theme) {
  const t = THEMES[theme];
  const cells = icons.map((ic, i) => {
    const col = i % COLS, row = Math.floor(i / COLS);
    const x = col * (TILE + GAP_X), y = row * ROW_H;
    const ix = x + (TILE - ICON) / 2, iy = y + (TILE - ICON) / 2;
    return [
      `<rect x="${x + 0.75}" y="${y + 0.75}" width="${TILE - 1.5}" height="${TILE - 1.5}" rx="${RADIUS}" fill="none" stroke="${t.line}" stroke-width="1.5"/>`,
      `<svg x="${ix}" y="${iy}" width="${ICON}" height="${ICON}" viewBox="${ic.svg.viewBox}"${ic.svg.attrs ? ' ' + ic.svg.attrs : ''}>${ic.svg.body}</svg>`,
      `<text x="${x + TILE / 2}" y="${y + TILE + LABEL_GAP + LABEL_SIZE}" text-anchor="middle" font-size="${LABEL_SIZE}" fill="${t.muted}">${escXml(truncate(ic.name))}</text>`,
    ].join('\n');
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W + PAD * 2}" height="${H + PAD * 2}" viewBox="${-PAD} ${-PAD} ${W + PAD * 2} ${H + PAD * 2}" color="${t.ink}" font-family='${FONT}' role="img" aria-label="Preview of ${icons.length} icons">
${cells.join('\n')}
</svg>
`;
}

mkdirSync(OUT_DIR, { recursive: true });
for (const theme of Object.keys(THEMES)) {
  const out = join(OUT_DIR, `icons-${theme}.svg`);
  const text = render(theme);
  writeFileSync(out, text);
  const kb = Math.round(Buffer.byteLength(text) / 1024);
  console.log(`[docs] ${out}  ${icons.length} icons, ${kb} KB`);
  if (kb > 1500) console.warn(`[docs] warning: ${out} is large; GitHub may be slow to render it.`);
}
if (skipped) console.log(`[docs] ${skipped} file(s) skipped`);

import {existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, readdirSync} from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const build = path.resolve('../build');
const fixtures = path.join(build, '_fixtures');
mkdirSync(build, {recursive: true});
mkdirSync(fixtures, {recursive: true});

function copyLogo(name) {
  const src = path.resolve('../../resources', name);
  const destDir = path.join(build, 'brand');
  mkdirSync(destDir, {recursive: true});
  if (existsSync(src)) copyFileSync(src, path.join(destDir, name));
}
copyLogo('logo_outline.svg');
// On the navy canvas the logo is a soft off-white, not pure white (pure white bloomed and looked harsh).
const logoSvg = path.resolve('../../resources/logo_outline.svg');
if (existsSync(logoSvg)) writeFileSync(path.join(build, 'brand', 'logo_soft.svg'), readFileSync(logoSvg, 'utf8').replace(/fill="#000000"/g, 'fill="#dbe4f0"'));

const rootScenes = path.join(build, 'scenes.json');
const fixtureScenes = path.join(fixtures, 'scenes.json');
if (!existsSync(fixtureScenes)) {
  const scenes = existsSync(rootScenes) ? readFileSync(rootScenes) : Buffer.from(JSON.stringify({scenes: [], cuts: {teaser: [], short: [], full: []}}, null, 2));
  writeFileSync(fixtureScenes, scenes);
}

const modelPath = path.join(fixtures, 'model.json');
if (!existsSync(modelPath)) {
  const members = [];
  for (let floor = 0; floor < 4; floor++) {
    const z = floor * 900;
    for (let x of [-1600, 0, 1600]) members.push({id: `c-${floor}-${x}`, type: 'column', profile: 'HEA300', material: 'S355JR', mark: 'C1', start: [x, -900, z], end: [x, -900, z + 800], length: 800});
    for (let y of [-900, 900]) members.push({id: `b-${floor}-${y}`, type: 'beam', profile: 'IPE240', material: 'S355JR', mark: 'B1', start: [-1800, y, z + 800], end: [1800, y, z + 800], length: 3600});
    members.push({id: `br-${floor}`, type: 'brace', profile: 'L80', material: 'S355JR', mark: 'BR1', start: [-1600, -900, z], end: [1600, 900, z + 800], length: 3900});
  }
  writeFileSync(modelPath, JSON.stringify({name: 'Fixture frame', members}, null, 2));
}

function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const name = Buffer.from(type);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([name, data])) >>> 0);
  return Buffer.concat([len, name, data, crc]);
}
let table;
function crc32(buf) {
  table ??= Array.from({length: 256}, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  let c = 0xffffffff;
  for (const b of buf) c = table[(c ^ b) & 255] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function rgb(hex) {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function writePng(file, bg, rects) {
  if (existsSync(file)) return;
  const w = 1920, h = 1080;
  const [br, bgc, bb] = rgb(bg);
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) {
    const row = y * (w * 3 + 1); raw[row] = 0;
    for (let x = 0; x < w; x++) {
      let col = [br, bgc, bb];
      for (const r of rects) if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) col = rgb(r.c);
      const i = row + 1 + x * 3; raw[i] = col[0]; raw[i + 1] = col[1]; raw[i + 2] = col[2];
    }
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  writeFileSync(file, Buffer.concat([Buffer.from('\x89PNG\r\n\x1a\n', 'binary'), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]));
}
function shotsFor(lang, theme) {
  const dir = path.join(fixtures, 'capture', `${lang}-${theme}`);
  mkdirSync(dir, {recursive: true});
  const dark = theme === 'dark';
  const bg = dark ? '#0b1220' : '#f6f8fb';
  const panel = dark ? '#172033' : '#ffffff';
  const accent = dark ? '#22d3ee' : '#1d4ed8';
  const green = dark ? '#14b8a6' : '#0f766e';
  const red = '#b91c1c';
  const common = [{x: 90, y: 90, w: 1740, h: 900, c: panel}, {x: 130, y: 140, w: 260, h: 56, c: accent}, {x: 420, y: 140, w: 230, h: 56, c: green}, {x: 1360, y: 140, w: 380, h: 56, c: dark ? '#334155' : '#dbeafe'}];
  const defs = {
    empty: {file: 'empty.png', targets: {load_tekla: [130, 140, 260, 56]}, rects: common},
    parts_loaded: {file: 'parts_loaded.png', targets: {auto_stock: [420, 140, 230, 56], parts_table: [130, 250, 720, 580]}, rects: [...common, {x: 130, y: 250, w: 720, h: 580, c: dark ? '#263244' : '#e2e8f0'}]},
    stock_ready: {file: 'stock_ready.png', targets: {calculate: [690, 140, 230, 56]}, rects: [...common, {x: 920, y: 250, w: 620, h: 130, c: green}]},
    result: {file: 'result.png', targets: {bars_view: [820, 285, 850, 440], overall_waste: [820, 750, 280, 70]}, rects: [...common, {x: 820, y: 285, w: 850, h: 440, c: green}, {x: 820, y: 750, w: 280, h: 70, c: red}]},
    insights: {file: 'insights.png', targets: {insights_panel: [1160, 230, 470, 520], overall_waste: [1230, 640, 310, 80], high_waste_warning: [1190, 330, 410, 140]}, rects: [...common, {x: 1160, y: 230, w: 470, h: 520, c: dark ? '#1e293b' : '#dbeafe'}, {x: 1190, y: 330, w: 410, h: 140, c: red}, {x: 1230, y: 640, w: 310, h: 80, c: red}]},
    export: {file: 'export.png', targets: {export_pdf: [1180, 140, 170, 56], export_excel: [1370, 140, 150, 56], export_csv: [1540, 140, 130, 56]}, rects: [...common, {x: 1180, y: 140, w: 170, h: 56, c: red}, {x: 1370, y: 140, w: 150, h: 56, c: green}, {x: 1540, y: 140, w: 130, h: 56, c: accent}]}
  };
  const shots = Object.entries(defs).map(([id, d]) => {
    writePng(path.join(dir, d.file), bg, d.rects);
    return {id, file: d.file, targets: d.targets};
  });
  writeFileSync(path.join(dir, 'shots.json'), JSON.stringify({lang, theme, size: [1920, 1080], part_count: 42, member_count: 28, config: {kerf_mm: 3, scrap_threshold_mm: 2000}, shots}, null, 2));
}
for (const lang of ['en', 'pt']) for (const theme of ['light', 'dark']) shotsFor(lang, theme);

const asset = (root, fallback) => existsSync(path.join(build, root)) ? root : fallback;
writeFileSync(path.join(build, 'asset-manifest.json'), JSON.stringify({
  scenes: asset('scenes.json', '_fixtures/scenes.json'),
  model: asset('model.json', '_fixtures/model.json'),
  music: existsSync(path.join(build, 'music', 'bed.wav')) && existsSync(path.join(build, 'music', 'bed.json')) ? 'music/bed.json' : null,
  capture: Object.fromEntries(['en', 'pt'].flatMap((lang) => ['light', 'dark'].map((theme) => {
    const key = `${lang}-${theme}`;
    return [key, asset(`capture/${key}/shots.json`, `_fixtures/capture/${key}/shots.json`)];
  }))),
  durations: Object.fromEntries((existsSync(path.join(build, 'audio')) ? readdirSync(path.join(build, 'audio')) : ['en', 'pt']).map((v) => [v, existsSync(path.join(build, 'audio', v, 'durations.json')) ? `audio/${v}/durations.json` : null]))
}, null, 2));

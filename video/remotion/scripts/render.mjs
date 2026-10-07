import {spawnSync} from 'node:child_process';
import {mkdirSync} from 'node:fs';
import path from 'node:path';

const mode = process.argv[2] || 'render';
const rest = process.argv.slice(3);
const propsArg = rest.find((a) => a.startsWith('--props='));
const frameArg = rest.find((a) => a.startsWith('--frame='));
const props = propsArg ? JSON.parse(propsArg.slice('--props='.length).replace(/^'|'$/g, '')) : {};
const lang = props.lang || 'en';
const name = props.voice || lang;  // output file stem: <cut>-<voice>
const cut = props.cut || 'full';
const outDir = path.resolve('../build/out');
mkdirSync(outDir, {recursive: true});
const publicDir = path.resolve('../build');
const input = 'src/index.ts';
const base = ['remotion', mode === 'still' ? 'still' : 'render', input, 'M13SNestDemo'];
const out = mode === 'still'
  ? path.join(outDir, `${cut}-${name}-f${frameArg ? frameArg.split('=')[1] : '0'}.png`)
  : props.stem
    ? path.join(outDir, 'audio', `${cut}-${name}-${props.stem}.wav`)
    : path.join(outDir, `${cut}-${name}.mp4`);
mkdirSync(path.dirname(out), {recursive: true});
const args = [...base, out, '--public-dir', publicDir, '--props', JSON.stringify(props)];
if (mode === 'still') args.push('--frame', frameArg ? frameArg.split('=')[1] : '0');
args.push('--gl', 'angle');
for (const arg of rest) if (!arg.startsWith('--props=') && !arg.startsWith('--frame=')) args.push(arg);
if (props.stem) args.push('--codec', 'wav');
else if (mode !== 'still') args[4] = out.replace(/\.mp4$/, '.raw.mp4');
const result = spawnSync('npx', args, {stdio: 'inherit'});
if (result.status !== 0 || mode === 'still' || props.stem) process.exit(result.status ?? 1);
// Master: measure loudness, apply static gain to -14 LUFS, then a fast peak limiter at -2.5 dBFS
// (keeps the mix dynamics; single-pass dynamic loudnorm pumped the gaps up).
// Remotion's bundled ffmpeg lacks alimiter; use the full imageio-ffmpeg build.
const FF = spawnSync('uvx', ['--quiet', '--from', 'imageio-ffmpeg', 'python', '-c',
  'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'], {encoding: 'utf8'}).stdout.trim();
const ff = (a) => spawnSync(FF, ['-y', '-hide_banner', ...a], {encoding: 'utf8'});
const loudness = (file) => {
  const probe = ff(['-i', file, '-vn', '-af', 'loudnorm=I=-14:TP=-1.5:print_format=json', '-f', 'null', '-']);
  return Number(JSON.parse((probe.stderr || '').match(/\{[^{}]*"input_i"[^{}]*\}/)[0]).input_i);
};
const encode = (gain) => spawnSync(FF, ['-y', '-loglevel', 'error', '-i', args[4], '-c:v', 'copy',
  '-af', `volume=${gain.toFixed(2)}dB,alimiter=limit=0.75:attack=1:release=80:level=0`,
  '-ar', '48000', '-c:a', 'aac', '-b:a', '320k', out], {stdio: 'inherit'});
// The limiter shaves loudness off a dense mix, so correct the static gain once from the measured result.
let gain = -14 - loudness(args[4]);
let master = encode(gain);
const miss = -14 - loudness(out);
if (master.status === 0 && Math.abs(miss) > 0.3) master = encode(gain += miss);
process.exit(master.status ?? 1);

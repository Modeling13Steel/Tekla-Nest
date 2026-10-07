import React, {useEffect, useState} from 'react';
import {loadFont as loadGeist} from '@remotion/google-fonts/Geist';
import {loadFont as loadGeistMono} from '@remotion/google-fonts/GeistMono';
import {noise2D} from '@remotion/noise';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  Img,
  Sequence,
  cancelRender,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import './style.css';

const {fontFamily: geist} = loadGeist('normal', {weights: ['400', '500', '600', '700'], subsets: ['latin', 'latin-ext'], ignoreTooManyRequestsWarning: true});
const {fontFamily: mono} = loadGeistMono('normal', {weights: ['500', '600'], subsets: ['latin', 'latin-ext'], ignoreTooManyRequestsWarning: true});
const C = {navy: '#0b1220', deep: '#070b14', panel: '#111a2e', blue: '#3b82f6', blueDeep: '#1d4ed8', teal: '#14b8a6', cyan: '#22d3ee', text: '#f8fafc', muted: '#94a3b8', light: '#f6f8fb', ink: '#0f172a', slate: '#64748b'};
const FPS = 30;
const W = 1920, H = 1080;
const brandEase = Easing.bezier(0.16, 1, 0.3, 1);
const pushEase = Easing.bezier(0.65, 0, 0.35, 1);

type Lang = 'en' | 'pt' | string;
type Cut = 'teaser' | 'short' | 'full' | string;
type Stem = 'vo' | 'sfx' | 'music';
// `voice` names the audio folder build/audio/<voice> (e.g. 'pt-raquel'); it defaults to the language.
type DemoProps = {lang?: Lang; cut?: Cut; cta_url?: string; stem?: Stem; voice?: string};
type SceneSpec = {n: number; beat: string; p: number; seconds: number; render: string; interaction: string; transition: string; sfx: string; vo: Record<string, string>; caption: Record<string, string>};
type ScenesDoc = {scenes: SceneSpec[]; cuts: Record<string, number[]>};
type Member = {id: string; type: string; profile: string; material: string; mark: string; start: [number, number, number]; end: [number, number, number]; length: number};
type ModelDoc = {name: string; members: Member[]};
type Shot = {id: string; file: string; targets: Record<string, [number, number, number, number]>};
type ShotsDoc = {lang: string; theme: string; size: [number, number]; shots: Shot[]};
type Kind = 'fade' | 'slide-left' | 'slide-up' | 'wipe' | 'zoom' | 'cut';
type TimedScene = {scene: SceneSpec; from: number; frames: number; voSeconds: number; voFrom: number; enter: Kind; enterFrames: number; exit: Kind; exitFrames: number};
type Cue = {name: string; at: number};
type Bed = {bpm: number; duration: number; bars: number[]; outro_at: number};
type MusicPlan = {headTrim: number; outroAt: number; outroTrim: number; duck: number[]};
type Loaded = {model: ModelDoc; shots: ShotsDoc; shotBase: string; timeline: TimedScene[]; totalFrames: number; cues: Cue[]; music: MusicPlan | null};
type AssetManifest = {scenes?: string; model?: string; music?: string | null; capture?: Record<string, string>; durations?: Record<string, string | null>};

const s = (seconds: number) => Math.ceil(seconds * FPS);
const T = 12;  // transition overlap, frames
const BREATH = 0.55, LEAD = 0.25, LEAD_CUT = 0.05;
const CTA_VO_DELAY = 0.7, CTA_HOLD = 1.2;
const KINDS: Kind[] = ['fade', 'slide-left', 'slide-up', 'wipe', 'zoom', 'cut'];
// Frames from file start to the audible peak, so each sound lands on its visual beat.
const PEAK: Record<string, number> = {whoosh_a: 7, whoosh_b: 5, hit: 27, click: 0, pop: 1};
const SFX_GAIN = 0.8;  // -1.9 dB trim on the baked SFX peaks
const MUSIC_INTRO_SKIP = 8.5; // s; the bed's first bars are a quiet build
const MUSIC_OPEN_DB = -5, MUSIC_DUCK_DB = -16.5, DUCK_ATTACK = 6, DUCK_RELEASE = 12;

const isCta = (scene: SceneSpec) => /cta/i.test(scene.beat);
const kindOf = (t: string): Kind => (KINDS.find((k) => t.trim().toLowerCase().startsWith(k)) || 'fade');
const cuesOf = (scene: SceneSpec) => [...(scene.sfx || '').matchAll(/(\w+)@([\d.]+)/g)].map((m) => ({name: m[1], at: Number(m[2])}));
const cueFrame = (scene: SceneSpec, name: string, frames: number, fallback: number) => {
  const c = cuesOf(scene).find((x) => x.name === name);
  return c ? Math.round(frames * c.at) : fallback;
};

async function readJson<T>(paths: string[]): Promise<{data: T; path: string}> {
  let last: unknown;
  for (const path of paths) {
    try {
      const res = await fetch(staticFile(path));
      if (res.ok) return {data: await res.json(), path};
      last = `${path}: ${res.status}`;
    } catch (err) {
      last = err;
    }
  }
  throw new Error(`Missing public asset. Tried ${paths.join(', ')} (${String(last)})`);
}
async function optionalJson<T>(paths: string[], fallback: T): Promise<T> {
  try { return (await readJson<T>(paths)).data; } catch { return fallback; }
}
const baseDir = (path: string) => path.split('/').slice(0, -1).join('/');

function buildTimeline(scenes: SceneSpec[], durations: Record<string, number>, cut: Cut): TimedScene[] {
  // The teaser must fit a 15 s non-skippable slot, so it breathes and holds a little less.
  const [breath, ctaDelay, ctaHold] = cut === 'teaser' ? [0.25, 0.3, 0.45] : [BREATH, CTA_VO_DELAY, CTA_HOLD];
  const out: TimedScene[] = [];
  scenes.forEach((scene, i) => {
    const enter = i === 0 ? 'fade' : kindOf(scene.transition);
    const enterFrames = enter === 'cut' ? 0 : T;
    const voSeconds = Number(durations[String(scene.n)] || 0);
    const lead = isCta(scene) ? ctaDelay : enter === 'cut' ? LEAD_CUT : LEAD;
    const seconds = isCta(scene)
      ? Math.max(scene.seconds, lead + voSeconds + ctaHold)
      : Math.max(scene.seconds, voSeconds ? lead + voSeconds + breath : 0);
    const prev = out[i - 1];
    const from = prev ? prev.from + prev.frames - (i === 0 ? 0 : enterFrames) : 0;
    if (prev) { prev.exit = enter; prev.exitFrames = enterFrames; }
    out.push({scene, from, frames: s(seconds), voSeconds, voFrom: s(lead), enter, enterFrames, exit: 'cut', exitFrames: 0});
  });
  return out;
}

function buildCues(timeline: TimedScene[]): Cue[] {
  const cues: Cue[] = [];
  let alt = 0;
  timeline.forEach((t, i) => {
    const own = cuesOf(t.scene);
    // A hit already carries its own riser, so it replaces the transition whoosh.
    const hitEarly = own.some((c) => c.name === 'hit' && c.at * t.frames < 15);
    if (i > 0 && t.enter !== 'cut' && !hitEarly) {
      const name = alt++ % 2 ? 'whoosh_b' : 'whoosh_a';
      cues.push({name, at: t.from + Math.round(t.enterFrames / 2) - PEAK[name]});
    }
    for (const c of own) cues.push({name: c.name, at: t.from + Math.round(t.frames * c.at) - (PEAK[c.name] ?? 0)});
  });
  return cues.map((c) => ({...c, at: Math.max(0, c.at)}));
}

function planMusic(bed: Bed, timeline: TimedScene[], total: number): MusicPlan {
  const outroLen = bed.duration - bed.outro_at;
  const outroAt = Math.max(0, total - s(outroLen));
  // Start the track so that, at the splice, the head is on a downbeat just like the outro.
  // Short cuts skip the track's quiet intro so the bed is energetic from the first frame.
  const skip = total < s(35) ? MUSIC_INTRO_SKIP : 0;
  const bar = bed.bars.find((b) => b >= outroAt / FPS + skip && b < bed.outro_at) ?? outroAt / FPS;
  const headTrim = Math.round((bar - outroAt / FPS) * FPS);
  const duck = new Array<number>(total).fill(0);
  for (const t of timeline) {
    if (!t.voSeconds) continue;
    const a = t.from + t.voFrom, b = a + s(t.voSeconds);
    for (let f = Math.max(0, a - DUCK_ATTACK); f < Math.min(total, b + DUCK_RELEASE); f++) {
      const v = f < a ? (f - (a - DUCK_ATTACK)) / DUCK_ATTACK : f <= b ? 1 : 1 - (f - b) / DUCK_RELEASE;
      duck[f] = Math.max(duck[f], v);
    }
  }
  return {headTrim, outroAt, outroTrim: Math.round(bed.outro_at * FPS), duck};
}

async function loadData(props: DemoProps): Promise<Loaded> {
  const lang = props.lang || 'en';
  const cut = props.cut || 'full';
  const manifest = await optionalJson<AssetManifest>(['asset-manifest.json'], {});
  const scenesDoc = (await readJson<ScenesDoc>(manifest.scenes ? [manifest.scenes] : ['scenes.json', '_fixtures/scenes.json'])).data;
  const voice = props.voice || lang;
  const durationPath = manifest.durations?.[voice];
  const durations = await optionalJson<Record<string, number>>(durationPath ? [durationPath] : [`audio/${voice}/durations.json`], {});
  const model = (await readJson<ModelDoc>(manifest.model ? [manifest.model] : ['model.json', '_fixtures/model.json'])).data;
  const key = `${lang}-light`;
  const shots = await readJson<ShotsDoc>(manifest.capture?.[key] ? [manifest.capture[key]] : [`capture/${key}/shots.json`, `_fixtures/capture/${key}/shots.json`]);
  const wanted = new Set(scenesDoc.cuts[cut] || scenesDoc.cuts.full || scenesDoc.scenes.map((x) => x.n));
  const timeline = buildTimeline(scenesDoc.scenes.filter((scene) => wanted.has(scene.n)), durations, cut);
  const last = timeline[timeline.length - 1];
  const totalFrames = last ? last.from + last.frames : FPS;
  const bed = manifest.music ? await optionalJson<Bed | null>([manifest.music], null) : null;
  return {model, shots: shots.data, shotBase: baseDir(shots.path), timeline, totalFrames, cues: buildCues(timeline), music: bed ? planMusic(bed, timeline, totalFrames) : null};
}

export const Root: React.FC = () => (
  <Composition
    id="M13SNestDemo"
    component={DemoVideo}
    fps={FPS}
    width={W}
    height={H}
    defaultProps={{lang: 'en', cut: 'full', cta_url: ''}}
    calculateMetadata={async ({props}) => ({durationInFrames: (await loadData(props as DemoProps)).totalFrames})}
  />
);

const DemoVideo: React.FC<DemoProps> = (props) => {
  const [data, setData] = useState<Loaded | null>(null);
  useEffect(() => {
    const handle = delayRender('load demo-video inputs');
    loadData(props).then((loaded) => { setData(loaded); continueRender(handle); }).catch((err) => cancelRender(err));
  }, [props.lang, props.cut, props.cta_url, props.voice]);
  if (!data) return <AbsoluteFill style={{background: C.navy}} />;
  return <AssembledVideo data={data} props={props} />;
};

const db = (x: number) => Math.pow(10, x / 20);
const AssembledVideo: React.FC<{data: Loaded; props: DemoProps}> = ({data, props}) => {
  const lang = props.lang || 'en';
  const want = (stem: Stem) => !props.stem || props.stem === stem;
  const m = data.music;
  const total = data.totalFrames;
  const musicGain = (f: number) => {
    const d = m?.duck[Math.min(total - 1, Math.max(0, f))] ?? 0;
    const edge = Math.min(1, f / 9, (total - f) / 15);  // 0.3 s in, 0.5 s out
    return db(MUSIC_OPEN_DB + (MUSIC_DUCK_DB - MUSIC_OPEN_DB) * d) * Math.max(0, edge);
  };
  return (
    <AbsoluteFill style={{fontFamily: geist, background: C.navy}}>
      <Backdrop />
      {data.timeline.map((timed) => (
        <Sequence key={timed.scene.n} from={timed.from} durationInFrames={timed.frames}>
          <Scene timed={timed} data={data} props={props} />
        </Sequence>
      ))}
      {m && want('music') && <>
        <Sequence durationInFrames={m.outroAt + 3}>
          <Audio src={staticFile('music/bed.wav')} trimBefore={m.headTrim} volume={(f) => musicGain(f) * interpolate(f, [m.outroAt - 2, m.outroAt + 3], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})} />
        </Sequence>
        <Sequence from={m.outroAt - 2}>
          <Audio src={staticFile('music/bed.wav')} trimBefore={m.outroTrim - 2} volume={(f) => musicGain(f + m.outroAt - 2) * interpolate(f, [0, 3], [0, 1], {extrapolateRight: 'clamp'})} />
        </Sequence>
      </>}
      {want('sfx') && data.cues.map((c, i) => <Sequence key={`${c.name}-${i}`} from={c.at}><Audio src={staticFile(`sfx/${c.name}.wav`)} volume={SFX_GAIN} /></Sequence>)}
      {want('vo') && data.timeline.filter((t) => t.voSeconds > 0).map((t) => (
        <Sequence key={`vo-${t.scene.n}`} from={t.from + t.voFrom}><Audio src={staticFile(`audio/${props.voice || lang}/${t.scene.n}.wav`)} /></Sequence>
      ))}
    </AbsoluteFill>
  );
};

const ease = (frame: number, range: [number, number], out: [number, number] = [0, 1], easing = brandEase) =>
  interpolate(frame, range, out, {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});

// Shared canvas: drifting brand glows over a faint blueprint grid. Continuous across scenes.
const Backdrop: React.FC = () => {
  const f = useCurrentFrame();
  const blob = (seed: string, x: number, y: number, color: string, size: number) => {
    const dx = noise2D(seed, f * 0.004, 0) * 220, dy = noise2D(seed, 0, f * 0.004) * 160;
    return <div className="blob" style={{left: x + dx - size / 2, top: y + dy - size / 2, width: size, height: size, background: `radial-gradient(circle, ${color} 0%, transparent 62%)`}} />;
  };
  return <AbsoluteFill className="backdrop">
    {blob('a', 420, 260, 'rgba(59,130,246,.38)', 1300)}
    {blob('b', 1560, 820, 'rgba(20,184,166,.26)', 1200)}
    {blob('c', 1380, 160, 'rgba(34,211,238,.16)', 900)}
    <div className="grid" style={{backgroundPosition: `0 ${f * 0.25}px`}} />
    <div className="vignette" />
  </AbsoluteFill>;
};

function transitionStyle(kind: Kind, p: number, dir: 'in' | 'out'): React.CSSProperties {
  if (kind === 'cut' || p <= 0) return {};
  const q = dir === 'in' ? 1 - p : p;  // how far "away" the scene is
  switch (kind) {
    case 'slide-left': return {transform: `translateX(${(dir === 'in' ? 1 : -1) * q * W}px)`};
    case 'slide-up': return {transform: `translateY(${(dir === 'in' ? 1 : -1) * q * H}px)`};
    case 'wipe': return {clipPath: dir === 'in' ? `inset(0 ${q * 100}% 0 0)` : `inset(0 0 0 ${q * 100}%)`};
    case 'zoom': return dir === 'in'
      ? {transform: `scale(${1 + 0.22 * q})`, opacity: 1 - q, filter: `blur(${q * 10}px)`}
      : {transform: `scale(${1 - 0.1 * q})`, opacity: 1 - q, filter: `blur(${q * 8}px)`};
    default: return {opacity: 1 - q};
  }
}

const STEP: Record<number, number> = {5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7};
const STEP_LABEL: Record<string, string[]> = {
  en: ['Import', 'Your stock', 'Market stock', 'Optimize', 'Insights', 'Purchase', 'Export'],
  pt: ['Importar', 'O seu stock', 'Stock de mercado', 'Otimizar', 'Sugestões', 'Compra', 'Exportar'],
};
const captionOf = (scene: SceneSpec, lang: string) => (scene.caption[lang] || scene.caption.en || '').replace(/\s*·?\s*`?\{cta_url\}`?/g, '').trim();

type SceneProps = {frames: number; voFrom: number; voFrames: number; lang: string; caption: string; scene: SceneSpec};

const Scene: React.FC<{timed: TimedScene; data: Loaded; props: DemoProps}> = ({timed, data, props}) => {
  const frame = useCurrentFrame();
  const {scene, frames} = timed;
  const lang = props.lang || 'en';
  const voFrames = timed.voSeconds > 0 ? s(timed.voSeconds) : Math.round(frames * 0.7);
  const pIn = timed.enterFrames ? ease(frame, [0, timed.enterFrames], [0, 1], timed.enter === 'zoom' || timed.enter === 'fade' ? brandEase : pushEase) : 1;
  const pOut = timed.exitFrames ? ease(frame, [frames - timed.exitFrames, frames], [0, 1], timed.exit === 'zoom' || timed.exit === 'fade' ? brandEase : pushEase) : 0;
  const last = timed === data.timeline[data.timeline.length - 1];
  const fadeEnd = last ? ease(frame, [frames - 15, frames], [1, 0]) : 1;
  const p: SceneProps = {frames, voFrom: timed.voFrom, voFrames, lang, caption: captionOf(scene, lang), scene};
  const step = STEP[scene.n];
  const chip = step ? {n: step, label: (STEP_LABEL[lang] || STEP_LABEL.en)[step - 1]} : undefined;
  const content = (() => {
    switch (scene.n) {
      case 1: return <ColdOpen {...p} />;
      case 2: return <Question {...p} />;
      case 3: return <Introducing {...p} />;
      case 4: return <ModelScene model={data.model} {...p} />;
      case 5: return <AppScene data={data} {...p} chip={chip} layout="right" accent={C.blue} phases={[{until: 0.36, shot: 'empty', target: 'load_tekla', click: 0.34}, {shot: 'parts_loaded', target: 'parts_table'}]} />;
      case 6: return <AppScene data={data} {...p} chip={chip} layout="left" accent={C.teal} phases={[{until: 0.28, shot: 'parts_loaded', target: 'client_stock', click: 0.26}, {shot: 'client_stock', target: 'stock_tabs'}]} />;
      case 7: return <AppScene data={data} {...p} chip={chip} layout="center" accent={C.cyan} phases={[{until: 0.26, shot: 'client_stock', target: 'auto_stock', click: 0.24}, {shot: 'market_stock', target: 'stock_tabs'}]} />;
      case 8: return <SixStrategies data={data} {...p} chip={chip} />;
      case 9: return <AppScene data={data} {...p} chip={chip} layout="right" accent={C.blue} phases={[{until: 0.5, shot: 'insights', target: 'insights_panel'}, {shot: 'insights', target: 'insight_warning'}]} />;
      case 10: return <AppScene data={data} {...p} chip={chip} layout="center" accent={C.teal} phases={[{until: 0.5, shot: 'purchase', target: 'purchase_table'}, {shot: 'purchase', target: 'purchase_total'}]} />;
      case 11: return <AppScene data={data} {...p} chip={chip} layout="left" accent={C.blue} cards phases={[{until: 0.52, shot: 'export', target: 'export_pdf'}, {until: 0.74, shot: 'export', target: 'export_excel'}, {shot: 'export', target: 'export_csv'}]} />;
      case 12: return <Fit {...p} />;
      case 13: return <Payoff {...p} />;
      case 14: return <EndCard {...p} cta={props.cta_url || ''} />;
      default: return null;
    }
  })();
  const edge = timed.enter === 'wipe' && pIn > 0 && pIn < 1;
  return <AbsoluteFill style={{opacity: fadeEnd}}>
    <AbsoluteFill style={{...transitionStyle(timed.exit, pOut, 'out')}}>
      <AbsoluteFill style={{...transitionStyle(timed.enter, pIn, 'in')}}>{content}</AbsoluteFill>
    </AbsoluteFill>
    {edge && <div className="wipeEdge" style={{left: pIn * W - 2}} />}
  </AbsoluteFill>;
};

// Kinetic type: words spring in on their share of the VO, sharpening from a blur. *word* = gradient.
type Token = {w: string; hl: boolean};
function tokens(text: string): Token[] {
  let hl = false;
  return text.split(/\s+/).filter(Boolean).map((raw) => {
    const open = raw.startsWith('*');
    const close = raw.replace(/[?.!,]+$/, '').endsWith('*');
    if (open) hl = true;
    const t = {w: raw.replace(/\*/g, ''), hl};
    if (close) hl = false;
    return t;
  });
}
const plain = (text: string) => text.replace(/\*/g, '');
function chunkStarts(chunks: string[], voFrames: number, lead = 0) {
  const total = chunks.reduce((n, c) => n + c.length + 1, 0) || 1;
  let acc = 0;
  return chunks.map((c) => { const at = lead + Math.round((acc / total) * voFrames * 0.85); acc += c.length + 1; return at; });
}
const Words: React.FC<{text: string; start: number; span: number; className?: string; style?: React.CSSProperties}> = ({text, start, span, className, style}) => {
  const frame = useCurrentFrame();
  const toks = tokens(text);
  const at = chunkStarts(toks.map((t) => t.w), span, start);
  // Side headlines start each sentence on its own line, so narrow columns never wrap mid-thought.
  const breaks = /headline|question/.test(className || '');
  return <div className={`words ${className || ''}`} style={style}>{toks.map((t, i) => {
    const sp = spring({frame: frame - at[i], fps: FPS, config: {damping: 14, stiffness: 170, mass: 0.7}});
    return <React.Fragment key={i}>
      <span className={t.hl ? 'hl' : undefined} style={{opacity: Math.min(1, sp * 1.6), transform: `translateY(${(1 - sp) * 46}px)`, filter: `blur(${Math.max(0, 1 - sp) * 12}px)`}}>{t.w}</span>
      {breaks && i < toks.length - 1 && /[.?!]$/.test(t.w) && <br />}
    </React.Fragment>;
  })}</div>;
};
const Chip: React.FC<{n: number; label: string; accent: string; at: number; light?: boolean}> = ({n, label, accent, at, light}) => {
  const frame = useCurrentFrame();
  const sp = spring({frame: frame - at, fps: FPS, config: {damping: 16, stiffness: 200}});
  return <div className={`chip ${light ? 'light' : ''}`} style={{opacity: sp, transform: `translateX(${(1 - sp) * -30}px)`}}>
    {n > 0 && <span className="chipNum" style={{fontFamily: mono, color: accent}}>{String(n).padStart(2, '0')}</span>}{label}
  </div>;
};

const ColdOpen: React.FC<SceneProps> = ({frames, voFrom, voFrames, caption, scene}) => {
  const frame = useCurrentFrame();
  const cutAt = cueFrame(scene, 'pop', frames, Math.round(frames * 0.3));
  const bar = ease(frame, [2, 22]);
  const fall = ease(frame, [cutAt + 2, cutAt + 30], [0, 1], Easing.in(Easing.quad));
  const flash = interpolate(frame, [cutAt, cutAt + 3, cutAt + 14], [0, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const [a, b] = caption.split(/(?<=\.)\s+/);
  return <AbsoluteFill className="center">
    <div className="steel" style={{width: 1240 * bar, marginTop: -260}}>
      <div className="steelMain" />
      <div className="steelOff" style={{transform: `translate(${fall * 60}px, ${fall * 420}px) rotate(${fall * 14}deg)`, opacity: 1 - fall}} />
      <div className="cutFlash" style={{opacity: flash, transform: `scaleY(${1 + flash * 5})`}} />
    </div>
    <div className="coldLines">
      <Words text={a || ''} start={voFrom} span={Math.round(voFrames * 0.45)} />
      <Words text={b || ''} start={voFrom + Math.round(voFrames * 0.48)} span={Math.round(voFrames * 0.5)} className="muted" />
    </div>
  </AbsoluteFill>;
};

const Question: React.FC<SceneProps> = ({voFrom, voFrames, caption}) =>
  <AbsoluteFill className="center"><Words text={caption} start={voFrom - 2} span={voFrames} className="question" /></AbsoluteFill>;

const Logo: React.FC<{className?: string; sweep?: number}> = ({className, sweep}) => <div className={`logoWrap ${className || ''}`}>
  <Img src={staticFile('brand/logo_soft.svg')} className="logo" />
  {sweep !== undefined && <div className="logoSweep" style={{WebkitMaskImage: `url(${staticFile('brand/logo_outline.svg')})`, maskImage: `url(${staticFile('brand/logo_outline.svg')})`, backgroundPosition: `${interpolate(sweep, [0, 1], [130, -30])}% 0`}} />}
</div>;

// Mirrors EndCard (same logo size, position, bloom and sweep) so the film opens and closes on the same card.
const Introducing: React.FC<SceneProps> = ({frames, scene, caption, voFrom, voFrames}) => {
  const frame = useCurrentFrame();
  const [name, what] = caption.split('·').map((x) => x.trim());
  const land = cueFrame(scene, 'hit', frames, 8);
  const {sp, bloom} = brandCard(frame, land);
  return <AbsoluteFill className="center">
    <div className="bloom" style={{opacity: bloom, transform: `scale(${0.6 + bloom * 0.5})`}} />
    <div className="endStack">
      <div style={{opacity: Math.min(1, sp * 1.5), transform: `scale(${0.85 + sp * 0.15})`, filter: `blur(${Math.max(0, 1 - sp) * 12}px)`}}><Logo className="small" sweep={ease(frame, [land + 4, land + 34])} /></div>
      <Words text={name || ''} start={voFrom + Math.round(voFrames * 0.2)} span={6} className="tagline" />
      {/* Sits in the end card's button slot (same height), so the logo lands in exactly the same place. */}
      <div className="subline"><Words text={what || ''} start={voFrom + Math.round(voFrames * 0.42)} span={Math.round(voFrames * 0.35)} /></div>
    </div>
  </AbsoluteFill>;
};

const brandCard = (frame: number, land: number) => ({
  sp: spring({frame: frame - land + 6, fps: FPS, config: {damping: 13, stiffness: 150}}),
  bloom: interpolate(frame, [land - 2, land + 4, land + 40], [0, 0.75, 0.45], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
});

const SixStrategies: React.FC<SceneProps & {data: Loaded; chip?: {n: number; label: string}}> = (props) => {
  const frame = useCurrentFrame();
  const {frames, caption, scene, voFrom, voFrames} = props;
  const land = cueFrame(scene, 'hit', frames, 8);
  const typeEnd = Math.round(frames * 0.56);
  const [a, b] = caption.split(/(?<=\.)\s+/);
  const split = (t = '') => { const m = t.match(/^(\d+)\s+(.*)$/); return m ? [Number(m[1]), m[2]] as const : [0, t] as const; };
  const [n1, w1] = split(a), [n2, w2] = split(b);
  const count = Math.round(interpolate(frame, [Math.max(0, land - 9), land], [1, n1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const pop = spring({frame: frame - land, fps: FPS, config: {damping: 9, stiffness: 220}});
  const typeOut = ease(frame, [typeEnd - 6, typeEnd + 4]);
  const secondAt = voFrom + Math.round(voFrames * 0.5);
  return <AbsoluteFill>
    {frame < typeEnd + 4 && <AbsoluteFill className="center" style={{opacity: 1 - typeOut, transform: `scale(${1 - typeOut * 0.08})`}}>
      <div className="six">
        <div className="sixRow"><span className="sixNum hl" style={{fontFamily: mono, transform: `scale(${1.25 - 0.25 * pop})`}}>{count}</span><Words text={w1} start={land + 2} span={10} className="sixWord" /></div>
        <div className="sixRow small"><span className="sixNum" style={{fontFamily: mono, opacity: ease(frame, [secondAt, secondAt + 8]), color: C.cyan}}>{n2 || ''}</span><Words text={w2} start={secondAt + 2} span={8} className="sixWord" /></div>
      </div>
    </AbsoluteFill>}
    {frame >= typeEnd - 6 && <Sequence from={typeEnd - 6} layout="none">
      <AppScene {...props} frames={frames - typeEnd + 6} voFrom={0} caption="" layout="center" accent={C.blue} phases={[{until: 0.14, shot: 'stock_ready', target: 'calculate', click: 0.12}, {shot: 'result', target: 'overall_waste'}]} />
    </Sequence>}
  </AbsoluteFill>;
};

type Rect = [number, number, number, number];
type Phase = {until?: number; shot: string; target: string; click?: number};
type Box = {width: number; height: number};
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const ZOOM: Record<string, number> = {parts_table: 1.5, stock_tabs: 1.6, bars_view: 1.5, insights_panel: 1.8, purchase_total: 2.2, purchase_table: 1.5};
function focusTransform(rect: Rect | undefined, target: string, progress: number, box: Box) {
  const base = box.width / 1920;
  const fit = rect ? Math.max(1, Math.min(box.width * 0.9 / rect[2], box.height * 0.8 / rect[3]) / base) : 1;
  const zoom = rect ? interpolate(progress, [0, 1], [1, Math.min(ZOOM[target] ?? 2.0, fit)], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const k = base * zoom;
  if (!rect) return {k, tx: 0, ty: 0, mapped: undefined as Rect | undefined};
  const cx = rect[0] + rect[2] / 2, cy = rect[1] + rect[3] / 2;
  const tx = clamp(box.width / 2 - cx * k, box.width - 1920 * k, 0);
  const ty = clamp(box.height / 2 - cy * k, box.height - 1080 * k, 0);
  return {k, tx, ty, mapped: [tx + rect[0] * k, ty + rect[1] * k, rect[2] * k, rect[3] * k] as Rect};
}
function findRect(doc: ShotsDoc, shotId: string, target: string): Rect | undefined {
  const own = doc.shots.find((x) => x.id === shotId)?.targets[target];
  return (own || doc.shots.map((x) => x.targets[target]).find(Boolean)) as Rect | undefined;
}

type Layout = 'left' | 'right' | 'center';
const CHROME = 38;
const LAYOUT: Record<Layout, {x: number; y: number; w: number; h: number}> = {
  right: {x: 600, y: 172, w: 1240, h: 698},
  left: {x: 80, y: 172, w: 1240, h: 698},
  center: {x: 290, y: 46, w: 1340, h: 754},
};

const AppScene: React.FC<SceneProps & {data: Loaded; phases: Phase[]; accent: string; layout: Layout; cards?: boolean; chip?: {n: number; label: string}}> = ({data, frames, caption, phases, accent, cards, layout, chip, voFrom, voFrames}) => {
  const frame = useCurrentFrame();
  const L = LAYOUT[layout];
  const box = {width: L.w, height: L.h};
  const p = frame / frames;
  const i = Math.max(0, phases.findIndex((ph) => ph.until === undefined || p < ph.until));
  const phase = phases[i];
  const start = i === 0 ? 0 : phases[i - 1].until || 0;
  const local = (p - start) / Math.max(0.01, (phase.until ?? 1) - start);
  const doc = data.shots;
  const shot = doc.shots.find((x) => x.id === phase.shot) || doc.shots[0];
  const rect = findRect(doc, phase.shot, phase.target);
  const focus = focusTransform(rect, phase.target, ease(local, [0.05, 0.5]), box);
  const ring = ease(local, [0.25, 0.5]);
  const clickF = phase.click !== undefined ? Math.round(phase.click * frames) : -1;
  const pressed = clickF >= 0 && frame >= clickF && frame < clickF + 6;
  const ripple = clickF >= 0 ? ease(frame, [clickF, clickF + 14]) : 0;
  const cursor = focus.mapped ? {x: focus.mapped[0] + focus.mapped[2] * 0.5, y: focus.mapped[1] + focus.mapped[3] * 0.55} : undefined;
  const enter = spring({frame: frame - 2, fps: FPS, config: {damping: 20, stiffness: 90, mass: 0.9}});
  const side = layout === 'right' ? -1 : layout === 'left' ? 1 : 0;
  const drift = interpolate(frame, [0, frames], [0, 1]);
  const ry = side * (interpolate(enter, [0, 1], [26, 9]) - drift * 4);
  const rx = layout === 'center' ? interpolate(enter, [0, 1], [18, 3]) - drift * 2 : 4;
  const ty = layout === 'center' ? (1 - enter) * 140 : 0;
  const tx = side * -(1 - enter) * 120;
  const headX = layout === 'right' ? 96 : 1380;
  return <AbsoluteFill>
    <div className="winGlow" style={{left: L.x - 80, top: L.y - 60, width: L.w + 160, height: L.h + CHROME + 120, background: `radial-gradient(closest-side, ${accent}55, transparent)`, opacity: enter}} />
    <div className="stage">
      <div className="window" style={{left: L.x, top: L.y, width: L.w, height: L.h + CHROME, opacity: Math.min(1, enter * 1.4), transform: `translate(${tx}px, ${ty}px) rotateY(${ry}deg) rotateX(${rx}deg) scale(${0.94 + enter * 0.06})`}}>
        <div className="chrome"><Img src={staticFile('brand/logo_outline.svg')} className="chromeLogo" /><span>Nest</span><i /><i /><i /></div>
        <div className="viewport" style={{width: L.w, height: L.h}}>
          {shot && <Img src={staticFile(`${data.shotBase}/${shot.file}`)} className="shot" style={{transform: `matrix(${focus.k},0,0,${focus.k},${focus.tx},${focus.ty})`}} />}
          {focus.mapped && <div className="ring" style={{left: focus.mapped[0] - 8, top: focus.mapped[1] - 8, width: focus.mapped[2] + 16, height: focus.mapped[3] + 16, borderColor: accent, boxShadow: `0 0 0 6px ${accent}22, 0 0 40px ${accent}66`, opacity: ring}} />}
          {cursor && clickF >= 0 && frame >= clickF && <div className="ripple" style={{left: cursor.x - 40, top: cursor.y - 40, borderColor: accent, opacity: 1 - ripple, transform: `scale(${0.3 + ripple})`}} />}
          {clickF >= 0 && cursor && frame < clickF + 16 && <Cursor x={cursor.x} y={cursor.y} pressed={pressed} opacity={ease(frame, [clickF - 16, clickF - 8]) * ease(frame, [clickF + 10, clickF + 16], [1, 0])} />}
          {cards && <ExportCards progress={p} />}
        </div>
      </div>
    </div>
    {layout === 'center'
      ? <>{chip && <div className="chipTop"><Chip {...chip} accent={accent} at={4} /></div>}{caption && <Words text={caption} start={voFrom} span={voFrames} className="bottomLine" />}</>
      : <div className="side" style={{left: headX}}>
          {chip && <Chip {...chip} accent={accent} at={4} />}
          <Words text={caption} start={voFrom} span={voFrames} className="headline" />
          <div className="accentBar" style={{background: `linear-gradient(90deg, ${accent}, ${C.cyan})`, width: 120 * ease(frame, [voFrom + 6, voFrom + 24])}} />
        </div>}
  </AbsoluteFill>;
};
const Cursor: React.FC<{x: number; y: number; pressed: boolean; opacity: number}> = ({x, y, pressed, opacity}) =>
  <svg className="cursor" style={{left: x, top: y, opacity, transform: `scale(${pressed ? 0.86 : 1})`}} width="30" height="40" viewBox="0 0 30 40"><path d="M2 2l24 21-11 1.6L9 36 2 2z" fill="#0f172a" stroke="#fff" strokeWidth="2.2" strokeLinejoin="round" /></svg>;
const ExportCards: React.FC<{progress: number}> = ({progress}) => {
  const frame = useCurrentFrame();
  return <div className="cards">{[['PDF', '#ef4444'], ['Excel', '#16a34a'], ['CSV', C.blue]].map(([t, color], i) => {
    const at = [0.3, 0.52, 0.74][i];
    const startF = Math.round(at * (frame / Math.max(progress, 1e-6)));
    const sp = progress >= at ? spring({frame: frame - startF, fps: FPS, config: {damping: 11, stiffness: 200}}) : 0;
    return <div key={t} className="card" style={{opacity: Math.min(1, sp * 1.5), transform: `translateY(${(1 - sp) * 50}px) scale(${0.8 + sp * 0.2})`}}><div className="cardBand" style={{background: color}} />{t}</div>;
  })}</div>;
};

const Fit: React.FC<SceneProps> = ({voFrom, voFrames, caption}) => {
  const frame = useCurrentFrame();
  const lines = caption.split('·').map((x) => x.trim()).filter(Boolean);
  const [eyebrow, main] = lines[0].includes(':') ? lines[0].split(/:\s*/, 2) : ['', lines[0]];
  lines[0] = main;
  const starts = chunkStarts(lines, voFrames, voFrom);
  const eb = spring({frame: frame - starts[0] + 4, fps: FPS, config: {damping: 16, stiffness: 160}});
  return <AbsoluteFill className="lightBg center"><div className="lightGrid" /><div className="fit">
    {eyebrow && <div className="fitEyebrow" style={{opacity: Math.min(1, eb * 1.5), transform: `translateY(${(1 - eb) * 30}px)`}}>{eyebrow}</div>}
    {lines.map((l, i) => {
      const sp = spring({frame: frame - starts[i], fps: FPS, config: {damping: 16, stiffness: 160}});
      return <div key={l} className={i === 0 ? 'fitMain' : 'fitSub'} style={{opacity: Math.min(1, sp * 1.5), transform: `translateY(${(1 - sp) * 40}px)`}}>{i > 0 && <span className="dot" />}{plain(l)}</div>;
    })}</div></AbsoluteFill>;
};

const Payoff: React.FC<SceneProps> = ({voFrom, voFrames, caption}) => {
  const frame = useCurrentFrame();
  const lines = caption.split('/').map((x) => x.trim()).filter(Boolean);
  const starts = chunkStarts(lines, voFrames, voFrom);
  return <AbsoluteFill className="center"><div className="triad">{lines.map((l, i) => {
    const sp = spring({frame: frame - starts[i], fps: FPS, config: {damping: 14, stiffness: 170}});
    const next = starts[i + 1];
    const dim = next !== undefined ? ease(frame, [next, next + 10]) : 0;
    return <div key={l} className={dim < 0.5 ? 'hl' : undefined} style={{opacity: Math.min(1, sp * 1.5) * (1 - dim * 0.6), transform: `translateY(${(1 - sp) * 40}px) scale(${1 - dim * 0.06})`, filter: `blur(${Math.max(0, 1 - sp) * 10}px)`}}>{plain(l)}</div>;
  })}</div></AbsoluteFill>;
};

const EndCard: React.FC<SceneProps & {cta: string}> = ({caption, lang, cta, voFrom, voFrames, frames, scene}) => {
  const frame = useCurrentFrame();
  const [tagline, action] = caption.split('·').map((x) => x.trim());
  const url = cta.trim() && !cta.includes('{') ? cta.trim() : '';
  const land = cueFrame(scene, 'hit', frames, 8);
  const {sp, bloom} = brandCard(frame, land);
  const actAt = voFrom + Math.round(voFrames * 0.5);
  const btn = spring({frame: frame - actAt, fps: FPS, config: {damping: 11, stiffness: 190}});
  return <AbsoluteFill className="center">
    <div className="bloom" style={{opacity: bloom, transform: `scale(${0.6 + bloom * 0.5})`}} />
    <div className="endStack">
      <div style={{opacity: Math.min(1, sp * 1.5), transform: `scale(${0.85 + sp * 0.15})`, filter: `blur(${Math.max(0, 1 - sp) * 12}px)`}}><Logo className="small" sweep={ease(frame, [land + 4, land + 34])} /></div>
      <Words text={tagline || ''} start={voFrom - 2} span={Math.round(voFrames * 0.45)} className="tagline" />
      <div className="button" style={{opacity: Math.min(1, btn * 1.5), transform: `scale(${0.7 + btn * 0.3})`}}>{plain(action || (lang === 'pt' ? 'Pedir demonstração' : 'Book a demo'))}{url ? ` · ${url}` : ''}</div>
    </div>
  </AbsoluteFill>;
};

const ModelScene: React.FC<SceneProps & {model: ModelDoc}> = ({model, frames, caption, voFrom, voFrames}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill className="lightBg">
    <div className="lightGrid" />
    <AbsoluteFill style={{transform: 'translateX(110px)'}}><ThreeCanvas width={W} height={H} camera={{fov: 36, position: [9, 6.5, 11.5], near: 0.1, far: 1000}}><ModelRig model={model} frame={frame} frames={frames} /></ThreeCanvas></AbsoluteFill>
    <div className="modelText">
      <Chip n={0} label="Tekla Structures" accent={C.blueDeep} at={4} light />
      <Words text={caption} start={voFrom} span={voFrames} className="headline dark" />
    </div>
  </AbsoluteFill>;
};
const ModelRig: React.FC<{model: ModelDoc; frame: number; frames: number}> = ({model, frame, frames}) => {
  const members = model.members || [];
  const points = members.flatMap((m) => [m.start, m.end]);
  const min = [0, 1, 2].map((i) => Math.min(...points.map((p) => p[i])));
  const max = [0, 1, 2].map((i) => Math.max(...points.map((p) => p[i])));
  const center = new THREE.Vector3((min[0] + max[0]) / 2, (min[2] + max[2]) / 2, -(min[1] + max[1]) / 2);
  const scale = 6.2 / Math.max(1, max[0] - min[0], max[1] - min[1], max[2] - min[2]);
  const sweep = interpolate(frame, [8, frames - 8], [0, members.length * 1.1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: brandEase});
  return <><ambientLight intensity={0.85} /><directionalLight position={[5, 10, 8]} intensity={1.4} /><group position={[2.2, 0, 0]} rotation={[0.2, interpolate(frame, [0, frames], [-0.5, 0.45], {extrapolateRight: 'clamp'}), 0]}>{members.map((m, i) => <MemberBox key={m.id || i} member={m} center={center} scale={scale} active={i < sweep} />)}</group></>;
};
const MemberBox: React.FC<{member: Member; center: THREE.Vector3; scale: number; active: boolean}> = ({member, center, scale, active}) => {
  const a = new THREE.Vector3(member.start[0], member.start[2], -member.start[1]).sub(center).multiplyScalar(scale);
  const b = new THREE.Vector3(member.end[0], member.end[2], -member.end[1]).sub(center).multiplyScalar(scale);
  const mid = a.clone().add(b).multiplyScalar(0.5);
  const dir = b.clone().sub(a);
  const len = Math.max(dir.length(), 0.04);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir.normalize());
  const thick = member.type === 'column' ? 0.08 : 0.055;
  return <mesh position={mid} quaternion={q}><boxGeometry args={[len, thick, thick]} /><meshStandardMaterial color={active ? C.blue : '#b6bfcc'} emissive={active ? '#1d4ed8' : '#000000'} emissiveIntensity={active ? 0.25 : 0} roughness={0.5} metalness={0.25} /></mesh>;
};

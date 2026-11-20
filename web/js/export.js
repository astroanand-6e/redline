/* Encode a reading plan to MP4 in the browser: WebCodecs H.264 + mp4-muxer (MIT, vendored; its
   author has since moved on to Mediabunny, but the muxer is complete and tiny).
   One encoded frame per word, carrying that word's exact duration on the 30 fps grid, so a
   12-minute paper is ~5k frames to encode rather than ~22k. */
import { ArrayBufferTarget, Muxer } from '../vendor/mp4-muxer/mp4-muxer.mjs';
import { FrameRenderer } from './render.js';

// H.264 High, Main and Constrained Baseline at level 4.0 (enough for 1080x1920 at 30 fps).
const CODECS = Object.freeze(['avc1.640028', 'avc1.4d0028', 'avc1.42e028']);
const QUANTIZER = 24; // constant-quality mode, where supported; text on flat colour stays crisp
const BITS_PER_PIXEL = 0.4; // per second, for the bitrate fallback (~370 kbps at 720p)
const KEYFRAME_SECONDS = 2; // seek points for players and editors
const MAX_QUEUE = 8; // encoder backpressure
const PROGRESS_EVERY = 25; // words between progress reports (and yields to the page)
// mp4-muxer gives the final sample the same duration as the gap before it (its stts table never
// reads the last chunk's own duration). Sending the last two words one frame at a time makes that
// gap exactly one frame, so the video ends on the planned frame.
const TAIL_WORDS = 2;

const microseconds = (frame, fps) => Math.round((frame * 1e6) / fps);
const nextTask = () => new Promise((resolve) => { setTimeout(resolve, 0); });

function configsFor(width, height, fps) {
  const base = { width, height, framerate: fps, avc: { format: 'avc' } };
  return CODECS.flatMap((codec) => [
    { ...base, codec, bitrateMode: 'quantizer' },
    { ...base, codec, bitrateMode: 'variable', bitrate: Math.round(width * height * BITS_PER_PIXEL) },
  ]);
}

/** The first encoder config this browser supports for the size, or null. */
export async function pickEncoderConfig(width, height, fps) {
  if (typeof VideoEncoder === 'undefined') return null;
  for (const config of configsFor(width, height, fps)) {
    try {
      if ((await VideoEncoder.isConfigSupported(config)).supported) return config;
    } catch {
      // An unknown option throws in some browsers; try the next config.
    }
  }
  return null;
}

function makeCanvas(width, height) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(width, height);
  return Object.assign(document.createElement('canvas'), { width, height });
}

/** Wait for the encoder queue to shrink; give up early on cancel or a closed (failed) encoder. */
async function drain(encoder, signal) {
  while (encoder.encodeQueueSize > MAX_QUEUE && encoder.state === 'configured' && !signal?.aborted) {
    await new Promise((resolve) => {
      const done = () => {
        clearTimeout(timer);
        encoder.removeEventListener('dequeue', done);
        resolve();
      };
      const timer = setTimeout(done, 20); // browsers without the dequeue event
      encoder.addEventListener('dequeue', done);
    });
  }
}

/**
 * Render `plan` with `layout`/`style` and return an MP4 Blob.
 * onProgress(fraction) reports progress; `signal` (AbortSignal) cancels.
 */
export async function exportMp4(plan, { layout, style, showWpm, onProgress, signal }) {
  const { width, height } = layout;
  const config = await pickEncoderConfig(width, height, plan.fps);
  if (!config) throw new Error('This browser cannot encode H.264 video.');

  const muxer = new Muxer({
    target: new ArrayBufferTarget(),
    video: { codec: 'avc', width, height, frameRate: plan.fps },
    fastStart: 'in-memory',
    firstTimestampBehavior: 'offset',
  });
  let failure = null;
  const encoder = new VideoEncoder({
    output: (chunk, meta) => muxer.addVideoChunk(chunk, meta),
    error: (error) => { failure = error; },
  });
  encoder.configure(config);
  const perFrame = config.bitrateMode === 'quantizer' ? { avc: { quantizer: QUANTIZER } } : {};

  const canvas = makeCanvas(width, height);
  const renderer = new FrameRenderer(canvas.getContext('2d', { alpha: false }), layout, style);
  let lastKeyFrame = -Infinity;
  const encodeCanvas = (start, frames) => {
    const timestamp = microseconds(start, plan.fps);
    const frame = new VideoFrame(canvas, { timestamp, duration: microseconds(start + frames, plan.fps) - timestamp });
    const keyFrame = start - lastKeyFrame >= plan.fps * KEYFRAME_SECONDS;
    if (keyFrame) lastKeyFrame = start;
    try {
      encoder.encode(frame, { ...perFrame, keyFrame });
    } finally {
      frame.close();
    }
  };
  const tailFrom = plan.tokens.length - TAIL_WORDS;
  try {
    for (let i = 0; i < plan.tokens.length; i += 1) {
      if (signal?.aborted) throw new DOMException('Export cancelled.', 'AbortError');
      if (failure) throw failure;
      renderer.render(plan.tokens[i].text, showWpm ? `${plan.wpms[i]} wpm` : null);
      if (i < tailFrom) encodeCanvas(plan.starts[i], plan.counts[i]);
      else for (let f = 0; f < plan.counts[i]; f += 1) encodeCanvas(plan.starts[i] + f, 1);
      await drain(encoder, signal);
      if (i % PROGRESS_EVERY === 0) {
        onProgress?.(i / plan.tokens.length);
        await nextTask();
      }
    }
    await encoder.flush();
    if (failure) throw failure;
    muxer.finalize();
  } catch (error) {
    throw error?.name === 'AbortError' ? error : (failure ?? error); // keep the encoder's root cause
  } finally {
    if (encoder.state !== 'closed') encoder.close();
  }
  onProgress?.(1);
  return new Blob([muxer.target.buffer], { type: 'video/mp4' });
}

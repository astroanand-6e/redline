/* Live RSVP playback on the page's canvas. Timing comes from the same frame plan as the MP4, and the
   clock is wall time (not frame ticks), so a slow device drops words' frames, never their timing. */
import { indexAtFrame } from './engine/plan.js';
import { FrameRenderer } from './render.js';

export class Player {
  constructor(canvas, onChange) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.onChange = onChange;
    this.plan = null;
    this.renderer = null;
    this.showWpm = true;
    this.index = 0;
    this.isPlaying = false;
    this.hasEnded = false;
    this.raf = 0;
    this.originMs = 0;
    this.tick = this.tick.bind(this);
  }

  get count() {
    return this.plan ? this.plan.tokens.length : 0;
  }

  setView(layout, style, showWpm) {
    this.canvas.width = layout.width;
    this.canvas.height = layout.height;
    this.renderer = new FrameRenderer(this.ctx, layout, style);
    this.showWpm = showWpm;
    this.draw();
  }

  /** Swap in a new plan; keep the word position when only the speed changed. */
  load(plan, { keepPosition = false } = {}) {
    const resume = keepPosition && this.isPlaying;
    this.stopLoop();
    this.plan = plan;
    this.index = keepPosition ? Math.min(this.index, Math.max(0, this.count - 1)) : 0;
    this.isPlaying = false;
    this.hasEnded = false;
    if (resume) this.play();
    else {
      this.draw();
      this.notify();
    }
  }

  play() {
    if (!this.count) return;
    if (this.hasEnded) this.index = 0;
    this.hasEnded = false;
    this.isPlaying = true;
    this.syncClock();
    this.stopLoop();
    this.raf = requestAnimationFrame(this.tick);
    this.draw();
    this.notify();
  }

  pause() {
    this.stopLoop();
    this.isPlaying = false;
    this.notify();
  }

  toggle() {
    if (this.isPlaying) this.pause();
    else this.play();
  }

  seek(index) {
    if (!this.count) return;
    this.index = Math.min(Math.max(0, Math.round(index)), this.count - 1);
    this.hasEnded = false;
    if (this.isPlaying) this.syncClock();
    this.draw();
    this.notify();
  }

  syncClock() {
    this.originMs = performance.now() - (this.plan.starts[this.index] * 1000) / this.plan.fps;
  }

  stopLoop() {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  tick(now) {
    const { plan } = this;
    const frame = Math.floor(((now - this.originMs) * plan.fps) / 1000);
    if (frame >= plan.totalFrames) {
      this.index = this.count - 1;
      this.hasEnded = true;
      this.draw();
      this.pause();
      return;
    }
    const index = indexAtFrame(plan.starts, frame);
    if (index !== this.index) {
      this.index = index;
      this.draw();
      this.notify();
    }
    this.raf = requestAnimationFrame(this.tick);
  }

  draw() {
    if (!this.renderer) return;
    const token = this.plan?.tokens[this.index];
    const label = token && this.showWpm ? `${this.plan.wpms[this.index]} wpm` : null;
    this.renderer.render(token ? token.text : '', label);
  }

  notify() {
    const { plan, index } = this;
    this.onChange?.({
      index,
      count: this.count,
      isPlaying: this.isPlaying,
      seconds: plan && this.count ? plan.starts[index] / plan.fps : 0,
      totalSeconds: plan ? plan.seconds : 0,
    });
  }
}

/* Redline in the browser: wires the page to the engine, the live player, the PDF reader and the
   MP4 exporter. Nothing leaves the visitor's machine. */
import { cleanPages } from './engine/clean.js';
import { FPS, formatClock, formatDuration, planFromTokens } from './engine/plan.js';
import { THEMES, layoutFor } from './engine/style.js';
import { tokenize } from './engine/tokens.js';
import { exportMp4, pickEncoderConfig } from './export.js';
import { ExtractionError, extractPages } from './pdftext.js';
import { Player } from './player.js';
import { loadFonts } from './render.js';

const MAX_PDF_BYTES = 50 * 1024 * 1024;
const MAX_TEXT_CHARS = 300_000; // same as the textarea's maxlength, which only limits typing
const ANNOUNCE_STEP = 10; // export progress is announced in 10% steps
const MAX_EXPORT_SECONDS = 60 * 60;
const TEXT_DEBOUNCE_MS = 250;
const SEEK_STEP = 10;
const SAMPLES = Object.freeze({
  attention: Object.freeze({ url: 'samples/attention-abstract.txt', name: 'attention-abstract' }),
  gettysburg: Object.freeze({ url: 'samples/gettysburg.pdf', name: 'gettysburg' }),
});
const TYPING_TARGETS = new Set(['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A', 'SUMMARY', 'VIDEO']);

const $ = (id) => document.getElementById(id);
const ui = Object.freeze({
  canvas: $('screen'), stage: $('stage'), play: $('play'), restart: $('restart'), scrub: $('scrub'),
  clock: $('clock'), file: $('file'), drop: $('drop'), fileName: $('file-name'),
  first: $('first-page'), last: $('last-page'), skipRefs: $('skip-refs'), stripCites: $('strip-cites'),
  reextract: $('reextract'), text: $('text'), stats: $('stats'), sourceStatus: $('source-status'),
  start: $('start-wpm'), end: $('end-wpm'), startOut: $('start-out'), endOut: $('end-out'),
  showWpm: $('show-wpm'), exportBtn: $('export'), cancel: $('cancel'), progress: $('progress'),
  exportStatus: $('export-status'), result: $('result'), save: $('save'),
});

let source = Object.freeze({ file: null, name: 'redline' });
let plan = planFromTokens([], { startWpm: 300, endWpm: 300 });
let tokenCache = Object.freeze({ text: '', tokens: [] });
let loadToken = 0; // bumped by every PDF read or sample load; only the latest may apply its text
let exportJob = null;
let resultUrl = null;
let canEncode = false;
let textTimer = 0;

const player = new Player(ui.canvas, renderTransport);

function settings() {
  return Object.freeze({
    startWpm: Number(ui.start.value),
    endWpm: Number(ui.end.value),
    format: document.querySelector('input[name="format"]:checked').value,
    theme: document.querySelector('input[name="theme"]:checked').value,
    showWpm: ui.showWpm.checked,
  });
}

function setStatus(el, message, kind = '') {
  el.textContent = message;
  el.dataset.kind = kind;
}

function renderTransport({ index, count, isPlaying, seconds, totalSeconds }) {
  ui.play.classList.toggle('is-playing', isPlaying);
  ui.play.setAttribute('aria-label', isPlaying ? 'Pause' : 'Play');
  ui.scrub.max = String(Math.max(0, count - 1));
  ui.scrub.value = String(index);
  ui.scrub.disabled = !count;
  ui.clock.textContent = `${formatClock(seconds)} / ${formatClock(totalSeconds)}`;
}

function describe(current, s) {
  if (!current.tokens.length) return 'Drop a PDF or paste text to begin.';
  const speed = s.startWpm === s.endWpm ? `${s.startWpm} wpm` : `${s.startWpm}→${s.endWpm} wpm`;
  const words = current.tokens.length.toLocaleString('en-US');
  const note = current.seconds > MAX_EXPORT_SECONDS ? ' · over the 60-minute video limit; raise the speed' : '';
  return `${words} words · about ${formatDuration(current.seconds)} at ${speed}${note}`;
}

function tokensFor(text) {
  if (tokenCache.text !== text) tokenCache = Object.freeze({ text, tokens: tokenize(text) });
  return tokenCache.tokens;
}

function updateExportButton() {
  ui.exportBtn.disabled = !canEncode || Boolean(exportJob) || !plan.tokens.length;
}

function replan({ keepPosition }) {
  const s = settings();
  ui.startOut.textContent = `${s.startWpm} wpm`;
  ui.endOut.textContent = `${s.endWpm} wpm`;
  plan = planFromTokens(tokensFor(ui.text.value), { startWpm: s.startWpm, endWpm: s.endWpm, fps: FPS });
  player.load(plan, { keepPosition });
  ui.stats.textContent = describe(plan, s);
  updateExportButton();
}

function applyView() {
  const s = settings();
  ui.stage.dataset.format = s.format;
  ui.stage.dataset.theme = s.theme;
  player.setView(layoutFor(s.format), THEMES[s.theme], s.showWpm);
}

function setText(text) {
  ui.text.value = text;
  replan({ keepPosition: false });
}

const pageNumber = (input, fallback) => {
  const n = Number.parseInt(input.value, 10);
  return Number.isInteger(n) && n > 0 ? n : fallback;
};

const safeName = (fileName) => fileName.replace(/\.pdf$/i, '').toLowerCase()
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'redline';

async function readPdf() {
  const { file } = source;
  if (!file) return;
  const token = ++loadToken;
  const isCurrent = () => token === loadToken;
  ui.reextract.disabled = true;
  setStatus(ui.sourceStatus, 'Reading the PDF…');
  try {
    const { pages, total } = await extractPages(new Uint8Array(await file.arrayBuffer()), {
      first: pageNumber(ui.first, 1),
      last: pageNumber(ui.last, 0),
      onProgress: (n, of) => { if (isCurrent()) setStatus(ui.sourceStatus, `Reading page ${n} of ${of}…`); },
    });
    if (!isCurrent()) return;
    const text = cleanPages(pages, { skipReferences: ui.skipRefs.checked, removeCitations: ui.stripCites.checked });
    if (!text) throw new ExtractionError('No selectable text found. This PDF may be a scan; run OCR on it first.');
    if (text.length > MAX_TEXT_CHARS) {
      throw new ExtractionError(`That's ${text.length.toLocaleString('en-US')} characters of text; the limit is ${MAX_TEXT_CHARS.toLocaleString('en-US')}. Pick a smaller page range.`);
    }
    setText(text);
    const span = pages.length === total ? `${total} page${total === 1 ? '' : 's'}` : `${pages.length} of ${total} pages`;
    setStatus(ui.sourceStatus, `Read ${span} of ${file.name}.`, 'ok');
  } catch (error) {
    if (!isCurrent()) return;
    if (!(error instanceof ExtractionError)) console.error(error);
    setStatus(ui.sourceStatus, error instanceof ExtractionError ? error.message : 'Could not read this PDF.', 'error');
  } finally {
    if (isCurrent()) ui.reextract.disabled = false;
  }
}

function takeFile(file) {
  if (!file) return;
  if (file.type !== 'application/pdf' && !/\.pdf$/i.test(file.name)) {
    setStatus(ui.sourceStatus, 'Please choose a PDF file.', 'error');
    return;
  }
  if (file.size > MAX_PDF_BYTES) {
    setStatus(ui.sourceStatus, 'That PDF is over 50 MB. Try a smaller file or split it.', 'error');
    return;
  }
  source = Object.freeze({ file, name: safeName(file.name) });
  ui.fileName.textContent = file.name;
  readPdf();
}

async function loadSample(key) {
  const sample = SAMPLES[key];
  const token = ++loadToken;
  const response = await fetch(sample.url);
  if (!response.ok) throw new Error(`sample ${key}: HTTP ${response.status}`);
  const body = sample.url.endsWith('.pdf') ? await response.blob() : await response.text();
  if (token !== loadToken) return; // the visitor picked something else meanwhile
  if (body instanceof Blob) {
    takeFile(new File([body], `${sample.name}.pdf`, { type: 'application/pdf' }));
    return;
  }
  source = Object.freeze({ file: null, name: sample.name });
  ui.fileName.textContent = '';
  setText(body);
  setStatus(ui.sourceStatus, 'Sample: the abstract of Attention Is All You Need (Vaswani et al., 2017).', 'ok');
}

const formatBytes = (n) => (n < 1e6 ? `${Math.max(1, Math.round(n / 1e3))} KB` : `${(n / 1e6).toFixed(1)} MB`);

function showResult(blob, fileName, ms) {
  if (resultUrl) URL.revokeObjectURL(resultUrl);
  resultUrl = URL.createObjectURL(blob);
  ui.result.src = resultUrl;
  ui.result.hidden = false;
  ui.save.href = resultUrl;
  ui.save.download = fileName;
  ui.save.textContent = `Save ${fileName} (${formatBytes(blob.size)})`;
  ui.save.hidden = false;
  setStatus(ui.exportStatus, `Encoded in ${(ms / 1000).toFixed(1)} s.`, 'ok');
  ui.save.click();
}

async function runExport() {
  if (plan.seconds > MAX_EXPORT_SECONDS) {
    setStatus(ui.exportStatus, `That would be a ${Math.round(plan.seconds / 60)}-minute video; the limit is 60 minutes. Raise the speed or trim the text.`, 'error');
    return;
  }
  const s = settings();
  const job = new AbortController();
  exportJob = job;
  updateExportButton();
  ui.cancel.hidden = false;
  ui.progress.hidden = false;
  ui.progress.value = 0;
  const startedAt = performance.now();
  let announced = -1;
  try {
    const blob = await exportMp4(plan, {
      layout: layoutFor(s.format),
      style: THEMES[s.theme],
      showWpm: s.showWpm,
      signal: job.signal,
      onProgress: (fraction) => {
        ui.progress.value = fraction;
        const step = Math.floor((fraction * 100) / ANNOUNCE_STEP) * ANNOUNCE_STEP;
        if (step !== announced) {
          announced = step;
          setStatus(ui.exportStatus, `Encoding… ${step}%`);
        }
      },
    });
    showResult(blob, `${source.name}-redline-${s.format.replace(':', 'x')}.mp4`, performance.now() - startedAt);
  } catch (error) {
    if (error.name === 'AbortError') setStatus(ui.exportStatus, 'Cancelled.');
    else {
      console.error(error);
      setStatus(ui.exportStatus, 'Video encoding failed. Try a shorter text, another format or another browser.', 'error');
    }
  } finally {
    exportJob = null;
    ui.cancel.hidden = true;
    ui.progress.hidden = true;
    updateExportButton();
  }
}

function onKey(event) {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
  if (TYPING_TARGETS.has(event.target.tagName) || event.target.isContentEditable) return;
  if (event.key === ' ') player.toggle();
  else if (event.key === 'ArrowLeft') player.seek(player.index - SEEK_STEP);
  else if (event.key === 'ArrowRight') player.seek(player.index + SEEK_STEP);
  else return;
  event.preventDefault();
}

function bindDrop() {
  const setOver = (isOver) => ui.drop.classList.toggle('is-over', isOver);
  ui.drop.addEventListener('dragover', (event) => { event.preventDefault(); setOver(true); });
  ui.drop.addEventListener('dragleave', () => setOver(false));
  ui.drop.addEventListener('drop', (event) => {
    event.preventDefault();
    setOver(false);
    takeFile(event.dataTransfer.files[0]);
  });
  ui.file.addEventListener('change', () => takeFile(ui.file.files[0]));
}

function bindEvents() {
  bindDrop();
  ui.play.addEventListener('click', () => player.toggle());
  ui.restart.addEventListener('click', () => player.seek(0));
  ui.scrub.addEventListener('input', () => player.seek(Number(ui.scrub.value)));
  ui.reextract.addEventListener('click', readPdf);
  ui.text.addEventListener('input', () => {
    clearTimeout(textTimer);
    textTimer = setTimeout(() => replan({ keepPosition: false }), TEXT_DEBOUNCE_MS);
  });
  for (const slider of [ui.start, ui.end]) slider.addEventListener('input', () => replan({ keepPosition: true }));
  document.querySelectorAll('input[name="format"], input[name="theme"]')
    .forEach((input) => input.addEventListener('change', applyView));
  ui.showWpm.addEventListener('change', applyView);
  document.querySelectorAll('[data-sample]').forEach((button) => button.addEventListener('click', () => {
    loadSample(button.dataset.sample).catch((error) => {
      console.error(error);
      setStatus(ui.sourceStatus, 'Could not load the sample.', 'error');
    });
  }));
  ui.exportBtn.addEventListener('click', runExport);
  ui.cancel.addEventListener('click', () => exportJob?.abort());
  document.addEventListener('keydown', onKey);
  document.addEventListener('visibilitychange', () => { if (document.hidden) player.pause(); });
}

async function init() {
  bindEvents();
  try {
    await loadFonts();
  } catch (error) {
    console.warn('Redline: the video font did not load; using a fallback serif.', error);
  }
  applyView();
  replan({ keepPosition: false });
  canEncode = Boolean(await pickEncoderConfig(1280, 720, FPS));
  if (!canEncode) {
    setStatus(ui.exportStatus, 'This browser cannot encode video (it needs WebCodecs with H.264). You can still read here; Chrome, Edge or Safari can download the MP4.', 'error');
  }
  updateExportButton();
  if (loadToken || ui.text.value) return; // the visitor already dropped a PDF or typed text
  try {
    await loadSample('attention');
  } catch (error) {
    console.error(error);
  }
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) player.play();
}

init().catch((error) => {
  console.error(error);
  setStatus(ui.sourceStatus, 'Redline could not start in this browser. Try a recent Chrome, Edge, Safari or Firefox.', 'error');
});

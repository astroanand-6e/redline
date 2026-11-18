// Runs via gr.HTML(js_on_load=...): `element` is the component's root node.
const WORDS = (
  "Read any PDF one word at a time. Your eyes stay still, " +
  "and the red letter does the work. Start at 300 words per minute, " +
  "finish at 900."
).split(" ");
const WPM = 300;
const pre = element.querySelector(".rl-pre");
const pivot = element.querySelector(".rl-pivot");
const post = element.querySelector(".rl-post");
const label = element.querySelector(".rl-wpm");

function orpIndex(word) {
  const letters = [...word].flatMap((ch, i) => (/[\p{L}\p{N}]/u.test(ch) ? [i] : []));
  if (!letters.length) return Math.floor(word.length / 2);
  const n = letters.length;
  const k = n <= 1 ? 0 : n <= 5 ? 1 : n <= 9 ? 2 : n <= 13 ? 3 : 4;
  return letters[k];
}

function pauseFor(word) {
  if (/[.!?]["')\]]*$/.test(word)) return 2.2;
  if (/[,;:]["')\]]*$/.test(word)) return 1.5;
  return 1;
}

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (element._rlTimer) clearTimeout(element._rlTimer);

if (!reduceMotion && pre && pivot && post) {
  let i = 0;
  const tick = () => {
    const word = WORDS[i % WORDS.length];
    const k = orpIndex(word);
    pre.textContent = word.slice(0, k);
    pivot.textContent = word[k] || "";
    post.textContent = word.slice(k + 1);
    const wpm = Math.round(WPM + (600 * (i % WORDS.length)) / (WORDS.length - 1));
    if (label) label.textContent = `${Math.round(wpm / 30) * 30} wpm`;
    i += 1;
    const atEnd = i % WORDS.length === 0;
    element._rlTimer = setTimeout(tick, (60000 / wpm) * pauseFor(word) * (atEnd ? 6 : 1));
  };
  tick();
}

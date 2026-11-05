/**
 * Mock API client — the ONLY place mock data lives.
 * Implements the same interface as the real client in api.ts so the UI
 * works unchanged when Phase 4 flips NEXT_PUBLIC_USE_MOCK=false.
 *
 * The mock "model" is a small transparent heuristic so that obviously
 * spammy text scores as fake and balanced text scores as genuine,
 * which makes the demo feel like a real product.
 *
 * The Phase 3.5 blocks (tier1, sarcasm, explain) are simulated with the same
 * rules and the same thresholds as the backend, so mock mode shows the real
 * UI states. They stay optional: if you set MOCK_ENABLE_TIER1 /
 * MOCK_ENABLE_SARCASM to false the response omits those keys entirely, exactly
 * like a backend started with ENABLE_TIER1=false / ENABLE_SARCASM=false.
 */

import { cleanMetadata } from "./utils";
import type {
  BatchResult,
  BatchRow,
  BatchSummary,
  DecisionSource,
  ExplainMethod,
  ExplainRequest,
  ExplainResponse,
  HealthResponse,
  HistoryEntry,
  HistoryListResponse,
  MetricsResponse,
  ModelInfo,
  ModelMetrics,
  PredictMetadata,
  PredictRequest,
  PredictionResult,
  RedFlag,
  ResponseModelUsed,
  SarcasmBlock,
  Sentiment,
  Severity,
  Tier1Block,
  Tier1Rule,
  TokenScore,
} from "./types";
import { ApiRequestError } from "./types";

const latency = (ms: number) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();

/** Mock mirrors of the backend feature switches. */
export const MOCK_ENABLE_TIER1 = true;
export const MOCK_ENABLE_SARCASM = true;
const MOCK_SARCASM_THRESHOLD = 0.6;
const MOCK_MAX_REVIEWS_PER_MINUTE = 5;
const MOCK_DUPLICATE_THRESHOLD = 3;
const MOCK_MIN_WORDS = 4;

/* ------------------------------------------------------------------ */
/* Deterministic pseudo-random (so demos are stable)                   */
/* ------------------------------------------------------------------ */

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function seededNoise(s: string, salt: number): number {
  return (hashString(`${s}#${salt}`) % 1000) / 1000; // 0..1
}

/* ------------------------------------------------------------------ */
/* Mock heuristics                                                     */
/* ------------------------------------------------------------------ */

const SPAMMY_WORDS = [
  "amazing", "incredible", "best", "fantastic", "perfect", "awesome",
  "wonderful", "life-changing", "must-buy", "greatest", "love", "loved",
  "highly recommend", "five stars", "5 stars",
];
const POSITIVE_LEXICON = ["good", "great", "love", "loved", "excellent", "amazing", "best", "perfect", "happy", "recommend", "awesome", "fantastic", "works", "nice", "quality"];
const NEGATIVE_LEXICON = ["bad", "worst", "terrible", "awful", "broken", "broke", "hate", "hated", "poor", "disappointed", "refund", "useless", "waste", "garbage", "junk", "trash", "scam", "cheap", "failed", "regret", "returned"];

const STOPWORDS = new Set([
  "the", "a", "an", "and", "or", "but", "i", "it", "this", "that", "is", "was",
  "are", "were", "to", "of", "in", "for", "on", "with", "my", "me", "so", "very",
  "really", "just", "have", "has", "had", "you", "your", "they", "them", "its",
  "at", "as", "be", "by", "from", "not", "no", "do", "does", "did", "would",
]);

function analyzeSentiment(text: string): Sentiment {
  const words = text.toLowerCase().match(/[a-z']+/g) ?? [];
  let pos = 0;
  let neg = 0;
  for (const w of words) {
    if (POSITIVE_LEXICON.includes(w)) pos++;
    if (NEGATIVE_LEXICON.includes(w)) neg++;
  }
  const total = words.length || 1;
  const posScore = Math.min(pos / Math.max(total / 12, 1), 1);
  const negScore = Math.min(neg / Math.max(total / 12, 1), 1);
  const compound = Math.max(-1, Math.min(1, (posScore - negScore) * 1.4));
  const neu = Math.max(0, 1 - posScore - negScore);
  const label =
    compound > 0.15 ? "Positive" : compound < -0.15 ? "Negative" : "Mixed";
  return {
    compound: Number(compound.toFixed(3)),
    label,
    pos: Number(posScore.toFixed(3)),
    neu: Number(neu.toFixed(3)),
    neg: Number(negScore.toFixed(3)),
  };
}

function buildFlags(text: string, words: string[], capsWords: number, exclamations: number): RedFlag[] {
  const flags: RedFlag[] = [];
  const lower = text.toLowerCase();
  if (capsWords >= 3)
    flags.push({ code: "ALL_CAPS", label: `${capsWords} words in ALL CAPS`, severity: capsWords >= 6 ? "high" : "medium" });
  if (exclamations >= 3)
    flags.push({ code: "EXCESS_EXCLAIM", label: `${exclamations} exclamation marks`, severity: exclamations >= 6 ? "high" : "medium" });
  const spamHits = SPAMMY_WORDS.filter((w) => lower.includes(w)).length;
  if (spamHits >= 3)
    flags.push({ code: "HYPE_DENSITY", label: "Unusually high hype-word density", severity: spamHits >= 5 ? "high" : "medium" });
  if (lower.includes("http://") || lower.includes("https://") || lower.includes("www."))
    flags.push({ code: "URL_PRESENT", label: "Contains a URL", severity: "high" });
  if (words.length < 8 && words.length > 0)
    flags.push({ code: "TOO_SHORT", label: "Review is very short", severity: "low" });
  if (/(.)\1{3,}/.test(lower.replace(/\s/g, "")))
    flags.push({ code: "REPEATED_CHARS", label: "Repeated character runs", severity: "low" });
  return flags;
}

function buildTokens(text: string, fakeLean: number): TokenScore[] {
  const words = text.toLowerCase().match(/[a-z']+/g) ?? [];
  const freq = new Map<string, number>();
  for (const w of words) {
    if (STOPWORDS.has(w) || w.length < 3) continue;
    freq.set(w, (freq.get(w) ?? 0) + 1);
  }
  const scores: TokenScore[] = Array.from(freq.entries()).map(([token, count]) => {
    const isSpammy = SPAMMY_WORDS.some((s) => token.includes(s));
    const isNegative = NEGATIVE_LEXICON.includes(token);
    // Fake-leaning tokens get positive scores, genuine-leaning negative.
    let score = (seededNoise(token, 7) - 0.5) * 0.8;
    if (isSpammy) score += 1.1 + fakeLean;
    if (isNegative) score -= 0.9;
    score += (count - 1) * 0.15;
    return { token, score: Number(score.toFixed(2)), direction: score >= 0 ? "fake" : "genuine" };
  });
  return scores.sort((a, b) => Math.abs(b.score) - Math.abs(a.score)).slice(0, 8);
}

/* ------------------------------------------------------------------ */
/* Phase 3.5 — Tier-1 rules (mirror of backend/app/services/tier1.py)   */
/* ------------------------------------------------------------------ */

const RULE_LABELS: Record<string, string> = {
  VELOCITY_EXCEEDED: "Too many reviews from this user in the last minute",
  DUPLICATE_FLOOD: "The same review text submitted repeatedly",
  VERY_SHORT: "Very short text",
  LINK_OR_CONTACT_SPAM: "Contains a link, e-mail address or phone number",
  REPEATED_CHARACTERS: "Letters stretched out (for example 'goooood')",
};
const RULE_SEVERITY: Record<string, Severity> = {
  VELOCITY_EXCEEDED: "high",
  DUPLICATE_FLOOD: "high",
  VERY_SHORT: "low",
  LINK_OR_CONTACT_SPAM: "medium",
  REPEATED_CHARACTERS: "low",
};

const URL_RE = /(?:https?:\/\/|www\.)\S+|\b[\w-]+\.(?:com|net|org|in|shop|store|co\.uk)\b/i;
const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
const PHONE_RE = /[+(]?[\d][\d\s().-]{6,}\d/;
const REPEAT_RE = /([A-Za-z\u0900-\u097F])\1{3,}/;

const normaliseText = (text: string) =>
  text.trim().toLowerCase().replace(/\s+/g, " ");

/**
 * Characters we keep when trimming punctuation off a token. Plain character
 * classes rather than unicode property escapes, so the file compiles at any
 * ES target: Latin (incl. accented), Devanagari, digits and apostrophes.
 */
const TOKEN_TRIM = /^[^0-9A-Za-z\u00C0-\u024F\u0900-\u097F']+|[^0-9A-Za-z\u00C0-\u024F\u0900-\u097F']+$/g;

/** Whitespace tokens with punctuation trimmed — Devanagari stays intact. */
function cueTokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/\s+/)
    .map((w) => w.replace(TOKEN_TRIM, ""))
    .filter(Boolean);
}

/** Sliding windows, in memory — the same "per process, resets on reload" caveat. */
const userWindow = new Map<string, number[]>();
const textWindow = new Map<string, number[]>();

function windowCount(store: Map<string, number[]>, key: string, moment: number, windowMs: number) {
  const hits = (store.get(key) ?? []).filter((t) => Math.abs(moment - t) <= windowMs);
  hits.push(moment);
  store.set(key, hits);
  return hits.length;
}

function softRules(text: string, wordCount: number): Tier1Rule[] {
  const found: Tier1Rule[] = [];
  const add = (code: string) =>
    found.push({ code, label: RULE_LABELS[code], severity: RULE_SEVERITY[code], kind: "soft" });
  if (wordCount < MOCK_MIN_WORDS) add("VERY_SHORT");
  if (URL_RE.test(text) || EMAIL_RE.test(text) || PHONE_RE.test(text)) add("LINK_OR_CONTACT_SPAM");
  if (REPEAT_RE.test(text)) add("REPEATED_CHARACTERS");
  return found;
}

const hardRule = (code: string): Tier1Rule => ({
  code,
  label: RULE_LABELS[code],
  severity: RULE_SEVERITY[code],
  kind: "hard",
});

/**
 * Evaluate the Tier-1 rules for one mock prediction. Side effect: records the
 * submission in the in-memory windows, exactly like the real tracker does, so
 * submitting the same review three times floods on the third.
 */
function mockTier1(
  text: string,
  metadata: PredictMetadata | undefined,
  wordCount: number
): Tier1Block {
  const parsed = metadata?.posted_at ? Date.parse(metadata.posted_at) : NaN;
  const moment = Number.isNaN(parsed) ? Date.now() : parsed;

  const rules = softRules(text, wordCount);

  let velocityCount = 0;
  if (typeof metadata?.reviews_last_minute === "number") {
    velocityCount = metadata.reviews_last_minute;
  } else if (metadata?.user_id) {
    velocityCount = windowCount(userWindow, metadata.user_id, moment, 60_000);
  }
  if (velocityCount > MOCK_MAX_REVIEWS_PER_MINUTE) rules.unshift(hardRule("VELOCITY_EXCEEDED"));

  const duplicates = windowCount(textWindow, normaliseText(text), moment, 600_000);
  if (duplicates >= MOCK_DUPLICATE_THRESHOLD) rules.unshift(hardRule("DUPLICATE_FLOOD"));

  const triggered = rules.some((r) => r.kind === "hard");
  return { triggered, action: triggered ? "flag_spam" : "pass", rules };
}

/* ------------------------------------------------------------------ */
/* Phase 3.5 — sarcasm contrast (mirror of services/sarcasm.py)        */
/* ------------------------------------------------------------------ */

const POSITIVE_CUES = [
  "wow", "great", "amazing", "awesome", "perfect", "love", "best", "thanks",
  "brilliant", "excellent", "wonderful", "fantastic",
  "बहुत पसंद आया", "बहुत बढ़िया", "बढ़िया", "bahut achha", "badhiya", "mast", "shandaar",
];
const NEGATIVE_CUES = [
  "garbage", "trash", "junk", "useless", "waste", "broke", "broken", "worst",
  "refund", "scam", "stopped working",
  "बेकार", "चिथड़े", "kachra", "bekaar", "fraud",
];

/** Whole-word (and whole-phrase) cue match on cleaned tokens. */
function matchedCues(text: string, cues: string[]): string[] {
  const tokens = cueTokens(text);
  const joined = ` ${tokens.join(" ")} `;
  return cues.filter((cue) => {
    const needle = cue.toLowerCase().trim();
    return needle.includes(" ") ? joined.includes(` ${needle} `) : tokens.includes(needle);
  });
}

function splitOpening(text: string): [string, string] {
  const end = Math.min(
    ...[text.indexOf("."), text.indexOf("!"), text.indexOf("?")]
      .filter((i) => i >= 0)
      .concat([text.length])
  );
  const first = text.slice(0, end);
  const words = first.trim().split(/\s+/).slice(0, 8);
  const opening = words.join(" ");
  return [opening, text.slice(opening.length)];
}

/** Remove cue words from one half before scoring it, so the halves stay comparable. */
function stripCues(text: string, cues: string[]): string {
  const tokens = text.split(/\s+/);
  const lower = tokens.map((t) => t.toLowerCase().replace(TOKEN_TRIM, ""));
  const drop = new Set<number>();
  for (const cue of cues) {
    const parts = cue.toLowerCase().split(/\s+/);
    for (let i = 0; i + parts.length <= lower.length; i++) {
      if (parts.every((p, k) => lower[i + k] === p)) {
        for (let k = 0; k < parts.length; k++) drop.add(i + k);
      }
    }
  }
  return tokens.filter((_, i) => !drop.has(i)).join(" ");
}

function mockSarcasm(text: string): SarcasmBlock {
  const [opening, rest] = splitOpening(text);
  const positiveCues = matchedCues(opening, POSITIVE_CUES);
  const negativeCues = matchedCues(rest, NEGATIVE_CUES);
  const keywordContrast = positiveCues.length > 0 && negativeCues.length > 0 ? 1 : 0;
  // The mock splits on punctuation, so an eight-word opening can swallow an
  // outcome word ("...total garbage, the"). Score each half without the other
  // half's cues; the backend's real VADER already separates them.
  const openScore = analyzeSentiment(stripCues(opening, NEGATIVE_CUES)).compound;
  const restScore = analyzeSentiment(stripCues(rest, POSITIVE_CUES)).compound;
  const vaderContrast = openScore >= 0.3 && restScore <= -0.3 ? 1 : 0;
  const score = Number((0.6 * keywordContrast + 0.4 * vaderContrast).toFixed(2));
  const suspected = score >= MOCK_SARCASM_THRESHOLD;
  if (!suspected) return { suspected: false, score };
  const risk_level: Severity = score >= 0.8 ? "high" : "medium";
  return {
    suspected: true,
    score,
    risk_level,
    positive_cues: positiveCues,
    negative_cues: negativeCues,
  };
}

const SARCASM_FLAG: RedFlag = {
  code: "SARCASM_SUSPECTED",
  label: "Possible sarcasm: positive opening, negative outcome",
  severity: "high",
};

/** Surface words the mock "stemmed" token came from, like the real token_map. */
function buildTokenMap(text: string, tokens: TokenScore[]): Record<string, string[]> {
  const surfaces = text
    .split(/\s+/)
    .map((word) => word.replace(TOKEN_TRIM, ""))
    .filter(Boolean);
  const map: Record<string, string[]> = {};
  for (const token of tokens) {
    const hits = surfaces.filter((surface) => surface.toLowerCase() === token.token);
    map[token.token] = hits.length ? Array.from(new Set(hits)) : [token.token];
  }
  return map;
}

function mockPredict(request: PredictRequest, id: number): PredictionResult {
  const text = request.review.trim();
  const metadata = cleanMetadata(request.metadata);
  const words = text.match(/[a-zA-Z0-9']+/g) ?? [];
  const capsWords = words.filter((w) => w.length > 1 && /^[A-Z0-9!%]+$/.test(w)).length;
  const exclamations = (text.match(/!/g) ?? []).length;
  const lower = text.toLowerCase();
  const spamHits = SPAMMY_WORDS.filter((w) => lower.includes(w)).length;

  const sentiment = analyzeSentiment(text);
  const flags = buildFlags(text, words, capsWords, exclamations);
  const meta = { words: words.length, exclamations, caps_words: capsWords };

  // 1. Sarcasm runs last in the backend and on both paths, so compute it up
  //    front: it is a risk flag only and never touches verdict or probability.
  const sarcasm = MOCK_ENABLE_SARCASM ? mockSarcasm(text) : undefined;
  const severity: Severity = sarcasm?.risk_level ?? "high";
  const allFlags =
    sarcasm?.suspected && !flags.some((f) => f.code === SARCASM_FLAG.code)
      ? [{ ...SARCASM_FLAG, severity }, ...flags]
      : flags;

  // 2. Tier-1 next: a hard rule decides the case and the model is skipped.
  const tier1 = MOCK_ENABLE_TIER1 ? mockTier1(text, metadata, words.length) : undefined;
  if (tier1?.triggered) {
    return {
      id,
      verdict: "fake",
      fake_probability: 1,
      confidence: 1,
      model_used: "tier1_rules",
      sentiment,
      flags: allFlags,
      tokens: [],
      meta,
      latency_ms: 1,
      created_at: now(),
      token_map: {},
      tier1,
      ...(sarcasm ? { sarcasm } : {}),
      decision_source: "tier1_rules" as DecisionSource,
    };
  }

  // 3. Otherwise the mock "model" scores it, exactly as before.
  let p = 0.16 + spamHits * 0.09 + exclamations * 0.035 + capsWords * 0.045;
  if (words.length < 8) p += 0.12;
  p += (seededNoise(text, 3) - 0.5) * 0.1;
  p = Math.max(0.03, Math.min(0.98, p));
  const fake_probability = Number(p.toFixed(2));

  const tokens = buildTokens(text, fake_probability);
  const model_used: ResponseModelUsed =
    request.model === "nb" ? "nb" : request.model === "svm" ? "svm" : seededNoise(text, 11) > 0.5 ? "svm" : "nb";

  return {
    id,
    verdict: fake_probability >= 0.5 ? "fake" : "genuine",
    fake_probability,
    confidence: fake_probability >= 0.5 ? fake_probability : Number((1 - fake_probability).toFixed(2)),
    model_used,
    sentiment,
    flags: allFlags,
    tokens,
    meta,
    latency_ms: 12 + Math.floor(seededNoise(text, 5) * 40),
    created_at: now(),
    token_map: buildTokenMap(text, tokens),
    ...(tier1 ? { tier1 } : {}),
    ...(sarcasm ? { sarcasm } : {}),
    decision_source: "model" as DecisionSource,
  };
}

/* ------------------------------------------------------------------ */
/* Phase 3.5 — mock /api/explain                                        */
/* ------------------------------------------------------------------ */

function mockExplain(request: ExplainRequest, text: string): ExplainResponse {
  const modelUsed: ResponseModelUsed =
    request.model === "nb" ? "nb" : request.model === "svm" ? "svm" : seededNoise(text, 11) > 0.5 ? "svm" : "nb";
  const tokens = buildTokens(text, 0).slice(0, 10);
  // The label follows the same rules as the backend: NB is never called SHAP.
  const method: ExplainMethod =
    modelUsed === "nb" ? "naive-bayes-logprob" : "shap-linear";
  return {
    method,
    model_used: modelUsed === "nb" ? "nb" : "svm",
    base_value: Number(((seededNoise(text, 13) - 0.5) * 0.4).toFixed(6)),
    tokens,
    token_map: buildTokenMap(text, tokens),
    latency_ms: 8 + Math.floor(seededNoise(text, 17) * 30),
  };
}

/* ------------------------------------------------------------------ */
/* Metrics — same shape as backend/models/metrics.json                 */
/* ------------------------------------------------------------------ */

function makeRoc(auc: number): { fpr: number[]; tpr: number[] } {
  const fpr: number[] = [];
  const tpr: number[] = [];
  // Power curve TPR = FPR^k has AUC = 1/(k+1), so k = 1/AUC - 1.
  const k = Math.max(1 / auc - 1, 0.01);
  for (let i = 0; i <= 20; i++) {
    const x = i / 20;
    fpr.push(Number(x.toFixed(3)));
    tpr.push(Number(Math.pow(x, k).toFixed(3)));
  }
  return { fpr, tpr };
}

function makeModelMetrics(accuracy: number, cm: [number, number][], auc: number): ModelMetrics {
  return {
    accuracy,
    precision: Number((accuracy - 0.03 + seededNoise(String(accuracy), 1) * 0.04).toFixed(4)),
    recall: Number((accuracy - 0.04 + seededNoise(String(accuracy), 2) * 0.05).toFixed(4)),
    f1: Number((accuracy - 0.035 + seededNoise(String(accuracy), 3) * 0.045).toFixed(4)),
    roc_auc: auc,
    confusion_matrix: cm,
    roc_curve: makeRoc(auc),
    best_params: { alpha: 0.5, C: 1.0 },
  };
}

const metricsResponse: MetricsResponse = {
  generated_at: "2026-10-18T09:42:11Z",
  dataset: {
    name: "Deceptive Opinion Spam Corpus (hotel reviews)",
    size: 1600,
    train_size: 1280,
    test_size: 320,
    fake_percent: 50.0,
    avg_words: 21.4,
  },
  best_model: "svm",
  active_feature_set: "tfidf_sentiment",
  models: {
    nb: {
      tfidf_only: makeModelMetrics(0.8469, [[140, 20], [29, 131]], 0.912),
      tfidf_sentiment: makeModelMetrics(0.8719, [[145, 15], [26, 134]], 0.934),
    },
    svm: {
      tfidf_only: makeModelMetrics(0.8906, [[148, 12], [23, 137]], 0.951),
      tfidf_sentiment: makeModelMetrics(0.9094, [[151, 9], [20, 140]], 0.968),
    },
  },
};

/* ------------------------------------------------------------------ */
/* Mock history store (in-memory)                                      */
/* ------------------------------------------------------------------ */

const SAMPLE_HISTORY_REVIEWS: Array<{ review: string; rating?: number }> = [
  { review: "Absolutely AMAZING!!! Best purchase I have EVER made!!! Buy it NOW, you will NOT regret it!!! Five stars!!!!", rating: 5 },
  { review: "Does what it says. Battery life is decent, setup took a few minutes. No complaints so far after two weeks of use.", rating: 4 },
  { review: "Broke after three days. Customer support never answered my emails. Total waste of money, do not buy.", rating: 1 },
  { review: "Solid product for the price. The instructions could be clearer but overall I'm satisfied with the build quality.", rating: 4 },
  { review: "I LOVE LOVE LOVE this!!! Perfect in every way, my whole family uses it now!! Must have item, 10/10!!!", rating: 5 },
  { review: "It arrived with a scratch on the lid. Works fine otherwise, but the packaging was poor for a premium product.", rating: 3 },
];

let historyStore: HistoryEntry[] = [];
let nextId = 1;
let historySeeded = false;

function seedHistory() {
  if (historySeeded) return;
  historySeeded = true;
  SAMPLE_HISTORY_REVIEWS.forEach((s, i) => {
    const p = mockPredict({ review: s.review, rating: s.rating, model: "best" }, nextId);
    historyStore.unshift({
      id: nextId++,
      review_text: s.review,
      verdict: p.verdict,
      fake_probability: p.fake_probability,
      model_used: p.model_used,
      compound: p.sentiment.compound,
      flags_json: JSON.stringify(p.flags),
      tokens_json: JSON.stringify(p.tokens),
      created_at: new Date(Date.now() - (i + 1) * 47 * 60 * 1000).toISOString(),
    });
  });
}

/* ------------------------------------------------------------------ */
/* Public mock client (mirrors the real client interface)              */
/* ------------------------------------------------------------------ */

export const mockApi = {
  async predict(request: PredictRequest): Promise<PredictionResult> {
    await latency(450 + Math.random() * 300);
    if (!request.review.trim()) {
      throw new ApiRequestError("EMPTY_REVIEW", "Review text must not be empty.");
    }
    const result = mockPredict(request, nextId++);
    seedHistory();
    historyStore.unshift({
      id: result.id,
      review_text: request.review,
      verdict: result.verdict,
      fake_probability: result.fake_probability,
      model_used: result.model_used,
      compound: result.sentiment.compound,
      flags_json: JSON.stringify(result.flags),
      tokens_json: JSON.stringify(result.tokens),
      created_at: result.created_at,
    });
    return result;
  },

  /**
   * Phase 3.5 — mock of POST /api/explain. Same shape and same honest method
   * labels as the real endpoint; NB is never labelled SHAP.
   */
  async explain(request: ExplainRequest): Promise<ExplainResponse> {
    await latency(220 + Math.random() * 260);
    const text = request.review.trim();
    if (!text) {
      throw new ApiRequestError("VALIDATION_ERROR", "review must be a non-empty string.");
    }
    if (text.length > 5000) {
      throw new ApiRequestError(
        "VALIDATION_ERROR",
        "review must be 1-5000 characters (got " + text.length + ")."
      );
    }
    return mockExplain(request, text);
  },

  async predictBatch(csvText: string): Promise<BatchResult> {
    await latency(700 + Math.random() * 600);
    const lines = csvText
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length === 0) {
      throw new ApiRequestError("EMPTY_CSV", "The CSV file contains no rows.");
    }
    const header = lines[0].toLowerCase();
    const hasHeader = header.includes("review");
    const dataLines = hasHeader ? lines.slice(1) : lines;
    if (dataLines.length > 5000) {
      throw new ApiRequestError("TOO_MANY_ROWS", "Maximum 5000 rows per batch.");
    }
    const rows: BatchRow[] = dataLines.map((line, i) => {
      // Very small CSV parse: review,"rating" or review,rating
      const m = line.match(/^("([^"]|"")*"|[^,]*)(?:,(.*))?$/);
      let review = (m?.[1] ?? line).replace(/^"|"$/g, "").replace(/""/g, '"');
      let rating: number | undefined;
      if (m?.[3] !== undefined && m[3] !== "") {
        const r = Number(m[3].replace(/^"|"$/g, ""));
        if (r >= 1 && r <= 5) rating = r;
      }
      if (!review) review = line;
      const p = mockPredict({ review, rating, model: "best" }, i + 1);
      return {
        row: i + 1,
        review,
        rating,
        verdict: p.verdict,
        fake_probability: p.fake_probability,
        confidence: p.confidence,
        sentiment_label: p.sentiment.label,
      };
    });
    const fake_count = rows.filter((r) => r.verdict === "fake").length;
    const summary: BatchSummary = {
      total: rows.length,
      fake_count,
      fake_percent: rows.length ? Number(((fake_count / rows.length) * 100).toFixed(1)) : 0,
      avg_confidence: rows.length
        ? Number((rows.reduce((a, r) => a + r.confidence, 0) / rows.length).toFixed(2))
        : 0,
    };
    return { summary, rows };
  },

  async getModels(): Promise<ModelInfo> {
    await latency(120);
    return { models: ["nb", "svm"], default: "best" };
  },

  async getMetrics(): Promise<MetricsResponse> {
    await latency(250 + Math.random() * 250);
    return metricsResponse;
  },

  async getHistory(params: {
    search?: string;
    verdict?: string;
    limit?: number;
    offset?: number;
  }): Promise<HistoryListResponse> {
    await latency(200 + Math.random() * 200);
    seedHistory();
    let entries = [...historyStore].sort((a, b) => b.created_at.localeCompare(a.created_at));
    if (params.search) {
      const q = params.search.toLowerCase();
      entries = entries.filter(
        (e) => e.review_text.toLowerCase().includes(q) || String(e.id).includes(q)
      );
    }
    if (params.verdict === "fake" || params.verdict === "genuine") {
      entries = entries.filter((e) => e.verdict === params.verdict);
    }
    const total = entries.length;
    const offset = params.offset ?? 0;
    const limit = params.limit ?? 50;
    return { total, entries: entries.slice(offset, offset + limit) };
  },

  async deleteHistoryEntry(id: number): Promise<void> {
    await latency(180);
    seedHistory();
    historyStore = historyStore.filter((e) => e.id !== id);
  },

  async clearHistory(): Promise<void> {
    await latency(250);
    historyStore = [];
  },

  async getHealth(): Promise<HealthResponse> {
    await latency(80);
    return { status: "ok", models_loaded: true, version: "0.1.0-mock" };
  },
};

export type ApiClient = typeof mockApi;

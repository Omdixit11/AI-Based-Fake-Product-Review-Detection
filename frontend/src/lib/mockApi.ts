/**
 * Mock API client — the ONLY place mock data lives.
 * Implements the same interface as the real client in api.ts so the UI
 * works unchanged when Phase 4 flips NEXT_PUBLIC_USE_MOCK=false.
 *
 * The mock "model" is a small transparent heuristic so that obviously
 * spammy text scores as fake and balanced text scores as genuine,
 * which makes the demo feel like a real product.
 */

import type {
  BatchResult,
  BatchRow,
  BatchSummary,
  HealthResponse,
  HistoryEntry,
  HistoryListResponse,
  MetricsResponse,
  ModelInfo,
  ModelMetrics,
  ModelUsed,
  PredictionResult,
  PredictRequest,
  RedFlag,
  Sentiment,
  TokenScore,
} from "./types";
import { ApiRequestError } from "./types";

const latency = (ms: number) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();

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
const NEGATIVE_LEXICON = ["bad", "worst", "terrible", "awful", "broken", "hate", "hated", "poor", "disappointed", "refund", "useless", "waste", "cheap", "failed", "regret", "returned"];

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

function mockPredict(request: PredictRequest, id: number): PredictionResult {
  const text = request.review.trim();
  const words = text.match(/[a-zA-Z0-9']+/g) ?? [];
  const capsWords = words.filter((w) => w.length > 1 && /^[A-Z0-9!%]+$/.test(w)).length;
  const exclamations = (text.match(/!/g) ?? []).length;
  const lower = text.toLowerCase();
  const spamHits = SPAMMY_WORDS.filter((w) => lower.includes(w)).length;

  let p = 0.16 + spamHits * 0.09 + exclamations * 0.035 + capsWords * 0.045;
  if (words.length < 8) p += 0.12;
  p += (seededNoise(text, 3) - 0.5) * 0.1;
  p = Math.max(0.03, Math.min(0.98, p));
  const fake_probability = Number(p.toFixed(2));

  const sentiment = analyzeSentiment(text);
  const flags = buildFlags(text, words, capsWords, exclamations);
  const tokens = buildTokens(text, fake_probability);
  const model_used: ModelUsed =
    request.model === "nb" ? "nb" : request.model === "svm" ? "svm" : seededNoise(text, 11) > 0.5 ? "svm" : "nb";

  return {
    id,
    verdict: fake_probability >= 0.5 ? "fake" : "genuine",
    fake_probability,
    confidence: fake_probability >= 0.5 ? fake_probability : Number((1 - fake_probability).toFixed(2)),
    model_used,
    sentiment,
    flags,
    tokens,
    meta: { words: words.length, exclamations, caps_words: capsWords },
    latency_ms: 12 + Math.floor(seededNoise(text, 5) * 40),
    created_at: now(),
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

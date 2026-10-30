/**
 * API contract types — must match docs/LLD.md exactly.
 * These are shared by the real client (api.ts) and the mock client (mockApi.ts).
 */

export type Verdict = "fake" | "genuine";
export type ModelChoice = "best" | "nb" | "svm";
export type ModelUsed = "nb" | "svm";
export type Severity = "low" | "medium" | "high";
export type TokenDirection = "fake" | "genuine";
export type SentimentLabel = "Positive" | "Mixed" | "Negative";
export type FeatureSet = "tfidf_only" | "tfidf_sentiment";

/* ---------- POST /api/predict ---------- */

export interface PredictRequest {
  review: string;
  rating?: number; // 1-5, optional
  model: ModelChoice;
}

export interface Sentiment {
  compound: number;
  label: SentimentLabel;
  pos: number;
  neu: number;
  neg: number;
}

export interface RedFlag {
  code: string;
  label: string;
  severity: Severity;
}

export interface TokenScore {
  token: string;
  score: number;
  direction: TokenDirection;
}

export interface PredictionMeta {
  words: number;
  exclamations: number;
  caps_words: number;
}

export interface PredictionResult {
  id: number;
  verdict: Verdict;
  fake_probability: number;
  confidence: number;
  model_used: ModelUsed;
  sentiment: Sentiment;
  flags: RedFlag[];
  tokens: TokenScore[];
  meta: PredictionMeta;
  latency_ms: number;
  created_at: string; // ISO-8601
}

/* ---------- POST /api/predict/batch ---------- */

export interface BatchSummary {
  total: number;
  fake_count: number;
  fake_percent: number;
  avg_confidence: number;
}

export interface BatchRow {
  row: number;
  review: string;
  rating?: number;
  verdict: Verdict;
  fake_probability: number;
  confidence: number;
  sentiment_label: SentimentLabel;
}

export interface BatchResult {
  summary: BatchSummary;
  rows: BatchRow[];
}

/* ---------- GET /api/models + /api/models/metrics ---------- */

export interface ModelInfo {
  models: ModelUsed[];
  default: ModelChoice;
}

export interface RocCurve {
  fpr: number[];
  tpr: number[];
}

/** Per-model, per-feature-set metrics. Confusion matrix: [[TN, FP], [FN, TP]] (positive = fake). */
export interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  confusion_matrix: [number, number][];
  roc_curve: RocCurve;
  best_params: Record<string, unknown>;
}

export interface DatasetInfo {
  name: string;
  size: number;
  train_size: number;
  test_size: number;
  fake_percent: number;
  avg_words: number;
}

/** Shape of backend/models/metrics.json — see docs/LLD.md. */
export interface MetricsResponse {
  generated_at: string;
  dataset: DatasetInfo;
  best_model: ModelUsed;
  active_feature_set: FeatureSet;
  models: {
    nb: Record<FeatureSet, ModelMetrics>;
    svm: Record<FeatureSet, ModelMetrics>;
  };
}

/* ---------- GET /api/history ---------- */

export interface HistoryEntry {
  id: number;
  review_text: string;
  verdict: Verdict;
  fake_probability: number;
  model_used: ModelUsed;
  compound: number;
  flags_json: string;
  tokens_json: string;
  created_at: string; // ISO-8601
}

export interface HistoryListResponse {
  total: number;
  entries: HistoryEntry[];
}

/* ---------- GET /api/health ---------- */

export interface HealthResponse {
  status: string;
  models_loaded: boolean;
  version: string;
}

/* ---------- Errors ---------- */

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export class ApiRequestError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
  }
}

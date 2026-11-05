/**
 * API contract types — must match docs/LLD.md exactly.
 * These are shared by the real client (api.ts) and the mock client (mockApi.ts).
 *
 * The Phase 3.5 additions (metadata, tier1, sarcasm, explain) are all OPTIONAL.
 * A mock-mode build or an older backend simply omits them, and every consumer
 * below treats a missing field as "feature off", never as an error.
 */

export type Verdict = "fake" | "genuine";
export type ModelChoice = "best" | "nb" | "svm";
export type ModelUsed = "nb" | "svm";
/** A prediction can also come from the Tier-1 rules, which skip the model. */
export type ResponseModelUsed = ModelUsed | "tier1_rules";
export type DecisionSource = "model" | "tier1_rules";
export type Severity = "low" | "medium" | "high";
export type TokenDirection = "fake" | "genuine";
export type SentimentLabel = "Positive" | "Mixed" | "Negative";
export type FeatureSet = "tfidf_only" | "tfidf_sentiment";
export type Tier1Action = "pass" | "flag_spam";
export type Tier1RuleKind = "soft" | "hard";
export type ExplainMethod =
  | "shap-linear"
  | "linear-coefficients"
  | "naive-bayes-logprob";

/* ---------- POST /api/predict ---------- */

/** Optional Phase 3.5 request metadata used by the Tier-1 rules. */
export interface PredictMetadata {
  user_id?: string;
  posted_at?: string; // ISO-8601
  reviews_last_minute?: number; // 0-10000
}

export interface PredictRequest {
  review: string;
  rating?: number; // 1-5, optional
  model: ModelChoice;
  metadata?: PredictMetadata;
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

/** Stemmed token -> the surface words in the review it came from. */
export type TokenMap = Record<string, string[]>;

/* ---------- Phase 3.5: optional blocks on the predict response ---------- */

export interface Tier1Rule {
  code: string;
  label: string;
  severity: Severity;
  kind: Tier1RuleKind;
}

export interface Tier1Block {
  triggered: boolean;
  action: Tier1Action;
  rules: Tier1Rule[];
}

export interface SarcasmBlock {
  suspected: boolean;
  score: number;
  risk_level?: Severity;
  positive_cues?: string[];
  negative_cues?: string[];
}

export interface PredictionResult {
  id: number;
  verdict: Verdict;
  fake_probability: number;
  confidence: number;
  model_used: ResponseModelUsed;
  sentiment: Sentiment;
  flags: RedFlag[];
  tokens: TokenScore[];
  meta: PredictionMeta;
  latency_ms: number;
  created_at: string; // ISO-8601
  /* --- additive Phase 3.5 fields, absent when the feature is switched off --- */
  token_map?: TokenMap;
  tier1?: Tier1Block;
  sarcasm?: SarcasmBlock;
  decision_source?: DecisionSource;
}

/* ---------- POST /api/explain (Phase 3.5) ---------- */

export interface ExplainRequest {
  review: string;
  model: ModelChoice;
}

export interface ExplainResponse {
  method: ExplainMethod;
  model_used: ModelUsed;
  base_value: number;
  tokens: TokenScore[];
  token_map: TokenMap;
  latency_ms: number;
}

/* ---------- POST /api/predict/batch ---------- */

export interface BatchSummary {
  total: number;
  fake_count: number;
  fake_percent: number;
  avg_confidence: number;
  /** Present only when the CSV carried user_id/posted_at and Tier-1 is on. */
  tier1_flagged?: number;
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
  /** Tier-1 hard rules are stored too, so a history row can say "tier1_rules". */
  model_used: ResponseModelUsed;
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

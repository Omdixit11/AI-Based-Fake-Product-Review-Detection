/**
 * API client. Reads NEXT_PUBLIC_USE_MOCK:
 *   "true"  -> mockApi.ts (mock data lives ONLY there)
 *   other   -> real FastAPI backend at NEXT_PUBLIC_API_URL
 *
 * Every function here mirrors the mock client, so components never know
 * which one is active.
 */

import { mockApi } from "./mockApi";
import { cleanMetadata } from "./utils";
import type {
  BatchResult,
  ExplainRequest,
  ExplainResponse,
  HealthResponse,
  HistoryListResponse,
  MetricsResponse,
  ModelInfo,
  PredictionResult,
  PredictRequest,
} from "./types";
import { ApiRequestError } from "./types";

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiRequestError(
      "NETWORK_ERROR",
      `Cannot reach the TruthLens API at ${BASE_URL}. Is the backend running?`
    );
  }
  if (!res.ok) {
    let code = "HTTP_ERROR";
    let message = `Request failed with status ${res.status}.`;
    try {
      const body = await res.json();
      if (body?.error?.code) {
        code = body.error.code;
        message = body.error.message;
      }
    } catch {
      /* keep defaults */
    }
    throw new ApiRequestError(code, message);
  }
  return (await res.json()) as T;
}

export const realApi = {
  async predict(req: PredictRequest): Promise<PredictionResult> {
    const { metadata: rawMetadata, ...rest } = req;
    const metadata = cleanMetadata(rawMetadata);
    const body = metadata ? { ...rest, metadata } : rest;
    return request<PredictionResult>("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  /**
   * Phase 3.5 — on-demand token attribution. Separate from predict() so the
   * analyze page only pays for it when the user asks, and it can 404/501 on an
   * older backend without affecting anything else.
   */
  async explain(req: ExplainRequest): Promise<ExplainResponse> {
    return request<ExplainResponse>("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review: req.review, model: req.model }),
    });
  },

  async predictBatch(csvText: string, filename: string): Promise<BatchResult> {
    const form = new FormData();
    form.append("file", new Blob([csvText], { type: "text/csv" }), filename);
    return request<BatchResult>("/api/predict/batch", { method: "POST", body: form });
  },

  async getModels(): Promise<ModelInfo> {
    return request<ModelInfo>("/api/models");
  },

  async getMetrics(): Promise<MetricsResponse> {
    return request<MetricsResponse>("/api/models/metrics");
  },

  async getHistory(params: {
    search?: string;
    verdict?: string;
    limit?: number;
    offset?: number;
  }): Promise<HistoryListResponse> {
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    if (params.verdict) qs.set("verdict", params.verdict);
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<HistoryListResponse>(`/api/history${suffix}`);
  },

  async deleteHistoryEntry(id: number): Promise<void> {
    await request(`/api/history/${id}`, { method: "DELETE" });
  },

  async clearHistory(): Promise<void> {
    await request("/api/history", { method: "DELETE" });
  },

  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health");
  },
};

export const api = USE_MOCK ? mockApi : realApi;

/** Signature check: every exported function exists on both clients. */
const _typecheck: typeof realApi = mockApi;
void _typecheck;

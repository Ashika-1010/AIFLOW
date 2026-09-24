/**
 * AIFlow API client — replaces the mock implementation.
 * All functions call the real FastAPI backend at VITE_API_BASE_URL.
 * Return types are identical to the original mock so no other file needs changing.
 *
 * Backend: backend/main.py  (uvicorn main:app --reload --port 8000)
 */
import type { Receipt, AuditSummary, AnalyticsPayload } from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)
  ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore parse error
    }
    throw new Error(`AIFlow API error: ${detail}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Execute a request through the real AIFlow decision pipeline.
 * Sends query, qualityFloor, the current region, and an optional docFilename
 * that pins a previously-uploaded corpus document as retrieval context.
 */
export async function runRequest(
  query: string,
  qualityFloor: number = 0.60,
  region: string = 'IN',
  docFilename?: string,
): Promise<Receipt> {
  return apiFetch<Receipt>('/v1/complete', {
    method: 'POST',
    body: JSON.stringify({ query, qualityFloor, region, docFilename: docFilename ?? null }),
  });
}

export async function listReceipts(): Promise<Receipt[]> {
  return apiFetch<Receipt[]>('/v1/receipts');
}

export async function getReceipt(id: string): Promise<Receipt> {
  return apiFetch<Receipt>(`/v1/receipts/${encodeURIComponent(id)}`);
}

export async function getAuditSummary(pessimistic: boolean = false): Promise<AuditSummary> {
  return apiFetch<AuditSummary>(`/v1/audit?pessimistic=${pessimistic}`);
}

export async function getAnalytics(pessimistic: boolean = false): Promise<AnalyticsPayload> {
  return apiFetch<AnalyticsPayload>(`/v1/analytics?pessimistic=${pessimistic}`);
}

export async function uploadDocument(file: File): Promise<{ status: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const url = `${BASE_URL}/v1/documents`;
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore parse error
    }
    throw new Error(`AIFlow API error: ${detail}`);
  }
  const body = await res.json();

return {
  status: body.status ?? body.message ?? 'success',
  filename: file.name,
};
}

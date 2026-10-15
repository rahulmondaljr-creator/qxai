// P2 — Central AI model configuration for RM AI.
// Defaults are ONLY models verified key-free in P1. Anything the user sets
// manually is their explicit choice (tested/untested shown in the Model Lab).

export type TaskCategory = 'general' | 'coding' | 'debugging' | 'reasoning' | 'fast' | 'translation';

export const TASK_CATEGORIES: { id: TaskCategory; label: string }[] = [
  { id: 'general', label: 'General Assistant' },
  { id: 'coding', label: 'Coding' },
  { id: 'debugging', label: 'Debugging' },
  { id: 'reasoning', label: 'Reasoning' },
  { id: 'fast', label: 'Fast Responses' },
  { id: 'translation', label: 'Translation (bn/en/hi)' },
];

/** Verified key-free on 2026-10-15 via the P1 harness (HTTP 200, auth: no). */
export const VERIFIED_FREE_MODEL = 'openai-fast';

const KEY_DEFAULT = 'cx_model_default';
const KEY_CATEGORY = 'cx_model_categories';
const KEY_LAST = 'cx_ai_last_status';

export interface ModelConfig {
  defaultModel: string;
  categories: Record<TaskCategory, string>;
}

export function getModelConfig(): ModelConfig {
  let saved: Partial<Record<TaskCategory, string>> = {};
  try {
    saved = JSON.parse(localStorage.getItem(KEY_CATEGORY) ?? '{}');
  } catch {
    /* ignore */
  }
  const categories: Record<TaskCategory, string> = {
    general: VERIFIED_FREE_MODEL,
    coding: VERIFIED_FREE_MODEL,
    debugging: VERIFIED_FREE_MODEL,
    reasoning: VERIFIED_FREE_MODEL,
    fast: VERIFIED_FREE_MODEL,
    translation: VERIFIED_FREE_MODEL,
  };
  (Object.keys(categories) as TaskCategory[]).forEach((k) => {
    if (typeof saved[k] === 'string' && saved[k]!.trim()) categories[k] = saved[k]!.trim();
  });
  return {
    defaultModel: (localStorage.getItem(KEY_DEFAULT) || '').trim() || VERIFIED_FREE_MODEL,
    categories,
  };
}

export function setDefaultModel(model: string): void {
  localStorage.setItem(KEY_DEFAULT, model.trim() || VERIFIED_FREE_MODEL);
}

export function setCategoryModel(category: TaskCategory, model: string): void {
  const cfg = getModelConfig();
  cfg.categories[category] = model.trim() || VERIFIED_FREE_MODEL;
  try {
    localStorage.setItem(KEY_CATEGORY, JSON.stringify(cfg.categories));
  } catch {
    /* storage full */
  }
}

export function resolveModelForCategory(category: TaskCategory): string {
  const cfg = getModelConfig();
  return cfg.categories[category] || cfg.defaultModel;
}

/* ---------- honest last-request status (written by sendChatStream) ---------- */

export interface LastRequestStatus {
  at: number;
  provider: string;
  requestedModel: string | null; // null = provider-side default (unidentified)
  ok: boolean;
  durationMs: number;
  error?: string;
}

export function recordRequestStatus(status: LastRequestStatus): void {
  try {
    localStorage.setItem(KEY_LAST, JSON.stringify(status));
  } catch {
    /* ignore */
  }
}

export function getLastRequestStatus(): LastRequestStatus | null {
  try {
    return JSON.parse(localStorage.getItem(KEY_LAST) ?? 'null') as LastRequestStatus | null;
  } catch {
    return null;
  }
}

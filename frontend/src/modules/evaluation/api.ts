import { api } from "@/api/client";

export interface PromptVersion {
  id: number;
  prompt_key: string;
  version: number;
  content: string;
  content_sha256: string;
  is_active: boolean;
  created_at: string;
}

export interface EvaluationResult {
  id: number;
  status: string;
  safety_pass_rate: number;
  safety_passed: boolean;
  metrics: Record<string, number>;
  regressions: string[];
  judge_summary?: {
    enabled: boolean;
    overall: number | null;
    minimum: number;
    fail_closed: boolean;
  };
  release_allowed: boolean;
  case_results: Array<{
    case_id: string;
    category: string;
    passed: boolean;
    metrics: Record<string, number>;
    judge_metrics?: Record<string, number>;
    reasons?: string[];
    improvement_suggestions?: string[];
    judge_error?: string | null;
  }>;
  duration_ms: number;
}

export async function listPrompts(
  promptKey?: string,
): Promise<PromptVersion[]> {
  const response = await api.get<PromptVersion[]>(
    "/evaluation/prompts",
    {
      params: {
        prompt_key: promptKey || undefined,
      },
    },
  );
  return response.data;
}

export async function createPrompt(
  promptKey: string,
  content: string,
): Promise<PromptVersion> {
  const response = await api.post<PromptVersion>(
    "/evaluation/prompts",
    {
      prompt_key: promptKey,
      content,
    },
  );
  return response.data;
}

export async function runEvaluation(
  id: number,
  options?: {
    executor_mode?: "demo" | "orchestrator";
    judge_enabled?: boolean;
  },
): Promise<EvaluationResult> {
  const response =
    await api.post<EvaluationResult>(
      `/evaluation/prompts/${id}/run`,
      options ?? {},
    );
  return response.data;
}

export async function activatePrompt(
  id: number,
): Promise<void> {
  await api.post(
    `/evaluation/prompts/${id}/activate`,
  );
}

export async function rollbackPrompt(
  key: string,
): Promise<void> {
  await api.post(
    `/evaluation/prompts/${key}/rollback`,
  );
}

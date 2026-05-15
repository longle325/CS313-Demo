export type ApiThresholds = {
  p33: number;
  p66: number;
};

export type ApiPredictionRow = {
  grid_id: string;
  year: number;
  prediction: number;
};

export type ApiPredictionsResponse = {
  year: number;
  model_id: string;
  thresholds: ApiThresholds;
  model_name: string;
  model_label: string;
  mode: 'forecast';
  train_year_min: number;
  train_year_max: number;
  predictions: ApiPredictionRow[];
};

export type ApiModelOption = {
  model_id: string;
  label: string;
  description: string;
  family: string;
  valid_r2: number | null;
  test_r2: number | null;
  mae: number | null;
  rmse: number | null;
  is_default: boolean;
};

export type ApiModelOptionsResponse = {
  default_model_id: string;
  models: ApiModelOption[];
};

export type ApiFeatureValue = {
  key: string;
  label: string;
  value: number | null;
  unit?: string | null;
};

export type ApiExplanationRow = {
  feature_key: string;
  feature_label: string;
  contribution: number;
  direction: 'positive' | 'negative' | 'neutral';
};

export type ApiGridResponse = {
  grid_id: string;
  year: number;
  model_id: string;
  model_label: string;
  observed: number | null;
  predicted: number;
  level: 'Low' | 'Medium' | 'High';
  thresholds: ApiThresholds;
  features: ApiFeatureValue[];
  explanation: ApiExplanationRow[];
};

export type ApiScenarioRequest = {
  grid_id: string;
  year: 2024 | 2025;
  model_id: string;
  forest_cover_pct: number;
  forest_loss_ha: number;
};

export type ApiScenarioResponse = {
  grid_id: string;
  year: number;
  model_id: string;
  model_label: string;
  baseline_predicted: number;
  scenario_predicted: number;
  delta: number;
  thresholds: ApiThresholds;
  baseline_explanation: ApiExplanationRow[];
  scenario_explanation: ApiExplanationRow[];
};

export type ApiHealthResponse = {
  status: string;
  model_year: number;
  forecast_years: number[];
  model_name: string;
  available_models: string[];
  mode: 'forecast';
};

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => apiGet<ApiHealthResponse>('/api/health'),
  models: () => apiGet<ApiModelOptionsResponse>('/api/models'),
  predictions: (year: number, modelId?: string) =>
    apiGet<ApiPredictionsResponse>(
      `/api/predictions?year=${year}${modelId ? `&model_id=${encodeURIComponent(modelId)}` : ''}`,
    ),
  grid: (gridId: string, year: number, modelId?: string) =>
    apiGet<ApiGridResponse>(
      `/api/grid?year=${year}&grid_id=${encodeURIComponent(gridId)}${
        modelId ? `&model_id=${encodeURIComponent(modelId)}` : ''
      }`,
    ),
  scenario: (payload: ApiScenarioRequest) =>
    apiPost<ApiScenarioResponse>('/api/scenario', payload),
};

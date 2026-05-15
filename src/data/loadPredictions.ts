import { api } from './apiClient';

export async function loadPredictions2024(modelId?: string) {
  return api.predictions(2024, modelId);
}

export async function loadPredictions(year: number, modelId?: string) {
  return api.predictions(year, modelId);
}

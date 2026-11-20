import http from "./http";

export interface MetricPoint {
  date: string;
  weight_kg: number | null;
  fasting_glucose: number | null;
  hba1c: number | null;
}

export interface MetricList {
  points: MetricPoint[];
}

export interface MetricPayload {
  date: string;
  weight_kg?: number | null;
  fasting_glucose?: number | null;
  hba1c?: number | null;
}

export function fetchMetrics(start: string, end: string) {
  return http.get<MetricList>("/api/v1/metrics", { params: { start, end } });
}

export function saveMetric(payload: MetricPayload) {
  return http.post<MetricPoint>("/api/v1/metrics", payload);
}

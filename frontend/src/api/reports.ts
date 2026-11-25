import http from "./http";

export interface ReportHint {
  code: string;
  message: string;
  basis: string;
}

export interface EnergyRatios {
  carb: number | null;
  protein: number | null;
  fat: number | null;
  factor_source: string;
  target_range: null;
}

export interface NutrientTotals {
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  gl_estimate: number | null;
}

export interface ReportItem {
  meal_plan_id: number;
  recipe_id: number;
  name: string;
  meal_type: string;
  servings: number;
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  oil_estimated: boolean;
  gi_band_label: string | null;
  gi_band_source: string;
  gl_estimate: number | null;
  gl_is_approximate: boolean;
}

export interface DailyReport {
  date: string;
  meal_count: number;
  kcal_target: number | null;
  kcal_target_source: string;
  totals: NutrientTotals;
  energy_ratios: EnergyRatios;
  fiber_target_g: null;
  fiber_target_source: string;
  fiber_met_days: null;
  gl_is_approximate: boolean;
  hints: ReportHint[];
  items: ReportItem[];
}

export interface WeekPoint {
  date: string;
  kcal: number | null;
  carb_energy_ratio: number | null;
  fiber_g: number | null;
}

export interface WeeklyReport {
  start: string;
  end: string;
  days: WeekPoint[];
  kcal_average: number | null;
  days_with_kcal: number;
  carb_energy_ratio: number | null;
  energy_factor_source: string;
  target_range: null;
  fiber_target_g: null;
  fiber_target_source: string;
  fiber_met_days: null;
  hints: ReportHint[];
}

export interface ExplainResponse {
  summary: string;
  citation_ids: string[];
  rag: string;
}

export type ReportScope = "daily" | "weekly";

export function fetchDaily(day: string) {
  return http.get<DailyReport>("/api/v1/report/daily", { params: { date: day } });
}

export function fetchWeekly(end: string) {
  return http.get<WeeklyReport>("/api/v1/report/weekly", { params: { end } });
}

export function explainReport(scope: ReportScope, day: string) {
  return http.post<ExplainResponse>(
    "/api/v1/report/explain",
    { scope, date: day },
    { timeout: 70000 },
  );
}

export interface Recipient {
  id: number;
  email: string;
  enabled: boolean;
}

export interface SendResult {
  sent: number;
  recipients: string[];
  date: string;
}

export function fetchRecipients() {
  return http.get<Recipient[]>("/api/v1/report/recipients");
}

export function addRecipient(email: string) {
  return http.post<Recipient>("/api/v1/report/recipients", { email });
}

export function deleteRecipient(id: number) {
  return http.delete<{ ok: boolean }>(`/api/v1/report/recipients/${id}`);
}

export function sendDaily(day: string) {
  return http.post<SendResult>("/api/v1/report/send", null, {
    params: { date: day },
  });
}

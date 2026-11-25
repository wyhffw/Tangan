import type { NutritionFacts } from "./nutrition";
import http from "./http";

export interface RecommendRequest {
  meal_type: string | null;
  only_inventory: boolean;
  exclude_ids: number[];
}

export interface RecommendItem extends NutritionFacts {
  recipe_id: number;
  name: string;
  score: number;
  reason: string;
  citation_ids: string[];
  missing_foods: string[];
  held_foods: string[];
  carb_servings: number | null;
}

export interface RejectReason {
  rule_id: string;
  message: string;
  source: string;
}

export interface RejectedRecipe {
  recipe_id: number;
  name: string;
  reasons: RejectReason[];
}

export interface DailyTargets {
  daily_kcal: number;
  carb_g: number;
  protein_g: number;
  fat_g: number;
  macro_source: string;
  meal_split_source: string;
}

export interface MealTargets {
  meal_type: string;
  kcal: number;
  carb_g: number;
  protein_g: number;
  fat_g: number;
}

export interface GlucoseStatus {
  level: string;
  fasting_glucose: number | null;
  hba1c: number | null;
  carb_scale: number;
  source: string;
}

export interface ConsumedItem {
  recipe_id: number;
  name: string;
  meal_type: string;
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
}

export interface Consumed {
  items: ConsumedItem[];
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
}

export interface RemainingBudget {
  kcal: number;
  carb_g: number;
  protein_g: number;
  fat_g: number;
}

export interface RecommendResponse {
  graph: string;
  rag: string;
  blocked: boolean;
  block_message: string | null;
  strict: RecommendItem[];
  relaxed: RecommendItem[];
  rejected: RejectedRecipe[];
  daily_targets: DailyTargets | null;
  meal_targets: MealTargets | null;
  glucose: GlucoseStatus | null;
  consumed: Consumed | null;
  remaining: RemainingBudget | null;
}

export function fetchRecommend(body: RecommendRequest) {
  return http.post<RecommendResponse>("/api/v1/recommend", body, { timeout: 70000 });
}

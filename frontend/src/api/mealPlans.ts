import type { NutritionFacts } from "./nutrition";
import type { DailyTargets, GlucoseStatus, RemainingBudget } from "./recommend";
import http from "./http";

export interface MealPlanView {
  id: number;
  date: string;
  meal_type: string;
  recipe_id: number;
  already_added: boolean;
}

export function addMealPlan(recipeId: number, mealType: string) {
  return http.post<MealPlanView>("/api/v1/meal-plans", {
    recipe_id: recipeId,
    meal_type: mealType,
  });
}

export interface MealPlanItem {
  id: number;
  date: string;
  meal_type: string;
  recipe_id: number;
  recipe_name: string;
  servings: number;
}

export interface ReportItem extends NutritionFacts {
  meal_plan_id: number;
  recipe_id: number;
  name: string;
  meal_type: string;
  servings: number;
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

export interface PlanSummary {
  date: string;
  daily_targets: DailyTargets | null;
  glucose: GlucoseStatus | null;
  consumed: NutrientTotals;
  remaining: RemainingBudget | null;
  items: ReportItem[];
}

export function listMealPlans() {
  return http.get<MealPlanItem[]>("/api/v1/meal-plans");
}

export function deleteMealPlan(planId: number) {
  return http.delete(`/api/v1/meal-plans/${planId}`);
}

export function fetchPlanSummary() {
  return http.get<PlanSummary>("/api/v1/meal-plans/summary");
}

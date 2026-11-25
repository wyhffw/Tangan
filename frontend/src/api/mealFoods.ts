import http from "./http";
import type { DailyTargets, GlucoseStatus, RemainingBudget } from "./recommend";

export interface FoodUnitOption {
  unit: string;
  grams_per_unit: number;
}

export interface FoodDetail {
  id: number;
  name: string;
  category: string | null;
  per_g: number;
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  gi: number | null;
  gi_band_label: string | null;
  gi_band_source: string;
  gi_source: string | null;
  nutrient_source: string | null;
  units: FoodUnitOption[];
}

export interface MealFoodItem {
  id: number;
  food_id: number;
  food_name: string;
  category: string | null;
  meal_type: string;
  quantity: number;
  unit: string;
  grams: number | null;
  kcal: number | null;
  kcal_estimated: boolean;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  gi: number | null;
  gi_band_label: string | null;
  gi_band_source: string;
  gi_source: string | null;
  nutrient_source: string | null;
}

export interface MealFoodTotals {
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  gi_weighted: number | null;
}

export interface MealFoodSummary {
  date: string;
  daily_targets: DailyTargets | null;
  glucose: GlucoseStatus | null;
  consumed: MealFoodTotals;
  remaining: RemainingBudget | null;
  items: MealFoodItem[];
  source: string;
  gi_source: string;
  incomplete: string[];
}

export interface MealFoodView {
  id: number;
  date: string;
  meal_type: string;
  food_id: number;
  already_added: boolean;
}

export interface RecipeFoodView {
  recipe_id: number;
  added: number;
  updated: number;
}

export function fetchFoodDetail(foodId: number) {
  return http.get<FoodDetail>(`/api/v1/meal-foods/foods/${foodId}`);
}

export function fetchMealFoodSummary() {
  return http.get<MealFoodSummary>("/api/v1/meal-foods/summary");
}

export function addMealFood(foodId: number, mealType: string, quantity: number, unit: string) {
  return http.post<MealFoodView>("/api/v1/meal-foods", {
    food_id: foodId,
    meal_type: mealType,
    quantity,
    unit,
  });
}

export function addRecipeToFoods(recipeId: number, mealType: string) {
  return http.post<RecipeFoodView>("/api/v1/meal-foods/recipe", {
    recipe_id: recipeId,
    meal_type: mealType,
  });
}

export function deleteMealFood(itemId: number) {
  return http.delete(`/api/v1/meal-foods/${itemId}`);
}

export function foodGiText(item: Pick<MealFoodItem, "gi_band_label" | "gi_band_source">): string {
  if (!item.gi_band_label) {
    return "—";
  }
  if (item.gi_band_source === "待核对") {
    return `${item.gi_band_label}（阈值待核对）`;
  }
  return item.gi_band_label;
}


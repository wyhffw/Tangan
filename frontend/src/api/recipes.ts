import type { NutritionFacts } from "./nutrition";
import http from "./http";

export interface RecipeIngredient {
  food_id: number;
  name: string;
  amount_g: number;
  is_main: boolean;
}

export interface RecipeGraphLink {
  food_name: string;
  relation: string;
  direction: string;
  other_label: string;
  other_name: string;
  reason: string | null;
  source: string | null;
}

export interface RecipeDetail extends NutritionFacts {
  id: number;
  name: string;
  cuisine: string | null;
  meal_types: string[];
  cooking_method: string | null;
  steps: string | null;
  servings: number;
  image_url: string | null;
  source: string | null;
  ingredients: RecipeIngredient[];
  graph: string;
  links: RecipeGraphLink[];
}

export function fetchRecipe(recipeId: number) {
  return http.get<RecipeDetail>(`/api/v1/recipes/${recipeId}`);
}

export interface RecipeSummary {
  id: number;
  name: string;
  cuisine: string | null;
  meal_types: string[];
  cooking_method: string | null;
  servings: number;
  image_url: string | null;
  kcal: number | null;
  carb_g: number | null;
  protein_g: number | null;
  fat_g: number | null;
  gi_band_label: string | null;
}

export interface RecipeList {
  items: RecipeSummary[];
  total: number;
  page: number;
  page_size: number;
}

export function fetchRecipes(params: {
  q?: string;
  meal_type?: string;
  page?: number;
  page_size?: number;
}) {
  return http.get<RecipeList>("/api/v1/recipes", { params });
}

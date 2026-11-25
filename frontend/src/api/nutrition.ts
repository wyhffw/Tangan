export interface NutritionFacts {
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

export function formatAmount(value: number | null): string {
  if (value == null) {
    return "—";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function giText(facts: NutritionFacts): string {
  if (!facts.gi_band_label) {
    return "—";
  }
  if (facts.gi_band_source === "待核对") {
    return `${facts.gi_band_label}（阈值待核对）`;
  }
  return facts.gi_band_label;
}

export function glText(facts: NutritionFacts): string {
  const amount = formatAmount(facts.gl_estimate);
  if (facts.gl_is_approximate) {
    return `粗估 ${amount}`;
  }
  return amount;
}

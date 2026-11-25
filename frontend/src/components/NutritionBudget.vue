<template>
  <div class="budget-card">
    <div class="budget-head">
      <h4>{{ mealName }} 营养预算</h4>
      <span class="budget-note">已摄入 {{ fmt(eatenKcal) }} / 预算 {{ fmt(targetKcal) }} kcal</span>
    </div>
    <div class="budget-body">
      <el-progress
        class="ring"
        type="circle"
        :percentage="kcalPercent"
        :width="128"
        :stroke-width="11"
        :color="ringColor"
      >
        <template #default>
          <div class="ring-center">
            <div class="ring-num">{{ fmt(remainingKcal) }}</div>
            <div class="ring-label">剩余 kcal</div>
          </div>
        </template>
      </el-progress>
      <div class="bars">
        <div v-for="macro in macros" :key="macro.key" class="bar-row">
          <span class="bar-name">{{ macro.name }}</span>
          <el-progress
            class="bar"
            :percentage="macro.percent"
            :stroke-width="10"
            :show-text="false"
            :color="macro.color"
          />
          <span class="bar-value">{{ macro.text }}</span>
        </div>
      </div>
    </div>
    <p v-if="carbServings > 0" class="carb-note">1 份碳水 ≈ 15 g，本餐约 {{ carbServings }} 份</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { Consumed, MealTargets, RemainingBudget } from "../api/recommend";

const props = defineProps<{
  mealName: string;
  mealTargets: MealTargets | null;
  consumed: Consumed | null;
  remaining: RemainingBudget | null;
}>();

function fmt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "0";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function clampPercent(value: number | null | undefined, target: number | null | undefined): number {
  if (value == null || target == null || target <= 0 || !Number.isFinite(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round((value / target) * 100)));
}

const eatenKcal = computed(() => props.consumed?.kcal ?? 0);
const targetKcal = computed(() => props.mealTargets?.kcal ?? 0);
const remainingKcal = computed(() => props.remaining?.kcal ?? 0);

const kcalPercent = computed(() => clampPercent(eatenKcal.value, targetKcal.value));

const ringColor = computed(() => {
  if (kcalPercent.value >= 100) {
    return "#ef4444";
  }
  if (kcalPercent.value >= 70) {
    return "#f59e0b";
  }
  return "#22c55e";
});

interface MacroRow {
  key: string;
  name: string;
  color: string;
  percent: number;
  text: string;
}

const macros = computed<MacroRow[]>(() => {
  const target = props.mealTargets;
  const eaten = props.consumed;
  return [
    {
      key: "carb",
      name: "碳水",
      color: "#f59e0b",
      percent: clampPercent(eaten?.carb_g, target?.carb_g),
      text: fmt(eaten?.carb_g) + " / " + fmt(target?.carb_g) + " g",
    },
    {
      key: "protein",
      name: "蛋白质",
      color: "#10b981",
      percent: clampPercent(eaten?.protein_g, target?.protein_g),
      text: fmt(eaten?.protein_g) + " / " + fmt(target?.protein_g) + " g",
    },
    {
      key: "fat",
      name: "脂肪",
      color: "#a855f7",
      percent: clampPercent(eaten?.fat_g, target?.fat_g),
      text: fmt(eaten?.fat_g) + " / " + fmt(target?.fat_g) + " g",
    },
  ];
});

const carbServings = computed(() => {
  const target = props.mealTargets?.carb_g;
  if (target == null || target <= 0) {
    return 0;
  }
  return Math.round((target / 15) * 2) / 2;
});
</script>

<style scoped>
.budget-card {
  margin-top: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.budget-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.budget-head h4 {
  margin: 0;
  color: #1f2937;
}

.budget-note {
  color: #6b7280;
  font-size: 13px;
}

.budget-body {
  display: flex;
  align-items: center;
  gap: 20px;
}

.ring {
  flex: none;
}

.ring-center {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ring-num {
  color: #1f2937;
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
}

.ring-label {
  margin-top: 4px;
  color: #9ca3af;
  font-size: 12px;
}

.bars {
  flex: 1;
  min-width: 0;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
}

.bar-name {
  width: 48px;
  flex: none;
  color: #6b7280;
  font-size: 13px;
  white-space: nowrap;
}

.bar {
  flex: 1;
}

.bar-value {
  min-width: 112px;
  color: #374151;
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
}

.carb-note {
  margin: 8px 0 0;
  color: #9ca3af;
  font-size: 12px;
}

@media (max-width: 560px) {
  .budget-body {
    flex-direction: column;
    align-items: stretch;
  }

  .ring {
    align-self: center;
  }
}
</style>


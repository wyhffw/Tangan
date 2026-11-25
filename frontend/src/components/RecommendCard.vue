<template>
  <el-card class="card">
    <template #header>
      <div class="title">
        <router-link :to="{ path: `/recipe/${item.recipe_id}`, query: { meal } }">
          {{ item.name }}
        </router-link>
        <span class="carbs">{{ carbText }}</span>
      </div>
    </template>
    <p class="reason">{{ item.reason }}</p>
    <div v-if="mealTargets" class="budget">
      <div class="budget-row">
        <span class="label">{{ carbLabel }}</span>
        <el-progress :percentage="carbPercent" :stroke-width="8" :show-text="false" class="bar" />
        <span class="value">{{ carbValue }}</span>
      </div>
      <div class="budget-row">
        <span class="label">{{ kcalLabel }}</span>
        <el-progress :percentage="kcalPercent" :stroke-width="8" :show-text="false" class="bar" />
        <span class="value">{{ kcalValue }}</span>
      </div>
    </div>
    <div class="tags">
      <el-tag v-for="name in item.held_foods" :key="`held-${name}`" type="success">
        库存已有 {{ name }}
      </el-tag>
      <el-tag v-for="name in item.missing_foods" :key="`miss-${name}`" type="warning">
        需购买 {{ name }}
      </el-tag>
    </div>
    <NutritionFacts :facts="item" />
    <p v-if="item.citation_ids.length" class="citations">
      引用片段：{{ item.citation_ids.join("、") }}
    </p>
    <el-button type="primary" plain :loading="adding" @click="$emit('add')">加入我的清单</el-button>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { MealTargets, RecommendItem, RemainingBudget } from "../api/recommend";
import NutritionFacts from "./NutritionFacts.vue";

const props = defineProps<{
  item: RecommendItem;
  meal: string;
  adding: boolean;
  mealTargets?: MealTargets | null;
  remaining?: RemainingBudget | null;
}>();

defineEmits<{ add: [] }>();

const carbText = computed(() => {
  if (props.item.carb_servings == null) {
    return "";
  }
  return `碳水约 ${props.item.carb_servings} 份`;
});

function percent(value: number | null, target: number | undefined): number {
  if (value == null || !target || target <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((value / target) * 100));
}

const carbLabel = computed(() => (props.remaining ? "剩余碳水" : "碳水"));
const kcalLabel = computed(() => (props.remaining ? "剩余热量" : "热量"));

function fmt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

const carbTarget = computed(() => props.remaining?.carb_g ?? props.mealTargets?.carb_g);
const kcalTarget = computed(() => props.remaining?.kcal ?? props.mealTargets?.kcal);

const carbPercent = computed(() => percent(props.item.carb_g, carbTarget.value));
const kcalPercent = computed(() => percent(props.item.kcal, kcalTarget.value));

const carbValue = computed(() => {
  if (props.item.carb_g == null) {
    return "—";
  }
  const target = carbTarget.value;
  const suffix = target != null ? ` / ${fmt(target)} g` : " g";
  return `${fmt(props.item.carb_g)}${suffix}`;
});

const kcalValue = computed(() => {
  if (props.item.kcal == null) {
    return "—";
  }
  const target = kcalTarget.value;
  const suffix = target != null ? ` / ${fmt(target)} kcal` : " kcal";
  return `${fmt(props.item.kcal)}${suffix}`;
});
</script>

<style scoped>
.card {
  margin-bottom: 12px;
}

.title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.title a {
  color: #1f6b3a;
  font-weight: 650;
  text-decoration: none;
}

.carbs {
  color: #b45309;
  font-size: 13px;
  white-space: nowrap;
}

.reason {
  margin-top: 0;
}

.budget {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.budget-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
}

.label {
  width: 56px;
  color: #6b7280;
  font-size: 13px;
}

.bar {
  flex: 1;
}

.value {
  min-width: 120px;
  color: #374151;
  font-size: 13px;
  text-align: right;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.citations {
  color: #6b7280;
  font-size: 13px;
}
</style>

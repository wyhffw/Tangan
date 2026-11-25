<template>
  <div>
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="热量">{{ formatAmount(facts.kcal) }} kcal</el-descriptions-item>
      <el-descriptions-item label="碳水">{{ formatAmount(facts.carb_g) }} g</el-descriptions-item>
      <el-descriptions-item label="蛋白质">{{ formatAmount(facts.protein_g) }} g</el-descriptions-item>
      <el-descriptions-item label="脂肪">{{ formatAmount(facts.fat_g) }} g</el-descriptions-item>
      <el-descriptions-item label="膳食纤维">{{ formatAmount(facts.fiber_g) }} g</el-descriptions-item>
      <el-descriptions-item label="钠">{{ formatAmount(facts.sodium_mg) }} mg</el-descriptions-item>
      <el-descriptions-item label="GI">{{ giText(facts) }}</el-descriptions-item>
      <el-descriptions-item label="GL">{{ glText(facts) }}</el-descriptions-item>
    </el-descriptions>
    <p v-if="facts.oil_estimated" class="hint">烹调油为估算</p>
  </div>
</template>

<script setup lang="ts">
import { formatAmount, giText, glText, type NutritionFacts } from "../api/nutrition";

defineProps<{ facts: NutritionFacts }>();
</script>

<style scoped>
.hint {
  margin: 8px 0 0;
  color: #6b7280;
  font-size: 13px;
}
</style>

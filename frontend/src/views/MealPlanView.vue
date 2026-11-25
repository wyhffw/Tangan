<template>
  <div v-loading="loading">
    <div class="toolbar">
      <h2>我的清单</h2>
      <el-button type="primary" @click="openPicker">添加食材</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-button v-if="error" @click="load">重试</el-button>

    <template v-if="summary">
      <div class="targets">
        <h3>今日营养目标</h3>
        <div class="target-grid">
          <div class="target-item"><span class="dot dot-kcal"></span>热量 <strong>{{ fmt(summary.daily_targets?.daily_kcal) }}</strong> kcal</div>
          <div class="target-item"><span class="dot dot-carb"></span>碳水 <strong>{{ fmt(summary.daily_targets?.carb_g) }}</strong> g</div>
          <div class="target-item"><span class="dot dot-protein"></span>蛋白质 <strong>{{ fmt(summary.daily_targets?.protein_g) }}</strong> g</div>
          <div class="target-item"><span class="dot dot-fat"></span>脂肪 <strong>{{ fmt(summary.daily_targets?.fat_g) }}</strong> g</div>
        </div>
        <NutritionBudget
          v-if="mealTargets"
          meal-name="全天"
          :meal-targets="mealTargets"
          :consumed="consumedView"
          :remaining="summary.remaining"
        />
        <div v-if="summary.glucose" class="glucose">
          <span v-if="summary.glucose.fasting_glucose != null" class="glucose-item">空腹血糖 <strong>{{ summary.glucose.fasting_glucose }} mmol/L</strong></span>
          <span v-if="summary.glucose.hba1c != null" class="glucose-item">糖化 <strong>{{ summary.glucose.hba1c }} %</strong></span>
          <el-tag v-if="glucoseTag" :type="glucoseTagType" size="small">{{ glucoseTag }}</el-tag>
        </div>
        <p v-if="summary.daily_targets" class="target-source">{{ summary.daily_targets.macro_source }}；{{ summary.daily_targets.meal_split_source }}</p>
        <p class="target-source">营养来源：{{ summary.source }}；{{ summary.gi_source }}</p>
        <p class="target-source">营养数字由后端按成分计算，不构成医疗建议。</p>
      </div>

      <h3>已加入的食材</h3>
      <el-empty v-if="summary.items.length === 0" description="今天还没有加入食材，点上方按钮自选食材并指定份量。" />
      <template v-else>
        <div v-for="meal in meals" :key="meal" class="meal-group">
          <template v-if="itemsOf(meal).length">
            <h4>{{ meal }}</h4>
            <el-table :data="itemsOf(meal)" size="small">
              <el-table-column prop="food_name" label="食材" min-width="130" />
              <el-table-column label="份量" width="130">
                <template #default="{ row }">
                  {{ row.quantity }} {{ row.unit }}
                  <span v-if="row.grams != null" class="grams">（{{ fmt(row.grams) }} 克）</span>
                </template>
              </el-table-column>
              <el-table-column label="热量 kcal" width="110">
                <template #default="{ row }">
                  {{ fmt(row.kcal) }}<span v-if="row.kcal_estimated" class="est">*</span>
                </template>
              </el-table-column>
              <el-table-column label="碳水 g" width="80">
                <template #default="{ row }">{{ fmt(row.carb_g) }}</template>
              </el-table-column>
              <el-table-column label="蛋白质 g" width="90">
                <template #default="{ row }">{{ fmt(row.protein_g) }}</template>
              </el-table-column>
              <el-table-column label="脂肪 g" width="80">
                <template #default="{ row }">{{ fmt(row.fat_g) }}</template>
              </el-table-column>
              <el-table-column label="膳食纤维 g" width="100">
                <template #default="{ row }">{{ fmt(row.fiber_g) }}</template>
              </el-table-column>
              <el-table-column label="钠 mg" width="90">
                <template #default="{ row }">{{ fmt(row.sodium_mg) }}</template>
              </el-table-column>
              <el-table-column label="GI" width="150">
                <template #default="{ row }">{{ foodGiText(row) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="70">
                <template #default="{ row }">
                  <el-button link type="danger" @click="remove(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </div>
        <p class="target-source">带 * 的热量为按供能系数（碳水/蛋白 4、脂肪 9 kcal/g）的估算值；成分表缺失的营养项不参与合计。</p>
      </template>
    </template>

    <el-dialog v-model="pickerVisible" title="添加食材" width="620px">
      <el-select
        v-model="selectedFoodId"
        filterable
        remote
        reserve-keyword
        :remote-method="searchFood"
        :loading="foodsLoading"
        placeholder="输入名称搜索食材，如 鸡蛋 / 花生油 / 绵白糖"
        style="width: 100%"
        @change="onFoodSelected"
      >
        <el-option v-for="f in foodOptions" :key="f.id" :label="f.name" :value="f.id">
          <div class="food-option">
            <span>{{ f.name }}</span>
            <span class="food-cat">{{ f.category || "" }}</span>
          </div>
        </el-option>
      </el-select>

      <div v-loading="detailLoading" class="food-detail">
        <template v-if="detail">
          <h4 class="detail-name">{{ detail.name }}</h4>
          <p v-if="detail.category" class="detail-cat">{{ detail.category }}</p>
          <div class="per100">
            <span>每 100 克：</span>
            <strong>{{ fmt(detail.kcal) }} kcal</strong>
            <span>碳水 {{ fmt(detail.carb_g) }} g</span>
            <span>蛋白质 {{ fmt(detail.protein_g) }} g</span>
            <span>脂肪 {{ fmt(detail.fat_g) }} g</span>
            <span v-if="detail.gi != null">GI {{ foodGiText(detail) }}</span>
          </div>
          <div class="form-row">
            <span class="form-label">份量</span>
            <el-input-number v-model="quantity" :min="0.1" :max="9999" :step="0.5" :precision="2" style="width: 140px" />
            <el-select v-model="unit" style="width: 190px" placeholder="单位">
              <el-option v-for="u in detail.units" :key="u.unit" :label="unitLabel(u)" :value="u.unit" />
            </el-select>
          </div>
          <div class="form-row">
            <span class="form-label">餐次</span>
            <el-radio-group v-model="pickMeal">
              <el-radio-button v-for="meal in meals" :key="meal" :label="meal">{{ meal }}</el-radio-button>
            </el-radio-group>
          </div>
          <div class="form-row">
            <el-button type="primary" plain @click="addToPending">加入本餐</el-button>
            <span class="pending-hint">加入后可继续搜索添加，最后点「确认加入」一次性保存。</span>
          </div>
          <p v-if="detail.nutrient_source" class="detail-source">{{ detail.nutrient_source }}</p>
          <p v-if="detail.gi_source" class="detail-source">{{ detail.gi_source }}</p>
        </template>
        <el-empty v-else description="搜索并选择一个食材查看营养与单位" :image-size="60" />
      </div>

      <div v-if="pendingItems.length" class="pending-box">
        <h4>待加入（{{ pendingItems.length }} 项）</h4>
        <div v-for="(item, index) in pendingItems" :key="index" class="pending-item">
          <span class="pending-name">{{ item.food_name }}</span>
          <span class="pending-meal">{{ item.meal_type }}</span>
          <span class="pending-amount">{{ item.quantity }} {{ item.unit }}<span v-if="item.grams != null">（{{ fmt(item.grams) }} 克）</span></span>
          <el-button link type="danger" @click="removePending(index)">移除</el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="cancelPicker">取消</el-button>
        <el-button type="primary" :disabled="pendingItems.length === 0 || submitting" @click="submitPending">
          确认加入<template v-if="pendingItems.length">（{{ pendingItems.length }} 项）</template>
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref } from "vue";

import { searchFoods, type FoodOption } from "../api/foods";
import {
  addMealFood,
  deleteMealFood,
  fetchFoodDetail,
  fetchMealFoodSummary,
  foodGiText,
  type FoodDetail,
  type FoodUnitOption,
  type MealFoodItem,
  type MealFoodSummary,
} from "../api/mealFoods";
import type { Consumed, MealTargets } from "../api/recommend";
import NutritionBudget from "../components/NutritionBudget.vue";

const meals = ["早餐", "午餐", "晚餐", "加餐"] as const;

const loading = ref(false);
const error = ref("");
const summary = ref<MealFoodSummary | null>(null);

const pickerVisible = ref(false);
const foodOptions = ref<FoodOption[]>([]);
const foodsLoading = ref(false);
const selectedFoodId = ref<number | null>(null);
const detail = ref<FoodDetail | null>(null);
const detailLoading = ref(false);
const quantity = ref(1);
const unit = ref("克");
const pickMeal = ref("早餐");
const submitting = ref(false);

interface PendingItem {
  food_id: number;
  food_name: string;
  meal_type: string;
  quantity: number;
  unit: string;
  grams: number | null;
}
const pendingItems = ref<PendingItem[]>([]);

function fmt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function unitLabel(item: FoodUnitOption): string {
  if (item.unit === "克") {
    return "克";
  }
  return `${item.unit}（约 ${item.grams_per_unit} 克）`;
}

function failureText(errorValue: unknown, fallback: string) {
  if (axios.isAxiosError(errorValue)) {
    const detailData = (errorValue.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detailData === "string" && detailData) {
      return detailData;
    }
  }
  return fallback;
}

const mealTargets = computed<MealTargets | null>(() => {
  const t = summary.value?.daily_targets;
  if (!t) {
    return null;
  }
  return {
    meal_type: "全天",
    kcal: t.daily_kcal,
    carb_g: t.carb_g,
    protein_g: t.protein_g,
    fat_g: t.fat_g,
  };
});

const consumedView = computed<Consumed | null>(() => {
  const c = summary.value?.consumed;
  if (!c) {
    return null;
  }
  return {
    items: [],
    kcal: c.kcal,
    carb_g: c.carb_g,
    protein_g: c.protein_g,
    fat_g: c.fat_g,
  };
});

const glucoseTag = computed(() => {
  const level = summary.value?.glucose?.level;
  if (!level || level === "normal") {
    return "";
  }
  return level === "high" ? "血糖明显偏高 · 已收紧碳水" : "血糖偏高 · 已收紧碳水";
});

const glucoseTagType = computed(() => {
  const level = summary.value?.glucose?.level;
  return level === "high" ? "danger" : "warning";
});

function itemsOf(meal: string) {
  return (summary.value?.items || []).filter((item) => item.meal_type === meal);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const response = await fetchMealFoodSummary();
    summary.value = response.data;
  } catch (caught) {
    summary.value = null;
    error.value = failureText(caught, "暂时无法加载清单");
  } finally {
    loading.value = false;
  }
}

async function searchFood(keyword: string) {
  const text = keyword.trim();
  if (!text) {
    foodOptions.value = [];
    return;
  }
  foodsLoading.value = true;
  try {
    const response = await searchFoods(text);
    foodOptions.value = response.data;
  } catch (caught) {
    ElMessage.error(failureText(caught, "暂时无法搜索食材"));
  } finally {
    foodsLoading.value = false;
  }
}

async function onFoodSelected(id: number | null) {
  detail.value = null;
  if (id == null) {
    return;
  }
  detailLoading.value = true;
  try {
    const response = await fetchFoodDetail(id);
    detail.value = response.data;
    quantity.value = 1;
    unit.value = response.data.units.some((item) => item.unit === "克")
      ? "克"
      : (response.data.units[0]?.unit ?? "克");
  } catch (caught) {
    detail.value = null;
    ElMessage.error(failureText(caught, "暂时无法加载食材营养"));
  } finally {
    detailLoading.value = false;
  }
}

function resetPicker(keepMeal = false) {
  selectedFoodId.value = null;
  detail.value = null;
  foodOptions.value = [];
  quantity.value = 1;
  unit.value = "克";
  if (!keepMeal) {
    pickMeal.value = "早餐";
  }
}

function openPicker() {
  resetPicker();
  pendingItems.value = [];
  pickerVisible.value = true;
}

function addToPending() {
  const foodId = selectedFoodId.value;
  const food = detail.value;
  if (foodId == null || !food) {
    ElMessage.warning("请先选择食材");
    return;
  }
  if (quantity.value <= 0) {
    ElMessage.warning("份量要大于 0");
    return;
  }
  const unitInfo = food.units.find((item) => item.unit === unit.value);
  const grams = unitInfo ? quantity.value * unitInfo.grams_per_unit : null;
  const existing = pendingItems.value.find(
    (item) => item.food_id === foodId && item.meal_type === pickMeal.value,
  );
  if (existing) {
    existing.quantity = quantity.value;
    existing.unit = unit.value;
    existing.grams = grams;
    ElMessage.success("已更新本餐列表中的这份食材");
  } else {
    pendingItems.value.push({
      food_id: foodId,
      food_name: food.name,
      meal_type: pickMeal.value,
      quantity: quantity.value,
      unit: unit.value,
      grams,
    });
    ElMessage.success("已加入本餐列表，可继续添加");
  }
  resetPicker(true);
}

function removePending(index: number) {
  pendingItems.value.splice(index, 1);
}

function cancelPicker() {
  pendingItems.value = [];
  pickerVisible.value = false;
}

async function submitPending() {
  if (pendingItems.value.length === 0) {
    ElMessage.warning("本餐还没有加入任何食材");
    return;
  }
  const items = [...pendingItems.value];
  submitting.value = true;
  let failed = 0;
  for (const item of items) {
    try {
      await addMealFood(item.food_id, item.meal_type, item.quantity, item.unit);
    } catch (caught) {
      failed += 1;
      ElMessage.error(failureText(caught, `「${item.food_name}」加入失败`));
    }
  }
  submitting.value = false;
  if (failed === 0) {
    ElMessage.success(`已加入 ${items.length} 项食材`);
  } else {
    ElMessage.warning(`已加入 ${items.length - failed} 项，${failed} 项失败`);
  }
  pendingItems.value = [];
  pickerVisible.value = false;
  await load();
}

async function remove(row: MealFoodItem) {
  try {
    await ElMessageBox.confirm(`确定从今日清单删除「${row.food_name}」吗？`, "删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await deleteMealFood(row.id);
    ElMessage.success("已删除");
    await load();
  } catch (caught) {
    ElMessage.error(failureText(caught, "暂时无法删除"));
  }
}

onMounted(() => {
  void load();
});
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar h2 {
  margin: 0;
}

.targets {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
}

.targets h3 {
  margin: 0 0 8px;
}

.target-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 8px;
}

.target-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #374151;
  font-size: 14px;
}

.target-item strong {
  color: #1f6b3a;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex: none;
}

.dot-kcal {
  background: #3b82f6;
}

.dot-carb {
  background: #f59e0b;
}

.dot-protein {
  background: #10b981;
}

.dot-fat {
  background: #a855f7;
}

.glucose {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  color: #374151;
  font-size: 13px;
}

.glucose-item strong {
  color: #b91c1c;
}

.target-source {
  margin: 8px 0 0;
  color: #9ca3af;
  font-size: 12px;
}

h3 {
  margin: 8px 0 12px;
}

.meal-group {
  margin-bottom: 16px;
}

.meal-group h4 {
  margin: 0 0 8px;
  color: #374151;
}

.grams {
  color: #9ca3af;
  font-size: 12px;
}

.est {
  color: #d97706;
  margin-left: 2px;
}

.food-option {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.food-cat {
  color: #9ca3af;
  font-size: 12px;
}

.food-detail {
  margin-top: 16px;
  min-height: 120px;
}

.detail-name {
  margin: 0 0 2px;
  color: #1f2937;
}

.detail-cat {
  margin: 0 0 8px;
  color: #9ca3af;
  font-size: 12px;
}

.per100 {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 6px;
  color: #374151;
  font-size: 13px;
}

.per100 strong {
  color: #1f6b3a;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.form-label {
  width: 44px;
  flex: none;
  color: #374151;
  font-size: 14px;
}

.detail-source {
  margin: 10px 0 0;
  color: #9ca3af;
  font-size: 12px;
}

.pending-hint {
  color: #9ca3af;
  font-size: 12px;
}

.pending-box {
  margin-top: 16px;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.pending-box h4 {
  margin: 0 0 8px;
  color: #374151;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.pending-item + .pending-item {
  border-top: 1px solid #f3f4f6;
}

.pending-name {
  color: #1f2937;
  font-size: 14px;
}

.pending-meal {
  color: #6b7280;
  font-size: 12px;
}

.pending-amount {
  margin-left: auto;
  color: #374151;
  font-size: 13px;
}
</style>


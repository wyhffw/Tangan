<template>
  <div v-loading="loading">
    <div class="toolbar">
      <el-radio-group v-model="mealType">
        <el-radio v-for="meal in meals" :key="meal" :value="meal">{{ meal }}</el-radio>
      </el-radio-group>
      <el-checkbox v-model="onlyInventory">只用冰箱里的食材</el-checkbox>
      <el-button type="primary" :disabled="loading" @click="generate">生成推荐</el-button>
      <el-button :disabled="loading || filtersChanged || shown.length === 0" @click="swap">
        换一批
      </el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-button v-if="error" @click="generate">重试</el-button>

    <template v-else-if="result">
      <div class="status">
        <el-tag :type="result.graph === 'up' ? 'success' : 'info'">图谱 {{ result.graph }}</el-tag>
        <el-tag :type="result.rag === 'up' ? 'success' : 'info'">检索 {{ result.rag }}</el-tag>
      </div>
      <el-alert
        v-if="result.blocked"
        :title="result.block_message || '请就医'"
        type="warning"
        show-icon
        :closable="false"
      />
      <template v-else>
        <div v-if="result.daily_targets" class="targets">
          <h3>今日营养目标</h3>
          <div class="target-grid">
            <div class="target-item"><span class="dot dot-kcal"></span>热量 <strong>{{ fmt(result.daily_targets.daily_kcal) }}</strong> kcal</div>
            <div class="target-item"><span class="dot dot-carb"></span>碳水 <strong>{{ fmt(result.daily_targets.carb_g) }}</strong> g</div>
            <div class="target-item"><span class="dot dot-protein"></span>蛋白质 <strong>{{ fmt(result.daily_targets.protein_g) }}</strong> g</div>
            <div class="target-item"><span class="dot dot-fat"></span>脂肪 <strong>{{ fmt(result.daily_targets.fat_g) }}</strong> g</div>
          </div>
          <NutritionBudget
            v-if="result.meal_targets"
            meal-name="全天"
            :meal-targets="result.meal_targets"
            :consumed="result.consumed"
            :remaining="result.remaining"
          />
          <div v-if="result.glucose" class="glucose">
            <span v-if="result.glucose.fasting_glucose != null" class="glucose-item">空腹血糖 <strong>{{ result.glucose.fasting_glucose }} mmol/L</strong></span>
            <span v-if="result.glucose.hba1c != null" class="glucose-item">糖化 <strong>{{ result.glucose.hba1c }} %</strong></span>
            <el-tag v-if="glucoseTag" :type="glucoseTagType" size="small">{{ glucoseTag }}</el-tag>
          </div>
          <div v-if="result.consumed && result.consumed.items.length" class="consumed">
            今日已摄入：<span v-for="item in result.consumed.items" :key="item.recipe_id" class="consumed-item">{{ item.name }}（碳水 {{ item.carb_g ?? "—" }} g · 热量 {{ item.kcal ?? "—" }} kcal）</span>
          </div>
          <p class="target-source">{{ result.daily_targets.macro_source }}；{{ result.daily_targets.meal_split_source }}</p>
        </div>
        <template v-if="loadedOnly">
          <h3>严格结果</h3>
          <el-empty v-if="result.strict.length === 0" description="没有能完全用冰箱食材做的菜" />
          <RecommendCard
            v-for="item in result.strict"
            :key="item.recipe_id"
            :item="item"
            :meal="loadedMeal"
            :adding="addingId === item.recipe_id"
            :meal-targets="result.meal_targets"
            :remaining="result.remaining"
            @add="add(item)"
          />
          <h3>放宽后需购买</h3>
          <el-empty v-if="result.relaxed.length === 0" description="没有需要另外购买食材的菜" />
          <RecommendCard
            v-for="item in result.relaxed"
            :key="item.recipe_id"
            :item="item"
            :meal="loadedMeal"
            :adding="addingId === item.recipe_id"
            :meal-targets="result.meal_targets"
            :remaining="result.remaining"
            @add="add(item)"
          />
        </template>
        <template v-else>
          <el-empty v-if="result.strict.length === 0" :description="emptyText" />
          <RecommendCard
            v-for="item in result.strict"
            :key="item.recipe_id"
            :item="item"
            :meal="loadedMeal"
            :adding="addingId === item.recipe_id"
            :meal-targets="result.meal_targets"
            :remaining="result.remaining"
            @add="add(item)"
          />
        </template>
        <el-collapse v-if="result.rejected.length">
          <el-collapse-item title="为什么不推荐" name="rejected">
            <div v-for="item in result.rejected" :key="item.recipe_id" class="rejected">
              <strong>{{ item.name }}</strong>
              <p v-for="reason in item.reasons" :key="reason.rule_id">
                {{ reason.rule_id }}：{{ reason.message }}
                <span class="source">出处：{{ reason.source }}</span>
              </p>
            </div>
          </el-collapse-item>
        </el-collapse>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";

import { addRecipeToFoods } from "../api/mealFoods";
import { fetchRecommend, type RecommendItem, type RecommendResponse } from "../api/recommend";
import NutritionBudget from "../components/NutritionBudget.vue";
import RecommendCard from "../components/RecommendCard.vue";

const meals = ["早餐", "午餐", "晚餐", "加餐"] as const;

const mealType = ref<(typeof meals)[number]>("午餐");
const onlyInventory = ref(false);
const excludeIds = ref<number[]>([]);
const loading = ref(false);
const error = ref("");
const result = ref<RecommendResponse | null>(null);
const loadedMeal = ref("午餐");
const loadedOnly = ref(false);
const addingId = ref<number | null>(null);
let requestSeq = 0;
const swapped = ref(false);

const shown = computed(() => {
  if (!result.value || result.value.blocked) {
    return [];
  }
  return [...result.value.strict, ...result.value.relaxed];
});

const glucoseTag = computed(() => {
  const level = result.value?.glucose?.level;
  if (!level || level === "normal") {
    return "";
  }
  return level === "high" ? "血糖明显偏高 · 已收紧碳水" : "血糖偏高 · 已收紧碳水";
});

const glucoseTagType = computed(() => {
  const level = result.value?.glucose?.level;
  return level === "high" ? "danger" : "warning";
});

const emptyText = computed(() =>
  swapped.value
    ? "已经看完全部符合条件的结果，点「生成推荐」重新开始"
    : "这次没有可推荐的菜",
);

const filtersChanged = computed(
  () => mealType.value !== loadedMeal.value || onlyInventory.value !== loadedOnly.value,
);

function fmt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function failureText(errorValue: unknown, fallback: string) {
  if (axios.isAxiosError(errorValue)) {
    const detail = (errorValue.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string" && detail) {
      return detail;
    }
  }
  return fallback;
}

async function load(nextExclude: number[]) {
  const seq = ++requestSeq;
  const meal = mealType.value;
  const only = onlyInventory.value;
  loading.value = true;
  error.value = "";
  try {
    const response = await fetchRecommend({
      meal_type: meal,
      only_inventory: only,
      exclude_ids: nextExclude,
    });
    if (seq !== requestSeq) {
      return;
    }
    result.value = response.data;
    excludeIds.value = nextExclude;
    loadedMeal.value = meal;
    loadedOnly.value = only;
  } catch (caught) {
    if (seq !== requestSeq) {
      return;
    }
    result.value = null;
    error.value = failureText(caught, "暂时无法生成推荐");
  } finally {
    if (seq === requestSeq) {
      loading.value = false;
    }
  }
}

function generate() {
  swapped.value = false;
  void load([]);
}

function swap() {
  swapped.value = true;
  void load([...excludeIds.value, ...shown.value.map((item) => item.recipe_id)]);
}

async function add(item: RecommendItem) {
  addingId.value = item.recipe_id;
  try {
    const response = await addRecipeToFoods(item.recipe_id, loadedMeal.value);
    const text = `已加入我的清单（新增 ${response.data.added} 项食材）`;
    ElMessage.success(text);
    void load([...excludeIds.value, item.recipe_id]);
  } catch (caught) {
    ElMessage.error(failureText(caught, "暂时无法加入清单"));
  } finally {
    addingId.value = null;
  }
}

onMounted(() => {
  void load([]);
});
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.status {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
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

.consumed {
  margin-top: 8px;
  color: #374151;
  font-size: 13px;
}

.consumed-item {
  margin-right: 12px;
  color: #6b7280;
}

.target-source {
  margin: 8px 0 0;
  color: #9ca3af;
  font-size: 12px;
}

h3 {
  margin: 8px 0 12px;
}

.source {
  margin-left: 8px;
  color: #6b7280;
}

.rejected + .rejected {
  margin-top: 8px;
}
</style>

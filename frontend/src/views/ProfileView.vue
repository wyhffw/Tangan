<template>
  <div v-loading="loading">
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" />
    <el-button v-if="loadError" @click="load">重试</el-button>
    <template v-else-if="!loading">
      <template v-if="!editing && !isBlank">
        <el-descriptions title="健康档案" :column="2" border class="profile-detail">
          <el-descriptions-item label="性别">{{ form.gender || "—" }}</el-descriptions-item>
          <el-descriptions-item label="出生年份">{{ form.birth_year ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="年龄">{{ preview.age ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="身高">{{ form.height_cm != null ? form.height_cm + " 厘米" : "—" }}</el-descriptions-item>
          <el-descriptions-item label="体重">{{ form.weight_kg != null ? form.weight_kg + " 千克" : "—" }}</el-descriptions-item>
          <el-descriptions-item label="BMI">{{ preview.bmi ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="活动水平">{{ form.activity_level || "—" }}</el-descriptions-item>
          <el-descriptions-item label="理想体重">{{ preview.ideal_weight_kg != null ? preview.ideal_weight_kg + " 千克" : "—" }}</el-descriptions-item>
          <el-descriptions-item label="建议热量">{{ preview.suggested_kcal != null ? preview.suggested_kcal + " 千卡（估算）" : "—" }}</el-descriptions-item>
          <el-descriptions-item label="疾病">{{ form.diseases.length ? form.diseases.join("、") : "无" }}</el-descriptions-item>
          <el-descriptions-item label="过敏原">{{ form.allergies.length ? form.allergies.join("、") : "无" }}</el-descriptions-item>
          <el-descriptions-item label="忌口">{{ form.dislikes.length ? form.dislikes.join("、") : "无" }}</el-descriptions-item>
          <el-descriptions-item label="口味">{{ form.tastes.length ? form.tastes.join("、") : "无" }}</el-descriptions-item>
          <el-descriptions-item label="菜系">{{ form.cuisines.length ? form.cuisines.join("、") : "无" }}</el-descriptions-item>
          <el-descriptions-item label="空腹血糖">{{ form.fasting_glucose != null ? form.fasting_glucose + " mmol/L" : "未填写" }}（不参与推荐）</el-descriptions-item>
          <el-descriptions-item label="糖化血红蛋白">{{ form.hba1c != null ? form.hba1c + " %" : "未填写" }}（不参与推荐）</el-descriptions-item>
          <el-descriptions-item label="每日热量目标">{{ form.daily_kcal_target != null ? form.daily_kcal_target + " 千卡" : "—" }}</el-descriptions-item>
        </el-descriptions>
        <div class="actions">
          <el-button type="primary" @click="startEdit">编辑档案</el-button>
        </div>
      </template>
      <template v-else>
        <p v-if="isBlank" class="hint">还没有完整的健康档案，填写后保存。</p>
        <p v-else class="hint">修改档案后保存。</p>
        <el-steps :active="step" finish-status="success" align-center class="steps">
        <el-step title="基本信息" />
        <el-step title="疾病指标" />
        <el-step title="过敏忌口" />
        <el-step title="偏好" />
      </el-steps>
      <el-alert
        v-if="preview.block_message"
        :title="preview.block_message"
        type="error"
        show-icon
        :closable="false"
      />
      <el-alert
        v-if="recipeBlock"
        :title="recipeBlock"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <div v-show="step === 0">
          <el-form-item label="性别" prop="gender">
            <el-radio-group v-model="form.gender">
              <el-radio value="女">女</el-radio>
              <el-radio value="男">男</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="出生年份" prop="birth_year">
            <el-input-number v-model="form.birth_year" :min="1900" :max="2100" :step="1" />
          </el-form-item>
          <el-form-item label="身高" prop="height_cm">
            <el-input-number v-model="form.height_cm" :min="50" :max="230" :precision="1" :step="1" />
            <span class="unit">厘米</span>
          </el-form-item>
          <el-form-item label="体重" prop="weight_kg">
            <el-input-number v-model="form.weight_kg" :min="20" :max="300" :precision="1" :step="0.5" />
            <span class="unit">千克</span>
          </el-form-item>
          <el-form-item label="活动水平" prop="activity_level">
            <el-radio-group v-model="form.activity_level">
              <el-radio value="轻">轻</el-radio>
              <el-radio value="中">中</el-radio>
              <el-radio value="重">重</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="年龄">{{ preview.age ?? "—" }}</el-descriptions-item>
            <el-descriptions-item label="BMI">{{ preview.bmi ?? "—" }}</el-descriptions-item>
            <el-descriptions-item label="理想体重">
              {{ preview.ideal_weight_kg != null ? `${preview.ideal_weight_kg} 千克` : "—" }}
            </el-descriptions-item>
            <el-descriptions-item label="建议热量">
              {{
                preview.suggested_kcal != null
                  ? `${preview.suggested_kcal} 千卡（简化估算，系数待核对）`
                  : "—"
              }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div v-show="step === 1">
          <el-form-item label="疾病">
            <el-select
              v-model="form.diseases"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入"
            >
              <el-option v-for="item in diseaseOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="空腹血糖">
            <el-input-number
              v-model="form.fasting_glucose"
              :min="0.1"
              :max="40"
              :precision="1"
              :step="0.1"
            />
            <span class="unit">mmol/L，不参与饮食推荐</span>
          </el-form-item>
          <el-form-item label="糖化血红蛋白">
            <el-input-number v-model="form.hba1c" :min="0.1" :max="30" :precision="1" :step="0.1" />
            <span class="unit">%，不参与饮食推荐</span>
          </el-form-item>
        </div>
        <div v-show="step === 2">
          <el-form-item label="过敏原">
            <el-select
              v-model="form.allergies"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入"
            >
              <el-option v-for="item in allergenOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="忌口">
            <el-select
              v-model="form.dislikes"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入后回车添加"
            />
          </el-form-item>
        </div>
        <div v-show="step === 3">
          <el-form-item label="口味">
            <el-select v-model="form.tastes" multiple placeholder="可多选">
              <el-option v-for="item in tasteOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="菜系">
            <el-select v-model="form.cuisines" multiple placeholder="可多选">
              <el-option v-for="item in cuisineOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="每日热量目标" prop="daily_kcal_target">
            <el-input-number v-model="form.daily_kcal_target" :min="1" :max="10000" :step="50" />
            <span class="unit">千卡，可手动修改</span>
          </el-form-item>
        </div>
      </el-form>
      <div class="actions">
        <el-button v-if="step > 0" @click="step -= 1">上一步</el-button>
        <el-button v-if="step < 3" type="primary" @click="next">下一步</el-button>
        <el-button v-else type="primary" :loading="saving" :disabled="!preview.can_save" @click="save">
          保存档案
        </el-button>
      </div>
        <el-alert v-if="saveError" :title="saveError" type="error" show-icon :closable="false" />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { fetchProfile, previewProfile, saveProfile, type ProfilePreview } from "../api/profile";

const diseaseOptions = ["2型糖尿病", "肾病", "妊娠"];
const allergenOptions = ["牛奶", "鸡蛋", "花生", "大豆", "小麦", "虾", "蟹", "鱼"];
const tasteOptions = ["清淡", "咸鲜", "酸甜", "麻辣"];
const cuisineOptions = ["家常", "川菜", "粤菜", "素食"];

const loading = ref(true);
const loadError = ref("");
const saveError = ref("");
const saving = ref(false);
const step = ref(0);
const isBlank = ref(true);
const editing = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({
  gender: "",
  birth_year: undefined as number | undefined,
  height_cm: undefined as number | undefined,
  weight_kg: undefined as number | undefined,
  activity_level: "",
  diseases: [] as string[],
  fasting_glucose: undefined as number | undefined,
  hba1c: undefined as number | undefined,
  allergies: [] as string[],
  dislikes: [] as string[],
  tastes: [] as string[],
  cuisines: [] as string[],
  daily_kcal_target: undefined as number | undefined,
});
const preview = reactive<ProfilePreview>({
  age: null,
  bmi: null,
  ideal_weight_kg: null,
  suggested_kcal: null,
  kcal_per_kg: null,
  kcal_source: "待核对",
  can_save: false,
  block_message: null,
});

const rules: FormRules = {
  gender: [{ required: true, message: "请选择性别", trigger: "change" }],
  birth_year: [{ required: true, message: "请填写出生年份", trigger: "change" }],
  height_cm: [
    { required: true, message: "请填写身高", trigger: "change" },
    {
      type: "number",
      min: 105.1,
      message: "身高需要大于 105 厘米才能估算理想体重",
      trigger: "change",
    },
  ],
  weight_kg: [
    { required: true, message: "请填写体重", trigger: "change" },
    { type: "number", min: 20.1, message: "请填写大于 20 千克的体重", trigger: "change" },
  ],
  activity_level: [{ required: true, message: "请选择活动水平", trigger: "change" }],
  daily_kcal_target: [{ required: true, message: "请填写每日热量目标", trigger: "change" }],
};

const recipeBlock = computed(() => {
  const blocked = form.diseases.some((name) => /肾病|妊娠|孕/.test(name));
  return blocked ? "档案中有肾病或妊娠相关情况，不生成个体化食谱，请就医或咨询医生、营养师。" : "";
});

function applyNumber(value: number | null) {
  return value ?? undefined;
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const { data } = await fetchProfile();
    isBlank.value = data.birth_year == null || data.height_cm == null;
    editing.value = isBlank.value;
    Object.assign(preview, {
      age: data.age,
      bmi: data.bmi,
      ideal_weight_kg: data.ideal_weight_kg,
      suggested_kcal: data.suggested_kcal,
      kcal_per_kg: data.kcal_per_kg,
      kcal_source: data.kcal_source,
      can_save: true,
      block_message: null,
    });
    form.gender = data.gender ?? "";
    form.birth_year = applyNumber(data.birth_year);
    form.height_cm = applyNumber(data.height_cm);
    form.weight_kg = applyNumber(data.weight_kg);
    form.activity_level = data.activity_level ?? "";
    form.diseases = [...data.diseases];
    form.fasting_glucose = applyNumber(data.fasting_glucose);
    form.hba1c = applyNumber(data.hba1c);
    form.allergies = [...data.allergies];
    form.dislikes = [...data.dislikes];
    form.tastes = [...(data.preferences.tastes ?? [])];
    form.cuisines = [...(data.preferences.cuisines ?? [])];
    form.daily_kcal_target = applyNumber(data.daily_kcal_target);
  } catch {
    loadError.value = "暂时读不到健康档案";
  } finally {
    loading.value = false;
  }
}

let ticket = 0;

async function refreshPreview() {
  const current = ++ticket;
  if (form.birth_year == null) {
    preview.can_save = false;
    preview.block_message = null;
    preview.age = null;
    preview.bmi = null;
    preview.suggested_kcal = null;
    preview.ideal_weight_kg = null;
    return;
  }
  const payload: {
    birth_year: number;
    height_cm?: number;
    weight_kg?: number;
    activity_level?: string;
  } = { birth_year: form.birth_year };
  if (
    form.height_cm != null &&
    form.height_cm > 105 &&
    form.weight_kg != null &&
    form.weight_kg > 20
  ) {
    payload.height_cm = form.height_cm;
    payload.weight_kg = form.weight_kg;
    if (form.activity_level) {
      payload.activity_level = form.activity_level;
    }
  }
  try {
    const { data } = await previewProfile(payload);
    if (current !== ticket) {
      return;
    }
    Object.assign(preview, data);
    if (form.daily_kcal_target == null && data.suggested_kcal != null) {
      form.daily_kcal_target = data.suggested_kcal;
    }
  } catch {
    if (current === ticket) {
      preview.can_save = false;
    }
  }
}

watch(
  () => [form.birth_year, form.height_cm, form.weight_kg, form.activity_level],
  () => {
    void refreshPreview();
  },
);

async function next() {
  if (step.value !== 0) {
    step.value += 1;
    return;
  }
  try {
    await formRef.value?.validateField([
      "gender",
      "birth_year",
      "height_cm",
      "weight_kg",
      "activity_level",
    ]);
  } catch {
    return;
  }
  await refreshPreview();
  if (!preview.can_save) {
    return;
  }
  step.value += 1;
}

function startEdit() {
  step.value = 0;
  editing.value = true;
}

function messageFrom(caught: unknown) {
  if (axios.isAxiosError(caught)) {
    const detail = caught.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return "保存失败，请检查填写内容";
}

async function save() {
  saveError.value = "";
  try {
    await formRef.value?.validate();
  } catch {
    return;
  }
  if (
    !form.gender ||
    form.birth_year == null ||
    form.height_cm == null ||
    form.weight_kg == null ||
    !form.activity_level ||
    form.daily_kcal_target == null
  ) {
    saveError.value = "请先完成基本信息和热量目标";
    return;
  }
  saving.value = true;
  try {
    const { data } = await saveProfile({
      gender: form.gender,
      birth_year: form.birth_year,
      height_cm: form.height_cm,
      weight_kg: form.weight_kg,
      activity_level: form.activity_level,
      diseases: form.diseases,
      fasting_glucose: form.fasting_glucose ?? null,
      hba1c: form.hba1c ?? null,
      allergies: form.allergies,
      dislikes: form.dislikes,
      preferences: { tastes: form.tastes, cuisines: form.cuisines },
      daily_kcal_target: form.daily_kcal_target,
    });
    isBlank.value = false;
    editing.value = false;
    Object.assign(preview, {
      age: data.age,
      bmi: data.bmi,
      ideal_weight_kg: data.ideal_weight_kg,
      suggested_kcal: data.suggested_kcal,
      kcal_per_kg: data.kcal_per_kg,
      kcal_source: data.kcal_source,
      can_save: true,
      block_message: null,
    });
    ElMessage.success("档案已保存");
  } catch (caught) {
    saveError.value = messageFrom(caught);
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  void load();
});
</script>

<style scoped>
.hint {
  margin: 0 0 12px;
  color: #5c6b62;
}

.profile-detail {
  margin-bottom: 16px;
}

.steps {
  margin-bottom: 20px;
}

.unit {
  margin-left: 8px;
  color: #5c6b62;
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
</style>

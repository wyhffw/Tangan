<template>
  <div class="home">
    <section class="hero">
      <h1 class="hero-greeting">{{ greeting }}，{{ username }}</h1>
      <p class="hero-sub">{{ heroSub }}</p>
      <div v-if="hasProfile" class="hero-metrics">
        <div class="metric">
          <span class="metric-value">{{ profile?.bmi ?? "—" }}</span>
          <span class="metric-label">BMI</span>
        </div>
        <div class="metric">
          <span class="metric-value">{{ profile?.suggested_kcal ?? "—" }}</span>
          <span class="metric-label">建议热量（千卡）</span>
        </div>
        <div class="metric">
          <span class="metric-value">{{ profile?.ideal_weight_kg ?? "—" }}</span>
          <span class="metric-label">理想体重（千克）</span>
        </div>
      </div>
      <el-button v-else size="large" round class="hero-btn" @click="go('/profile')">
        去完善健康档案
      </el-button>
    </section>

    <el-card class="checkin">
      <template #header>
        <span class="reminder-header">今日健康打卡</span>
      </template>
      <el-form :inline="true" class="checkin-form">
        <el-form-item label="体重 (kg)">
          <el-input-number
            v-model="checkin.weight_kg"
            :min="20"
            :max="300"
            :precision="1"
            :step="0.5"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="空腹血糖 (mmol/L)">
          <el-input-number
            v-model="checkin.fasting_glucose"
            :min="0.1"
            :max="40"
            :precision="1"
            :step="0.1"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="糖化血红蛋白 (%)">
          <el-input-number
            v-model="checkin.hba1c"
            :min="0.1"
            :max="30"
            :precision="1"
            :step="0.1"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="checkinSaving" @click="submitCheckin">
            保存
          </el-button>
          <el-button link type="primary" @click="go('/health')">查看趋势 →</el-button>
        </el-form-item>
      </el-form>
      <p v-if="checkinMessage" class="checkin-message">{{ checkinMessage }}</p>
    </el-card>

    <section class="quick">
      <div
        v-for="item in quickLinks"
        :key="item.path"
        class="quick-card"
        @click="go(item.path)"
      >
        <span class="quick-icon">{{ item.icon }}</span>
        <span class="quick-title">{{ item.title }}</span>
        <span class="quick-desc">{{ item.desc }}</span>
      </div>
    </section>

    <el-card class="reminder">
      <template #header>
        <span class="reminder-header">冰箱提醒</span>
      </template>
      <div v-loading="reminderLoading">
        <el-alert
          v-if="reminderError"
          type="error"
          :title="reminderError"
          show-icon
          :closable="false"
        />
        <template v-else-if="reminders.length">
          <el-alert
            class="reminder-tip"
            type="warning"
            show-icon
            :closable="false"
            :title="reminderTip"
          />
          <el-table :data="reminders" border>
            <el-table-column prop="food_name" label="食材" />
            <el-table-column label="到期日" width="140">
              <template #default="{ row }">{{ row.expires_at ?? "—" }}</template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <p v-else class="fresh">冰箱里的食材都很新鲜，不用着急。</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { fetchReminders, type InventoryItem } from "../api/inventory";
import { saveMetric } from "../api/metrics";
import { fetchProfile, type ProfileView } from "../api/profile";
import { useUserStore } from "../stores/user";
import { statusLabel, statusType } from "../utils/inventoryStatus";

const router = useRouter();
const user = useUserStore();

const profile = ref<ProfileView | null>(null);
const reminders = ref<InventoryItem[]>([]);
const reminderLoading = ref(true);
const reminderError = ref("");

const quickLinks = [
  { path: "/recommend", icon: "🍽️", title: "今日推荐", desc: "看看今天吃什么" },
  { path: "/chat", icon: "💬", title: "问一问", desc: "饮食疑问随时问" },
  { path: "/fridge", icon: "🧊", title: "我的冰箱", desc: "冰箱里有什么" },
  { path: "/profile", icon: "📋", title: "健康档案", desc: "查看身体状况" },
];

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 6) return "夜深了";
  if (hour < 9) return "早上好";
  if (hour < 12) return "上午好";
  if (hour < 14) return "中午好";
  if (hour < 18) return "下午好";
  return "晚上好";
});

const username = computed(() => user.username || "朋友");

const hasProfile = computed(
  () =>
    profile.value != null &&
    (profile.value.birth_year != null || profile.value.height_cm != null),
);

const heroSub = computed(() =>
  hasProfile.value
    ? "今天也要好好吃饭，我帮您搭配健康的一日三餐。"
    : "填写健康档案后，我会根据您的情况推荐更合适的饭菜。",
);

const reminderTip = computed(
  () => "有 " + reminders.value.length + " 样食材快到期了，记得早点吃。",
);

const checkin = ref({
  weight_kg: undefined as number | undefined,
  fasting_glucose: undefined as number | undefined,
  hba1c: undefined as number | undefined,
});
const checkinSaving = ref(false);
const checkinMessage = ref("");

function shanghaiToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

async function submitCheckin() {
  const payload = {
    date: shanghaiToday(),
    weight_kg: checkin.value.weight_kg ?? null,
    fasting_glucose: checkin.value.fasting_glucose ?? null,
    hba1c: checkin.value.hba1c ?? null,
  };
  if (
    payload.weight_kg == null &&
    payload.fasting_glucose == null &&
    payload.hba1c == null
  ) {
    checkinMessage.value = "请至少填一项";
    return;
  }
  checkinSaving.value = true;
  checkinMessage.value = "";
  try {
    await saveMetric(payload);
    checkinMessage.value = "已保存今天的健康记录";
    checkin.value = {
      weight_kg: undefined,
      fasting_glucose: undefined,
      hba1c: undefined,
    };
  } catch {
    checkinMessage.value = "保存失败，请稍后再试";
  } finally {
    checkinSaving.value = false;
  }
}

function go(path: string) {
  void router.push(path);
}

async function loadReminders() {
  reminderLoading.value = true;
  reminderError.value = "";
  try {
    const { data } = await fetchReminders();
    reminders.value = data;
  } catch {
    reminderError.value = "暂时读不到冰箱信息";
  } finally {
    reminderLoading.value = false;
  }
}

onMounted(() => {
  void loadReminders();
  void (async () => {
    try {
      const { data } = await fetchProfile();
      profile.value = data;
    } catch {
      // 档案读不到不打断首页
    }
  })();
});
</script>

<style scoped>
.home {
  max-width: 960px;
}

.hero {
  padding: 32px 36px;
  border-radius: 16px;
  background: linear-gradient(135deg, #2f7d5b 0%, #45a06f 100%);
  color: #fff;
  margin-bottom: 20px;
  box-shadow: 0 8px 24px rgba(47, 125, 91, 0.25);
}

.hero-greeting {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
}

.hero-sub {
  margin: 0 0 22px;
  font-size: 16px;
  opacity: 0.92;
}

.hero-metrics {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-value {
  font-size: 30px;
  font-weight: 700;
}

.metric-label {
  font-size: 13px;
  opacity: 0.85;
}

.hero-btn {
  background: #fff;
  color: #2f7d5b;
  border: none;
  font-weight: 600;
}

.quick {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.quick-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 24px 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e8efe9;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.quick-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
}

.quick-icon {
  font-size: 32px;
}

.quick-title {
  font-size: 17px;
  font-weight: 600;
  color: #2c3a32;
}

.quick-desc {
  font-size: 13px;
  color: #8a9890;
}

.reminder-header {
  font-weight: 600;
}

.checkin {
  margin-bottom: 20px;
}

.checkin-form {
  align-items: center;
}

.checkin-message {
  margin: 8px 0 0;
  color: #2f7d5b;
}

.reminder-tip {
  margin-bottom: 12px;
}

.fresh {
  margin: 0;
  color: #6b7a72;
  font-size: 15px;
}
</style>

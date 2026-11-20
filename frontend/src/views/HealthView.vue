<template>
  <div>
    <div class="toolbar">
      <el-date-picker
        v-model="range"
        type="daterange"
        value-format="YYYY-MM-DD"
        :clearable="false"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="load"
      />
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-button v-if="error" @click="load">重试</el-button>
    <p v-else-if="loading">加载中</p>

    <template v-else>
      <el-empty v-if="!points.length" description="这段时间还没有健康记录" />
      <template v-else>
        <h3 class="chart-title">体重（kg）</h3>
        <div ref="weightEl" class="chart" />
        <h3 class="chart-title">空腹血糖（mmol/L）</h3>
        <div ref="glucoseEl" class="chart" />
        <h3 class="chart-title">糖化血红蛋白（%）</h3>
        <div ref="hba1cEl" class="chart" />
        <el-table :data="points" border>
          <el-table-column prop="date" label="日期" width="130" />
          <el-table-column label="体重（kg）" width="130">
            <template #default="{ row }">{{ row.weight_kg ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="空腹血糖（mmol/L）" width="170">
            <template #default="{ row }">{{ row.fasting_glucose ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="糖化血红蛋白（%）" width="170">
            <template #default="{ row }">{{ row.hba1c ?? "—" }}</template>
          </el-table-column>
        </el-table>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";

import { fetchMetrics, type MetricPoint } from "../api/metrics";

interface Chart {
  setOption: (option: object) => void;
  dispose: () => void;
}

type MetricKey = "weight_kg" | "fasting_glucose" | "hba1c";

const range = ref<[string, string]>([daysAgo(29), shanghaiToday()]);
const loading = ref(false);
const error = ref("");
const points = ref<MetricPoint[]>([]);
const weightEl = ref<HTMLDivElement | null>(null);
const glucoseEl = ref<HTMLDivElement | null>(null);
const hba1cEl = ref<HTMLDivElement | null>(null);
const charts = shallowRef<Chart[]>([]);

function formatDate(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

function shanghaiToday(): string {
  return formatDate(new Date());
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return formatDate(d);
}

function clearCharts() {
  for (const chart of charts.value) {
    chart.dispose();
  }
  charts.value = [];
}

async function paint() {
  clearCharts();
  await nextTick();
  const echarts = await import("echarts");
  const next: Chart[] = [];
  const dates = points.value.map((item) => item.date);
  const specs: { el: HTMLDivElement | null; key: MetricKey; title: string }[] = [
    { el: weightEl.value, key: "weight_kg", title: "体重" },
    { el: glucoseEl.value, key: "fasting_glucose", title: "空腹血糖" },
    { el: hba1cEl.value, key: "hba1c", title: "糖化血红蛋白" },
  ];
  for (const spec of specs) {
    if (!spec.el) {
      continue;
    }
    const chart = echarts.init(spec.el);
    chart.setOption({
      xAxis: { type: "category", data: dates },
      yAxis: { type: "value", scale: true },
      series: [
        {
          name: spec.title,
          type: "line",
          connectNulls: false,
          data: points.value.map((item) => item[spec.key]),
        },
      ],
    });
    next.push(chart);
  }
  charts.value = next;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [start, end] = range.value;
    const response = await fetchMetrics(start, end);
    points.value = response.data.points;
    loading.value = false;
    await paint();
  } catch {
    loading.value = false;
    error.value = "健康记录加载失败";
  }
}

onMounted(() => {
  void load();
});

onBeforeUnmount(() => {
  clearCharts();
});
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.chart {
  width: 100%;
  height: 260px;
  margin-bottom: 12px;
}

.chart-title {
  margin: 8px 0;
}
</style>

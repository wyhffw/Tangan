<template>
  <div>
    <div class="toolbar">
      <el-input v-model="name" placeholder="食材或疾病，例如荞麦、2型糖尿病" @keyup.enter="search" />
      <el-radio-group v-model="depth">
        <el-radio :value="1">一度</el-radio>
        <el-radio :value="2">二度</el-radio>
      </el-radio-group>
      <el-button type="primary" :disabled="loading" @click="search">查询</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-button v-if="error" @click="search">重试</el-button>
    <p v-else-if="loading">加载中</p>

    <template v-else-if="result">
      <el-alert
        v-if="result.graph !== 'up'"
        title="图谱暂时不可用"
        type="info"
        show-icon
        :closable="false"
      />
      <el-empty v-else-if="result.nodes.length === 0" description="没有找到这个食材或疾病" />
      <template v-else>
        <div ref="chartEl" class="chart" />
        <ul class="links">
          <li v-for="(link, index) in result.links" :key="index">
            <button type="button" @click="openNode(link.source)">{{ nodeName(link.source) }}</button>
            {{ relationText(link.relation) }}
            <button type="button" @click="openNode(link.target)">{{ nodeName(link.target) }}</button>
            <span v-if="link.citation" class="citation">{{ link.citation }}</span>
          </li>
        </ul>
      </template>
      <section v-if="facts" class="facts">
        <h3>{{ facts.name }}</h3>
        <p>数字来自成分表，不写在图谱节点上。</p>
        <p>GI {{ facts.gi == null ? "—" : facts.gi }}（{{ facts.gi_source }}）</p>
        <p>每 {{ facts.per_g ?? "—" }} 克：热量 {{ amount(facts.kcal) }} kcal，碳水 {{ amount(facts.carb_g) }} g</p>
        <p>蛋白质 {{ amount(facts.protein_g) }} g，脂肪 {{ amount(facts.fat_g) }} g，膳食纤维 {{ amount(facts.fiber_g) }} g</p>
        <p>钠 {{ amount(facts.sodium_mg) }} mg。营养来源：{{ facts.nutrient_source }}</p>
      </section>
      <p v-else-if="factsNote">{{ factsNote }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, shallowRef } from "vue";
import type { EChartsType } from "echarts";

import {
  fetchFoodFacts,
  fetchNeighbors,
  type FoodFacts,
  type GraphNode,
  type Neighborhood,
} from "../api/graph";

const labelNames: Record<string, string> = {
  Food: "食材",
  Disease: "疾病",
  Recipe: "食谱",
  CookingMethod: "做法",
  Nutrient: "营养素",
};

const relationNames: Record<string, string> = {
  RECOMMEND: "推荐",
  AVOID: "避免",
  LIMIT: "限量",
  CONTAINS: "含有",
  COOKED_BY: "做法",
  AVOID_METHOD: "避免做法",
  SUBSTITUTE: "可替换",
};

const categoryColors = ["#2f7d4a", "#c45656", "#3a7ca5", "#c48a2a", "#6b5b95"];

const name = ref("");
const depth = ref(2);
const loading = ref(false);
const error = ref("");
const result = ref<Neighborhood | null>(null);
const facts = ref<FoodFacts | null>(null);
const factsNote = ref("");
const chartEl = ref<HTMLDivElement | null>(null);
const chart = shallowRef<EChartsType | null>(null);
let ticket = 0;

function amount(value: number | null): string {
  if (value == null) {
    return "—";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function relationText(relation: string): string {
  return relationNames[relation] ?? relation;
}

function nodeName(id: string): string {
  return result.value?.nodes.find((item) => item.id === id)?.name ?? id;
}

function openNode(id: string) {
  const node = result.value?.nodes.find((item) => item.id === id);
  if (!node) {
    return;
  }
  void loadFacts(node);
}

async function loadFacts(node: GraphNode) {
  facts.value = null;
  factsNote.value = "";
  if (node.label !== "Food") {
    factsNote.value = `${node.name}不是食材，这里不显示营养数字。`;
    return;
  }
  if (node.pg_id == null) {
    factsNote.value = "图谱里没有对应的成分表编号，不显示营养数字。";
    return;
  }
  try {
    const response = await fetchFoodFacts(node.pg_id);
    facts.value = response.data;
  } catch {
    factsNote.value = "成分表暂时读不出来。";
  }
}

async function paint() {
  chart.value?.dispose();
  chart.value = null;
  await nextTick();
  if (!chartEl.value || !result.value || result.value.graph !== "up" || result.value.nodes.length === 0) {
    return;
  }
  const echarts = await import("echarts");
  const categories = Object.values(labelNames);
  const instance = echarts.init(chartEl.value);
  instance.setOption({
    tooltip: {},
    legend: [{ data: categories }],
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        categories: categories.map((item, index) => ({
          name: item,
          itemStyle: { color: categoryColors[index] },
        })),
        data: result.value.nodes.map((node) => ({
          id: node.id,
          name: node.name,
          category: Math.max(Object.keys(labelNames).indexOf(node.label), 0),
          label: node.label,
          pg_id: node.pg_id,
        })),
        links: result.value.links.map((link) => ({
          source: link.source,
          target: link.target,
        })),
        force: { repulsion: 220, edgeLength: 110 },
      },
    ],
  });
  instance.on("click", (params) => {
    if (params.dataType !== "node" || !params.data) {
      return;
    }
    void loadFacts(params.data as unknown as GraphNode);
  });
  chart.value = instance;
}

async function search() {
  const current = ++ticket;
  const selectedName = name.value.trim();
  const selectedDepth = depth.value;
  if (!selectedName) {
    error.value = "请输入食材或疾病";
    return;
  }
  loading.value = true;
  error.value = "";
  facts.value = null;
  factsNote.value = "";
  try {
    const response = await fetchNeighbors(selectedName, selectedDepth);
    if (current !== ticket) {
      return;
    }
    result.value = response.data;
    loading.value = false;
    await paint();
  } catch {
    if (current !== ticket) {
      return;
    }
    error.value = "图谱查询失败";
    loading.value = false;
  }
}

onBeforeUnmount(() => {
  chart.value?.dispose();
});
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar .el-input {
  max-width: 320px;
}

.chart {
  width: 100%;
  height: 480px;
}

.links {
  padding-left: 18px;
}

.links button {
  border: 0;
  background: transparent;
  color: #1f6b3a;
  cursor: pointer;
}

.citation,
.facts p {
  color: #5c6b62;
}

.facts {
  margin-top: 12px;
}
</style>

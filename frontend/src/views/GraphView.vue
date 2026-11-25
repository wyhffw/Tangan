<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="name"
        class="search-input"
        placeholder="输入疾病，例如 2型糖尿病"
        clearable
        @keyup.enter="search"
      />
      <el-button type="primary" :disabled="loading" @click="search">查询</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="block" />
    <p v-if="loading" class="hint">加载中…</p>

    <template v-else-if="guidance">
      <el-alert
        v-if="guidance.graph !== 'up'"
        title="图谱暂时不可用"
        type="info"
        show-icon
        :closable="false"
        class="block"
      />

      <template v-else-if="guidance.disease">
        <h2 class="disease-name">{{ guidance.disease }} · 饮食指导</h2>

        <el-card v-if="guidance.notes.length" class="block" shadow="never">
          <template #header><span class="card-title">注意事项</span></template>
          <ol class="notes">
            <li v-for="(note, index) in guidance.notes" :key="index">{{ note.note }}</li>
          </ol>
        </el-card>

        <div class="grid">
          <el-card class="col" shadow="never">
            <template #header><span class="card-title good">该吃</span></template>
            <div v-if="guidance.recommended.length" class="tag-cloud">
              <el-tag v-for="food in guidance.recommended" :key="food.name" type="success" effect="plain">
                {{ food.name }}
              </el-tag>
            </div>
            <el-empty v-else description="暂无" :image-size="50" />
          </el-card>

          <el-card class="col" shadow="never">
            <template #header><span class="card-title bad">不该吃</span></template>
            <div v-if="guidance.avoided.length" class="tag-cloud">
              <el-tag v-for="food in guidance.avoided" :key="food.name" type="danger" effect="plain">
                {{ food.name }}
              </el-tag>
            </div>
            <el-empty v-else description="暂无" :image-size="50" />
          </el-card>
        </div>

        <el-card v-if="guidance.limits.length" class="block" shadow="never">
          <template #header><span class="card-title">要限量</span></template>
          <ul class="limit-list">
            <li v-for="limit in guidance.limits" :key="limit.name">
              <span class="limit-name">{{ limit.name }}</span>
              <el-tag v-if="limit.max_per_day != null" type="warning" effect="plain">
                每天不超过 {{ limit.max_per_day }} {{ limit.unit }}
              </el-tag>
              <el-tag v-else type="warning" effect="plain">尽量少吃</el-tag>
            </li>
          </ul>
        </el-card>

        <el-card v-if="guidance.avoided_methods.length" class="block" shadow="never">
          <template #header><span class="card-title">避免的做法</span></template>
          <div class="tag-cloud">
            <el-tag v-for="method in guidance.avoided_methods" :key="method.name" type="info" effect="plain">
              {{ method.name }}
            </el-tag>
          </div>
        </el-card>

        <p class="disclaimer">内容依据成人糖尿病食养指南（2023年版）整理，仅供参考，不构成医疗建议。</p>
      </template>

      <template v-else-if="neighbors && neighbors.center">
        <h2 class="disease-name">{{ neighbors.center.name }} · 相关关系</h2>
        <el-card class="block" shadow="never">
          <ul v-if="neighbors.links.length" class="relation-list">
            <li v-for="(link, index) in neighbors.links" :key="index">
              <span class="rel-name">{{ nodeName(link.source) }}</span>
              <el-tag size="small" effect="plain">{{ relationText(link.relation) }}</el-tag>
              <span class="rel-name">{{ nodeName(link.target) }}</span>
            </li>
          </ul>
          <el-empty v-else description="这个食材暂时没有图谱关系" :image-size="50" />
        </el-card>
      </template>

      <el-empty v-else description="没找到这个疾病或食材的指导信息" class="block" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  fetchGuidance,
  fetchNeighbors,
  type DiseaseGuidance,
  type Neighborhood,
} from "../api/graph";

const relationNames: Record<string, string> = {
  RECOMMEND: "推荐",
  AVOID: "避免",
  LIMIT: "限量",
  CONTAINS: "含有",
  COOKED_BY: "做法",
  AVOID_METHOD: "避免做法",
  SUBSTITUTE: "可替换",
};

const name = ref("2型糖尿病");
const loading = ref(false);
const error = ref("");
const guidance = ref<DiseaseGuidance | null>(null);
const neighbors = ref<Neighborhood | null>(null);

function relationText(relation: string): string {
  return relationNames[relation] ?? relation;
}

function nodeName(id: string): string {
  return neighbors.value?.nodes.find((item) => item.id === id)?.name ?? id;
}

async function search() {
  const query = name.value.trim();
  if (!query) {
    error.value = "请输入疾病或食材";
    return;
  }
  loading.value = true;
  error.value = "";
  guidance.value = null;
  neighbors.value = null;
  try {
    const response = await fetchGuidance(query);
    guidance.value = response.data;
    if (response.data.graph === "up" && !response.data.disease) {
      const neighborResponse = await fetchNeighbors(query, 1);
      neighbors.value = neighborResponse.data;
    }
  } catch {
    error.value = "查询失败，请重试";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.page {
  max-width: 960px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  max-width: 360px;
}

.block {
  margin-bottom: 16px;
}

.hint {
  color: #5c6b62;
}

.disease-name {
  margin: 0 0 16px;
  font-size: 22px;
}

.card-title {
  font-weight: 600;
}

.card-title.good {
  color: #2f7d4a;
}

.card-title.bad {
  color: #c45656;
}

.notes {
  margin: 0;
  padding-left: 20px;
  line-height: 1.9;
  color: #2b3a31;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.col {
  margin-bottom: 16px;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.limit-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.limit-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f3f1;
}

.limit-list li:last-child {
  border-bottom: 0;
}

.limit-name {
  font-weight: 600;
  min-width: 72px;
}

.relation-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.relation-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.rel-name {
  font-weight: 500;
}

.disclaimer {
  color: #8a9a90;
  font-size: 13px;
}
</style>

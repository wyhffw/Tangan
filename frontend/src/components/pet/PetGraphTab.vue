<template>
  <div class="graph-tab">
    <div class="toolbar">
      <el-input
        v-model="name"
        placeholder="输入疾病或食材，如 2型糖尿病"
        clearable
        @keyup.enter="search"
      />
      <el-button type="primary" :disabled="loading" @click="search">查询</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <p v-if="loading" class="hint">加载中…</p>

    <div v-else-if="guidance?.disease" class="result">
      <h4>{{ guidance.disease }} · 饮食指导</h4>
      <div v-if="guidance.notes.length">
        <p class="sub">注意事项</p>
        <ol class="notes">
          <li v-for="(note, index) in guidance.notes" :key="index">{{ note.note }}</li>
        </ol>
      </div>
      <p v-if="guidance.recommended.length" class="sub good">该吃</p>
      <div v-if="guidance.recommended.length" class="tags">
        <el-tag v-for="food in guidance.recommended" :key="food.name" type="success" effect="plain">
          {{ food.name }}
        </el-tag>
      </div>
      <p v-if="guidance.avoided.length" class="sub bad">不该吃</p>
      <div v-if="guidance.avoided.length" class="tags">
        <el-tag v-for="food in guidance.avoided" :key="food.name" type="danger" effect="plain">
          {{ food.name }}
        </el-tag>
      </div>
      <p v-if="guidance.limits.length" class="sub warn">要限量</p>
      <ul v-if="guidance.limits.length" class="limits">
        <li v-for="limit in guidance.limits" :key="limit.name">
          {{ limit.name }}：{{ limit.max_per_day != null ? `每天不超过 ${limit.max_per_day} ${limit.unit}` : "尽量少吃" }}
        </li>
      </ul>
    </div>

    <div v-else-if="neighbors?.center" class="result">
      <h4>{{ neighbors.center.name }} · 相关关系</h4>
      <ul v-if="neighbors.links.length" class="links">
        <li v-for="(link, index) in neighbors.links" :key="index">
          {{ nodeName(link.source) }}
          <el-tag size="small" effect="plain">{{ relationText(link.relation) }}</el-tag>
          {{ nodeName(link.target) }}
        </li>
      </ul>
      <el-empty v-else description="暂无图谱关系" :image-size="50" />
    </div>

    <el-empty v-else description="输入疾病或食材查询饮食指导" :image-size="60" />
    <p class="disclaimer">内容依据成人糖尿病食养指南（2023年版）整理，仅供参考。</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  fetchGuidance,
  fetchNeighbors,
  type DiseaseGuidance,
  type Neighborhood,
} from "../../api/graph";

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
.graph-tab {
  height: 100%;
  overflow-y: auto;
}

.toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.hint {
  color: #5c6b62;
}

.result h4 {
  margin: 4px 0 8px;
  font-size: 15px;
}

.sub {
  margin: 8px 0 4px;
  font-size: 13px;
  font-weight: 600;
}

.sub.good {
  color: #2f7d4a;
}

.sub.bad {
  color: #c45656;
}

.sub.warn {
  color: #b8860b;
}

.notes {
  margin: 0;
  padding-left: 18px;
  line-height: 1.7;
  color: #2b3a31;
  font-size: 13px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.limits,
.links {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 13px;
}

.limits li,
.links li {
  padding: 4px 0;
}

.disclaimer {
  color: #8a9a90;
  font-size: 12px;
  margin-top: 8px;
}
</style>


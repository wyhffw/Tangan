<template>
  <div class="llm-tab">
    <el-alert :type="configured ? 'success' : 'warning'" :title="statusText" show-icon :closable="false" />

    <div class="field">
      <label>服务商</label>
      <el-radio-group v-model="form.provider" size="small" @change="onProviderChange">
        <el-radio-button value="deepseek">DeepSeek</el-radio-button>
        <el-radio-button value="qwen">通义千问</el-radio-button>
        <el-radio-button value="ollama">本地 Ollama</el-radio-button>
      </el-radio-group>
      <p class="tip">{{ providerHint }}</p>
    </div>

    <div v-if="form.provider !== 'ollama'" class="field">
      <label>API Key</label>
      <el-input
        v-model="form.api_key"
        type="password"
        show-password
        size="small"
        placeholder="粘贴 API Key（一般 sk- 开头）"
        clearable
      />
    </div>

    <div class="field">
      <label>模型名称（可选）</label>
      <el-input v-model="form.model" size="small" placeholder="留空用默认模型" />
    </div>

    <div class="field">
      <label>接口地址（可选）</label>
      <el-input v-model="form.base_url" size="small" placeholder="留空用默认地址" />
    </div>

    <div class="actions">
      <el-button size="small" type="primary" :loading="testing" @click="test">测试连接</el-button>
      <el-button size="small" type="success" :loading="saving" @click="save">保存</el-button>
    </div>

    <el-alert
      v-if="result.message"
      :type="result.ok ? 'success' : 'error'"
      :title="result.message"
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { fetchLlmConfig, saveLlmConfig, testLlmConfig } from "../../api/llm";

const providerHints: Record<string, string> = {
  deepseek: "DeepSeek：platform.deepseek.com 注册后在「API Keys」创建 Key。",
  qwen: "通义千问：百炼平台 bailian.console.aliyun.com 创建 API-KEY。",
  ollama: "使用服务器本地 Ollama 模型，无需 API Key。未配置云端时也会自动用它兜底。",
};

const form = reactive({
  provider: "deepseek",
  api_key: "",
  model: "",
  base_url: "",
});
const configured = ref(false);
const statusText = ref("");
const providerHint = ref(providerHints.deepseek);
const testing = ref(false);
const saving = ref(false);
const result = reactive({ ok: false, message: "" });

async function load() {
  try {
    const { data } = await fetchLlmConfig();
    form.provider = data.provider;
    form.model = data.model;
    form.base_url = data.base_url;
    form.api_key = "";
    configured.value = data.configured;
    providerHint.value = providerHints[data.provider] ?? "";
    statusText.value = data.configured
      ? "已接入，当前模型 " + (data.model || "默认")
      : "还没有接入云端大模型，问答会尝试用本地 Ollama。";
  } catch {
    statusText.value = "暂时读不到配置，请稍后再试。";
  }
}

function onProviderChange(value: string | number | boolean | undefined) {
  form.provider = String(value ?? "deepseek");
  providerHint.value = providerHints[form.provider] ?? "";
  form.model = "";
  form.base_url = "";
}

async function test() {
  testing.value = true;
  result.message = "";
  try {
    const { data } = await testLlmConfig({ ...form });
    result.ok = data.ok;
    result.message = data.message;
  } catch {
    result.ok = false;
    result.message = "测试失败，请检查网络，或稍后再试。";
  } finally {
    testing.value = false;
  }
}

async function save() {
  saving.value = true;
  result.message = "";
  try {
    const { data } = await saveLlmConfig({ ...form });
    configured.value = data.configured;
    statusText.value = data.configured
      ? "已接入，当前模型 " + (data.model || "默认")
      : "还没有接入";
    result.ok = true;
    result.message = "保存成功";
    form.api_key = "";
  } catch {
    result.ok = false;
    result.message = "保存失败，请稍后再试。";
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.llm-tab {
  height: 100%;
  overflow-y: auto;
}

.field {
  margin: 12px 0;
}

.field label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #2b3a31;
}

.tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: #6b7a72;
  line-height: 1.5;
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>


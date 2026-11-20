<template>
  <div class="llm-config">
    <el-card class="intro">
      <h2 class="intro-title">接入 AI 大模型</h2>
      <p class="intro-lead">
        只要填一次 API Key，「问答」就能给出更聪明、更自然的回答。
        整个过程三步，照着做就行。
      </p>
      <el-alert
        v-if="statusText"
        :type="configured ? 'success' : 'warning'"
        :title="statusText"
        show-icon
        :closable="false"
      />
    </el-card>

    <el-card>
      <template #header>
        <span class="step">第 1 步</span> 选择服务商
      </template>
      <el-radio-group v-model="form.provider" size="large" @change="onProviderChange">
        <el-radio-button value="deepseek">DeepSeek</el-radio-button>
        <el-radio-button value="qwen">通义千问</el-radio-button>
      </el-radio-group>
      <p class="tip">{{ providerHint }}</p>
    </el-card>

    <el-card>
      <template #header>
        <span class="step">第 2 步</span> 填写 API Key
      </template>
      <el-input
        v-model="form.api_key"
        type="password"
        show-password
        size="large"
        placeholder="粘贴你的 API Key（一般是 sk- 开头）"
        clearable
      />
      <p class="tip">Key 只保存在你自己的服务器上，不会上传到别的地方。</p>
    </el-card>

    <el-card>
      <template #header>
        <span class="step">第 3 步</span> 测试并保存
      </template>
      <div class="actions">
        <el-button type="primary" size="large" :loading="testing" @click="test">
          测试连接
        </el-button>
        <el-button type="success" size="large" :loading="saving" @click="save">
          保存
        </el-button>
      </div>
      <el-alert
        v-if="result.message"
        :type="result.ok ? 'success' : 'error'"
        :title="result.message"
        show-icon
        :closable="false"
        class="result"
      />
    </el-card>

    <el-collapse>
      <el-collapse-item title="高级设置（一般不用改）" name="advanced">
        <el-form label-width="110px">
          <el-form-item label="模型名称">
            <el-input v-model="form.model" placeholder="留空会自动填默认模型" />
          </el-form-item>
          <el-form-item label="接口地址">
            <el-input v-model="form.base_url" placeholder="留空会自动填默认地址" />
          </el-form-item>
        </el-form>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { fetchLlmConfig, saveLlmConfig, testLlmConfig } from "../api/llm";

const providerHints: Record<string, string> = {
  deepseek:
    "DeepSeek（深度求索）：打开 platform.deepseek.com 注册后，在「API Keys」里创建一个 Key。",
  qwen:
    "通义千问（阿里云）：打开百炼平台 bailian.console.aliyun.com 开通后，在「API-KEY」里创建一个 Key。",
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
      ? "已接入，当前 Key 显示为 " + data.api_key_masked
      : "还没有接入，按下面三步填写即可。";
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
      ? "已接入，当前 Key 显示为 " + data.api_key_masked
      : "还没有接入";
    result.ok = true;
    result.message = "保存成功";
    form.api_key = "";
    ElMessage.success("已保存");
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
.llm-config {
  max-width: 720px;
}

.intro {
  margin-bottom: 16px;
}

.intro-title {
  margin: 0 0 8px;
  font-size: 24px;
}

.intro-lead {
  margin: 0 0 16px;
  font-size: 16px;
  color: #3c4a42;
  line-height: 1.7;
}

.step {
  display: inline-block;
  margin-right: 8px;
  padding: 2px 10px;
  border-radius: 12px;
  background: #2f7d5b;
  color: #fff;
  font-size: 14px;
}

.tip {
  margin: 12px 0 0;
  font-size: 15px;
  color: #6b7a72;
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 12px;
}

.result {
  margin-top: 14px;
}

.llm-config :deep(.el-card) {
  margin-bottom: 16px;
}

.llm-config :deep(.el-radio-button) {
  font-size: 16px;
}
</style>



<template>
  <div class="forward-page">
    <h2 class="page-title">转发给家人</h2>
    <p class="page-desc">
      把每日饮食报告发到家人邮箱，方便他们随时了解饮食情况。
      系统每天 20:00 自动发送，也可以在这里手动立即发送。
    </p>

    <el-card class="block">
      <template #header>
        <span class="block-header">收件邮箱</span>
      </template>
      <div class="forward-form">
        <el-input
          v-model="newEmail"
          placeholder="家人邮箱，如 parent@qq.com"
          clearable
          @keyup.enter="addEmail"
        />
        <el-button type="primary" :loading="adding" @click="addEmail">添加</el-button>
      </div>
      <ul v-if="recipients.length" class="recipients">
        <li v-for="item in recipients" :key="item.id">
          <span>{{ item.email }}</span>
          <el-button link type="danger" @click="removeEmail(item.id)">删除</el-button>
        </li>
      </ul>
      <el-empty v-else description="还没有配置收件邮箱" :image-size="60" />
    </el-card>

    <el-card class="block">
      <template #header>
        <span class="block-header">发送</span>
      </template>
      <p class="send-hint">立即把今天的饮食报告发到上面所有邮箱。</p>
      <el-button
        type="success"
        :loading="sending"
        :disabled="!recipients.length"
        @click="sendNow"
      >
        立即发送今日报告
      </el-button>
      <el-alert
        v-if="message"
        class="message"
        :title="message"
        :type="isError ? 'error' : 'success'"
        show-icon
        :closable="false"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import {
  addRecipient,
  deleteRecipient,
  fetchRecipients,
  sendDaily,
  type Recipient,
} from "../api/reports";

const newEmail = ref("");
const recipients = ref<Recipient[]>([]);
const adding = ref(false);
const sending = ref(false);
const message = ref("");
const isError = ref(false);

function shanghaiToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function extractError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}

async function loadRecipients() {
  try {
    const response = await fetchRecipients();
    recipients.value = response.data;
  } catch (error) {
    message.value = extractError(error, "读取收件邮箱失败");
    isError.value = true;
  }
}

async function addEmail() {
  const email = newEmail.value.trim();
  if (!email) {
    return;
  }
  adding.value = true;
  message.value = "";
  try {
    const response = await addRecipient(email);
    newEmail.value = "";
    if (!recipients.value.some((item) => item.id === response.data.id)) {
      recipients.value.push(response.data);
    }
    message.value = "已添加收件邮箱";
    isError.value = false;
  } catch (error) {
    message.value = extractError(error, "添加失败");
    isError.value = true;
  } finally {
    adding.value = false;
  }
}

async function removeEmail(id: number) {
  try {
    await deleteRecipient(id);
    recipients.value = recipients.value.filter((item) => item.id !== id);
    message.value = "已删除收件邮箱";
    isError.value = false;
  } catch (error) {
    message.value = extractError(error, "删除失败");
    isError.value = true;
  }
}

async function sendNow() {
  sending.value = true;
  message.value = "";
  try {
    const response = await sendDaily(shanghaiToday());
    message.value = `已发送给 ${response.data.recipients.length} 个邮箱`;
    isError.value = false;
  } catch (error) {
    message.value = extractError(error, "发送失败");
    isError.value = true;
  } finally {
    sending.value = false;
  }
}

onMounted(() => {
  void loadRecipients();
});
</script>

<style scoped>
.forward-page {
  max-width: 720px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 22px;
  color: #2c3a32;
}

.page-desc {
  margin: 0 0 20px;
  color: #6b7a72;
  font-size: 14px;
  line-height: 1.6;
}

.block {
  margin-bottom: 20px;
}

.block-header {
  font-weight: 600;
}

.forward-form {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.forward-form .el-input {
  max-width: 360px;
}

.recipients {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recipients li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f0;
}

.send-hint {
  margin: 0 0 12px;
  color: #6b7a72;
  font-size: 14px;
}

.message {
  margin-top: 12px;
}
</style>

<template>
  <div class="chat-tab">
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <div class="messages">
      <el-empty
        v-if="messages.length === 0"
        description="问饮食知识、今日推荐或本周报告"
        :image-size="60"
      />
      <div v-for="(item, index) in messages" :key="index" class="msg" :class="item.role">
        <div class="body" v-html="render(item.content)" />
        <div v-if="item.pending" class="pending">
          <span>确认后才会写入档案。</span>
          <div class="pending-actions">
            <el-button size="small" type="primary" :disabled="sending" @click="confirmDraft">确认</el-button>
            <el-button size="small" :disabled="sending" @click="cancelDraft">取消</el-button>
          </div>
        </div>
      </div>
    </div>
    <form class="composer" @submit.prevent="send">
      <el-input v-model="draft" placeholder="例如：糖尿病能吃西瓜吗" :disabled="sending" />
      <el-button type="primary" native-type="submit" :disabled="sending || !draft.trim()">发送</el-button>
    </form>
  </div>
</template>

<script setup lang="ts">
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import { ref } from "vue";
import { useRouter } from "vue-router";

import { streamChat } from "../../api/chat";
import { useUserStore } from "../../stores/user";

interface Line {
  role: "user" | "assistant";
  content: string;
  pending: boolean;
}

const markdown = new MarkdownIt({ html: false, linkify: true });
const sessionId = ref<number | null>(null);
const messages = ref<Line[]>([]);
const draft = ref("");
const sending = ref(false);
const error = ref("");
const router = useRouter();
const user = useUserStore();

function render(text: string) {
  return DOMPurify.sanitize(markdown.render(text));
}

function send() {
  void sendText(draft.value.trim());
}

function confirmDraft() {
  void sendText("确认");
}

function cancelDraft() {
  void sendText("取消");
}

async function sendText(text: string) {
  if (!text || sending.value) {
    return;
  }
  error.value = "";
  sending.value = true;
  messages.value.push({ role: "user", content: text, pending: false });
  const reply: Line = { role: "assistant", content: "", pending: false };
  messages.value.push(reply);
  draft.value = "";
  try {
    await streamChat(text, sessionId.value, {
      onToken(chunk) {
        reply.content += chunk;
      },
      onSources() {},
      onPending() {
        reply.pending = true;
      },
      onDone(id) {
        sessionId.value = id;
      },
    });
  } catch (caught) {
    if (caught instanceof Error && caught.message === "unauthorized") {
      user.logout();
      void router.push("/login");
      return;
    }
    error.value = "暂时无法回答，请稍后重试。";
    messages.value = messages.value.filter((item) => item !== reply);
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.chat-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 4px 2px;
}

.msg {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f6f8f6;
  margin-bottom: 8px;
  font-size: 13px;
}

.msg.user {
  background: #e8f2eb;
}

.body :deep(p) {
  margin: 0 0 6px;
}

.pending {
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fdf6ec;
  color: #7a5b2e;
  font-size: 12px;
}

.pending-actions {
  margin-top: 6px;
}

.composer {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
</style>


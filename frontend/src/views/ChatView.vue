<template>
  <div class="chat">
    <aside class="sessions">
      <el-button @click="startNew">新对话</el-button>
      <button
        v-for="item in sessions"
        :key="item.id"
        type="button"
        class="session"
        :class="{ active: sessionId === item.id }"
        @click="openSession(item.id)"
      >
        {{ item.preview }}
      </button>
    </aside>
    <section class="thread">
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
      <el-empty v-if="messages.length === 0" description="问饮食知识、今日推荐或本周报告" />
      <article v-for="(item, index) in messages" :key="index" class="message" :class="item.role">
        <div class="body" v-html="render(item.content)" />
        <el-collapse v-if="item.sources.length">
          <el-collapse-item title="引用">
            <p v-for="source in item.sources" :key="source.chunk_id">
              {{ source.source }} 第 {{ source.page }} 页（{{ source.chunk_id }}）
            </p>
          </el-collapse-item>
        </el-collapse>
        <div v-if="item.pending" class="pending-card">
          <p class="pending-title">这些信息还没有写入档案，确认后才会保存。</p>
          <p v-if="item.draft?.allergies?.length">过敏原：{{ item.draft.allergies.join("、") }}</p>
          <p v-if="item.draft?.dislikes?.length">不吃：{{ item.draft.dislikes.join("、") }}</p>
          <div class="pending-actions">
            <el-button size="small" type="primary" :disabled="sending" @click="confirmDraft">确认</el-button>
            <el-button size="small" :disabled="sending" @click="cancelDraft">取消</el-button>
          </div>
        </div>
      </article>
      <form class="composer" @submit.prevent="send">
        <el-input v-model="draft" placeholder="例如：糖尿病能吃西瓜吗" :disabled="sending" />
        <el-button type="primary" native-type="submit" :disabled="sending || !draft.trim()">发送</el-button>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { fetchSession, fetchSessions, streamChat, type ChatSessionSummary, type ChatSource } from "../api/chat";
import { useUserStore } from "../stores/user";

interface Line {
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[];
  pending: boolean;
  draft: { allergies?: string[]; dislikes?: string[] } | null;
}

const markdown = new MarkdownIt({ html: false, linkify: true });
const sessions = ref<ChatSessionSummary[]>([]);
const sessionId = ref<number | null>(null);
const messages = ref<Line[]>([]);
const draft = ref("");
const sending = ref(false);
const error = ref("");
const router = useRouter();
const user = useUserStore();

onMounted(() => {
  void loadSessions();
});

function render(text: string) {
  return DOMPurify.sanitize(markdown.render(text));
}

async function loadSessions() {
  const { data } = await fetchSessions();
  sessions.value = data;
}

function startNew() {
  sessionId.value = null;
  messages.value = [];
}

async function openSession(id: number) {
  sessionId.value = id;
  const { data } = await fetchSession(id);
  messages.value = data.messages.map((item) => ({
    role: item.role === "assistant" ? "assistant" : "user",
    content: item.content,
    sources: item.meta.sources ?? [],
    pending: item.meta.pending_profile_id != null,
    draft: item.meta.draft ?? null,
  }));
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
  messages.value.push({ role: "user", content: text, sources: [], pending: false, draft: null });
  const reply: Line = { role: "assistant", content: "", sources: [], pending: false, draft: null };
  messages.value.push(reply);
  draft.value = "";
  try {
    await streamChat(text, sessionId.value, {
      onToken(chunk) {
        reply.content += chunk;
      },
      onSources(items) {
        reply.sources = items;
      },
      onPending(_pendingId, itemDraft) {
        reply.pending = true;
        reply.draft = itemDraft;
      },
      onDone(id) {
        sessionId.value = id;
      },
    });
    await loadSessions();
  } catch (caught) {
    if (caught instanceof Error && caught.message === "unauthorized") {
      user.logout();
      void router.push({ path: "/login", query: { redirect: "/chat" } });
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
.chat {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  min-height: 480px;
}

.sessions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session {
  text-align: left;
  border: 1px solid #d9e4dc;
  background: #fff;
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
}

.session.active {
  border-color: #2f7d4a;
}

.thread {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  padding: 12px;
  border-radius: 8px;
  background: #f6f8f6;
}

.message.user {
  background: #e8f2eb;
}

.body :deep(p) {
  margin: 0 0 8px;
}

.composer {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.pending-card {
  border: 1px solid #d9b38c;
  background: #fdf6ec;
  border-radius: 8px;
  padding: 10px 12px;
}

.pending-title {
  margin: 0 0 6px;
  font-weight: 600;
}

.pending-card p {
  margin: 0 0 4px;
}

.pending-actions {
  margin-top: 8px;
}
</style>

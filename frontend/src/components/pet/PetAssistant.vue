<template>
  <div class="pet-root">
    <button v-if="!assistant.visible && !assistant.hidden" class="pet-avatar" type="button" @click="assistant.open()">
      <span class="pet-emoji">🐱</span>
      <span class="pet-label">智能助手</span>
    </button>

    <div
      v-if="assistant.visible"
      ref="winEl"
      class="pet-window"
      :style="{ left: pos.x + 'px', top: pos.y + 'px' }"
    >
      <div class="pet-header" @pointerdown="startDrag">
        <span class="pet-title">🐱 智能助手</span>
        <div class="pet-tabs">
          <button
            type="button"
            :class="{ active: assistant.tab === 'chat' }"
            @click="assistant.setTab('chat')"
          >
            问答
          </button>
          <button
            type="button"
            :class="{ active: assistant.tab === 'graph' }"
            @click="assistant.setTab('graph')"
          >
            知识图谱
          </button>
          <button
            type="button"
            :class="{ active: assistant.tab === 'llm' }"
            @click="assistant.setTab('llm')"
          >
            大模型设置
          </button>
        </div>
        <div class="pet-actions">
          <button type="button" title="最小化" @click="assistant.minimize()">—</button>
          <button type="button" title="关闭" @click="assistant.close()">×</button>
        </div>
      </div>

      <div class="pet-body">
        <PetChatTab v-if="assistant.tab === 'chat'" />
        <PetGraphTab v-else-if="assistant.tab === 'graph'" />
        <PetLlmTab v-else />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";

import { useAssistantStore } from "../../stores/assistant";
import PetChatTab from "./PetChatTab.vue";
import PetGraphTab from "./PetGraphTab.vue";
import PetLlmTab from "./PetLlmTab.vue";

const assistant = useAssistantStore();
const winEl = ref<HTMLDivElement | null>(null);
const pos = reactive({ x: 0, y: 0 });

const WIN_W = 400;
const WIN_H = 540;

function clamp() {
  pos.x = Math.max(0, Math.min(pos.x, window.innerWidth - 88));
  pos.y = Math.max(0, Math.min(pos.y, window.innerHeight - 64));
}

function placeDefault() {
  pos.x = Math.max(8, window.innerWidth - WIN_W - 24);
  pos.y = Math.max(8, window.innerHeight - WIN_H - 24);
  clamp();
}

let dragging = false;
let startX = 0;
let startY = 0;
let originX = 0;
let originY = 0;

function startDrag(event: PointerEvent) {
  const target = event.target as HTMLElement;
  if (target.closest("button")) {
    return;
  }
  dragging = true;
  startX = event.clientX;
  startY = event.clientY;
  originX = pos.x;
  originY = pos.y;
  window.addEventListener("pointermove", onDrag);
  window.addEventListener("pointerup", stopDrag);
}

function onDrag(event: PointerEvent) {
  if (!dragging) {
    return;
  }
  pos.x = originX + event.clientX - startX;
  pos.y = originY + event.clientY - startY;
  clamp();
}

function stopDrag() {
  dragging = false;
  window.removeEventListener("pointermove", onDrag);
  window.removeEventListener("pointerup", stopDrag);
}

onMounted(() => {
  placeDefault();
  window.addEventListener("resize", placeDefault);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", placeDefault);
  window.removeEventListener("pointermove", onDrag);
  window.removeEventListener("pointerup", stopDrag);
});
</script>

<style scoped>
.pet-root {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1000;
}

.pet-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 72px;
  height: 72px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #4caf7d, #2f7d5b);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(47, 125, 91, 0.35);
  animation: pet-bob 3s ease-in-out infinite;
}

.pet-emoji {
  font-size: 30px;
  line-height: 1;
}

.pet-label {
  font-size: 11px;
  font-weight: 600;
}

.pet-window {
  position: fixed;
  width: 400px;
  height: 540px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pet-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: linear-gradient(135deg, #4caf7d, #2f7d5b);
  color: #fff;
  cursor: move;
  user-select: none;
  touch-action: none;
}

.pet-title {
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
}

.pet-tabs {
  display: flex;
  gap: 2px;
  margin-left: auto;
}

.pet-tabs button {
  border: none;
  background: transparent;
  color: #eaf6ef;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.pet-tabs button.active {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
  font-weight: 600;
}

.pet-actions {
  display: flex;
  gap: 2px;
}

.pet-actions button {
  border: none;
  background: transparent;
  color: #fff;
  font-size: 16px;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  cursor: pointer;
  line-height: 1;
}

.pet-actions button:hover {
  background: rgba(255, 255, 255, 0.25);
}

.pet-body {
  flex: 1;
  min-height: 0;
  padding: 10px;
}

@keyframes pet-bob {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}
</style>


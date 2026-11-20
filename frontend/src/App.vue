<template>
  <div v-if="isPublic" class="public-shell">
    <router-view />
    <DisclaimerFooter />
  </div>
  <el-container v-else class="layout">
    <el-aside width="220px">
      <div class="brand">糖安食助</div>
      <el-menu router :default-active="menuIndex">
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/profile">健康档案</el-menu-item>
        <el-menu-item index="/fridge">我的冰箱</el-menu-item>
        <el-menu-item index="/recommend">今日推荐</el-menu-item>
        <el-menu-item index="/report">营养报告</el-menu-item>
        <el-menu-item index="/shopping">购物清单</el-menu-item>
        <el-menu-item index="/chat">问答</el-menu-item>
        <el-menu-item index="/graph">知识图谱</el-menu-item>
        <el-menu-item index="/llm">大模型设置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header-bar">
        <span>{{ title }}</span>
        <span class="header-user">
          {{ user.username }}
          <el-button link type="primary" @click="signOut">退出</el-button>
        </span>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer>
        <DisclaimerFooter />
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import DisclaimerFooter from "./components/DisclaimerFooter.vue";
import { useUserStore } from "./stores/user";

const route = useRoute();
const router = useRouter();
const user = useUserStore();
const title = computed(() => String(route.meta.title ?? "糖安食助"));
const isPublic = computed(() => route.meta.public === true);
const menuIndex = computed(() =>
  route.path.startsWith("/recipe/") ? "/recommend" : route.path,
);

function signOut() {
  user.logout();
  void router.push("/login");
}
</script>

<style scoped>
.public-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.public-shell :deep(.disclaimer) {
  margin-top: auto;
}

.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}
</style>

import { createRouter, createWebHistory, type RouteRecordRaw, type Router } from "vue-router";

import { useUserStore } from "../stores/user";
import HomeView from "../views/HomeView.vue";
import AuthView from "../views/AuthView.vue";
import ProfileView from "../views/ProfileView.vue";
import FridgeView from "../views/FridgeView.vue";
import RecommendView from "../views/RecommendView.vue";
import RecipeView from "../views/RecipeView.vue";
import ReportView from "../views/ReportView.vue";
import ShoppingView from "../views/ShoppingView.vue";
import GraphView from "../views/GraphView.vue";
import ChatView from "../views/ChatView.vue";
import LlmConfigView from "../views/LlmConfigView.vue";

export const routes: RouteRecordRaw[] = [
  { path: "/login", component: AuthView, meta: { title: "登录", public: true } },
  { path: "/register", component: AuthView, meta: { title: "注册", public: true } },
  { path: "/", name: "home", component: HomeView, meta: { title: "首页" } },
  { path: "/profile", component: ProfileView, meta: { title: "健康档案" } },
  { path: "/fridge", component: FridgeView, meta: { title: "我的冰箱" } },
  { path: "/recommend", component: RecommendView, meta: { title: "今日推荐" } },
  { path: "/recipe/:id", component: RecipeView, meta: { title: "食谱详情" } },
  { path: "/report", component: ReportView, meta: { title: "营养报告" } },
  { path: "/shopping", component: ShoppingView, meta: { title: "购物清单" } },
  { path: "/chat", component: ChatView, meta: { title: "问答" } },
  { path: "/graph", component: GraphView, meta: { title: "知识图谱" } },
  { path: "/llm", component: LlmConfigView, meta: { title: "大模型设置" } },
];

export function attachAuthGuard(router: Router) {
  router.beforeEach((to) => {
    if (to.meta.public) {
      return true;
    }
    if (useUserStore().token) {
      return true;
    }
    return { path: "/login", query: { redirect: to.fullPath } };
  });
}

const router = createRouter({
  history: createWebHistory(),
  routes,
});

attachAuthGuard(router);

export default router;

import { createRouter, createWebHistory, type RouteRecordRaw, type Router } from "vue-router";

import { useUserStore } from "../stores/user";
import HomeView from "../views/HomeView.vue";
import AuthView from "../views/AuthView.vue";
import ProfileView from "../views/ProfileView.vue";
import FridgeView from "../views/FridgeView.vue";
import RecommendView from "../views/RecommendView.vue";
import MealPlanView from "../views/MealPlanView.vue";
import RecipeView from "../views/RecipeView.vue";
import ReportView from "../views/ReportView.vue";
import EmailForwardView from "../views/EmailForwardView.vue";
import ShoppingView from "../views/ShoppingView.vue";
import HealthView from "../views/HealthView.vue";

export const routes: RouteRecordRaw[] = [
  { path: "/login", component: AuthView, meta: { title: "登录", public: true } },
  { path: "/register", component: AuthView, meta: { title: "注册", public: true } },
  { path: "/", name: "home", component: HomeView, meta: { title: "首页" } },
  { path: "/profile", component: ProfileView, meta: { title: "健康档案" } },
  { path: "/health", component: HealthView, meta: { title: "健康趋势" } },
  { path: "/fridge", component: FridgeView, meta: { title: "我的冰箱" } },
  { path: "/recommend", component: RecommendView, meta: { title: "今日推荐" } },
  { path: "/meal-plan", component: MealPlanView, meta: { title: "我的清单" } },
  { path: "/recipe/:id", component: RecipeView, meta: { title: "食谱详情" } },
  { path: "/report", component: ReportView, meta: { title: "营养报告" } },
  { path: "/report-email", component: EmailForwardView, meta: { title: "转发给家人" } },
  { path: "/shopping", component: ShoppingView, meta: { title: "购物清单" } },
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

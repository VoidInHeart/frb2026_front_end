import { createRouter, createWebHistory } from "vue-router";
import UploadView from "../views/UploadView.vue";
import ReviewWorkspaceView from "../views/ReviewWorkspaceView.vue";
import RecommendationDetailView from "../views/RecommendationDetailView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "upload",
      component: UploadView,
      meta: { title: "上传论文" }
    },
    {
      path: "/workspace",
      name: "workspace",
      component: ReviewWorkspaceView,
      meta: { title: "评审工作台" }
    },
    {
      path: "/recommendations/:paperId",
      name: "recommendation-detail",
      component: RecommendationDetailView,
      meta: { title: "推荐论文详情" }
    }
  ],
  scrollBehavior() {
    return { top: 0 };
  }
});

router.afterEach((to) => {
  document.title = `${to.meta.title || "论文评分系统"} · 论文评分系统`;
});

export default router;

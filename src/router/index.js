import { createRouter, createWebHistory } from "vue-router";
import RecommendationDetailView from "../views/RecommendationDetailView.vue";
import ReviewWorkspaceView from "../views/ReviewWorkspaceView.vue";
import RuleLibraryManagementView from "../views/RuleLibraryManagementView.vue";
import UploadView from "../views/UploadView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "upload",
      component: UploadView,
      meta: {
        title: "上传论文"
      }
    },
    {
      path: "/rule-library",
      name: "rule-library-management",
      component: RuleLibraryManagementView,
      meta: {
        title: "规则库管理"
      }
    },
    {
      path: "/workspace",
      name: "workspace",
      component: ReviewWorkspaceView,
      meta: {
        title: "论文评分工作台"
      }
    },
    {
      path: "/recommendations/:paperId",
      name: "recommendation-detail",
      component: RecommendationDetailView,
      meta: {
        title: "推荐论文详情"
      }
    }
  ]
});

router.afterEach((to) => {
  if (typeof document !== "undefined") {
    document.title = to.meta?.title
      ? `${to.meta.title} | 论文评分系统`
      : "论文评分系统";
  }
});

export default router;

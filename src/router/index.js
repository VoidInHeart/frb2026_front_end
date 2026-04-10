import { createRouter, createWebHistory } from "vue-router";
import RecommendationDetailView from "../views/RecommendationDetailView.vue";
import ReviewWorkspaceView from "../views/ReviewWorkspaceView.vue";
import SummaryView from "../views/SummaryView.vue";
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
      path: "/workspace",
      name: "workspace",
      component: ReviewWorkspaceView,
      meta: {
        title: "审查工作区"
      }
    },
    {
      path: "/summary",
      name: "summary",
      component: SummaryView,
      meta: {
        title: "汇总页面"
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
      ? `${to.meta.title} | 论文分阶段审查系统`
      : "论文分阶段审查系统";
  }
});

export default router;

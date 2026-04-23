import { createRouter, createWebHistory } from "vue-router";
import AboutView from "../views/AboutView.vue";
import HomeView from "../views/HomeView.vue";
import LoadingView from "../views/LoadingView.vue";
import RecommendationDetailView from "../views/RecommendationDetailView.vue";
import ReviewWorkspaceView from "../views/ReviewWorkspaceView.vue";
import SummaryView from "../views/SummaryView.vue";
import UploadView from "../views/UploadView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      meta: {
        title: "研航智审",
      },
    },
    {
      path: "/upload",
      alias: "/review/start",
      name: "upload",
      component: UploadView,
      meta: {
        title: "上传论文",
      },
    },
    {
      path: "/loading",
      name: "loading",
      component: LoadingView,
      meta: {
        title: "加载页面",
      },
    },
    {
      path: "/workspace",
      name: "workspace",
      component: ReviewWorkspaceView,
      meta: {
        title: "审查工作区",
      },
    },
    {
      path: "/summary",
      name: "summary",
      component: SummaryView,
      meta: {
        title: "汇总页面",
      },
    },
    {
      path: "/recommendations/:paperId",
      name: "recommendation-detail",
      component: RecommendationDetailView,
      meta: {
        title: "推荐论文详情",
      },
    },
    {
      path: "/about",
      name: "about",
      component: AboutView,
      meta: {
        title: "关于我们",
      },
    },
  ],
});

router.afterEach((to) => {
  if (typeof document !== "undefined") {
    document.title = to.meta?.title
      ? `${to.meta.title} | 论文分阶段审查系统`
      : "论文分阶段审查系统";
  }
});

export default router;

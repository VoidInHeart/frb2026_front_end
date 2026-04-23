<script setup>
import { computed, ref } from "vue";

const featureCards = [
  {
    title: "精准定制",
    description: "结合规则库与任务意图，生成面向不同学科和评审偏好的个性化审查路径。"
  },
  {
    title: "协同智能",
    description: "通过多能力编排衔接解析、审查、汇总与推荐，让复杂流程在同一工作流中协同推进。"
  },
  {
    title: "全方位剖析",
    description: "覆盖格式、逻辑、方法与创新点，并对关键证据和问题进行结构化沉淀。"
  },
  {
    title: "便携流程",
    description: "从上传到汇总全流程可追踪、可回看，支持快速启动与清晰决策。"
  }
];

const logoCandidates = [
  "/assets/logo.svg",
  "/assets/logo.png",
  "/assets/logo.jpg",
  "/assets/logo.jpeg",
  "/assets/logo.webp"
];

const logoIndex = ref(0);
const showLogoImage = ref(true);

const logoSrc = computed(() => logoCandidates[logoIndex.value] || "");

function handleLogoError() {
  if (logoIndex.value < logoCandidates.length - 1) {
    logoIndex.value += 1;
    return;
  }

  showLogoImage.value = false;
}
</script>

<template>
  <section class="home-layout">
      <div class="home-brand-cluster">
        <div class="logo-orb" aria-label="研航智审 Logo">
          <div class="logo-mark">
            <img
              v-if="showLogoImage"
              :src="logoSrc"
              alt="研航智审 Logo"
              class="site-logo"
              @error="handleLogoError"
            />
            <div v-else class="logo-fallback">研航</div>
          </div>
        </div>

        <div class="brand-title-wrap">
          <h1 class="brand-title">研航智审</h1>
          <p class="brand-subtitle">——基于规则驱动和智能体编排的专家评审系统</p>
        </div>
      </div>

      <p class="brand-intro">
        让论文审查从“人工切换任务”变为“结构化协同流程”，在单一入口中连接解析、规则执行与专家建议生成。
      </p>

      <div class="feature-grid">
        <article v-for="(feature, index) in featureCards" :key="feature.title" class="feature-card">
          <p class="feature-kicker">0{{ index + 1 }}</p>
          <h2 class="feature-title">{{ feature.title }}</h2>
          <p class="feature-desc">{{ feature.description }}</p>
        </article>
      </div>

      <div class="button-row home-actions">
        <RouterLink class="primary-button hero-primary" to="/upload">开启论文评审</RouterLink>
      </div>
  </section>
</template>

<style scoped>
.home-layout {
  min-height: calc(100vh - var(--topbar-offset));
  width: 100vw;
  margin-left: calc(50% - 50vw);
  position: relative;
  overflow: hidden;
  padding: clamp(4px, 0.8vw, 10px) clamp(14px, 4vw, 54px) clamp(18px, 2.2vw, 28px);
  display: grid;
  align-content: start;
  gap: clamp(10px, 1.4vw, 18px);
}

.home-layout::before,
.home-layout::after {
  content: "";
  position: absolute;
  border-radius: 999px;
  pointer-events: none;
}

.home-layout::before {
  width: 340px;
  height: 340px;
  top: -180px;
  right: -120px;
  background: radial-gradient(circle, rgba(208, 122, 53, 0.3), transparent 68%);
}

.home-layout::after {
  width: 320px;
  height: 320px;
  left: -120px;
  bottom: -190px;
  background: radial-gradient(circle, var(--primary-soft), transparent 68%);
}

.home-brand-cluster {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 12px;
}

.logo-orb {
  width: clamp(88px, 10vw, 124px);
  height: clamp(88px, 10vw, 124px);
  border-radius: 28px;
  border: 1px solid var(--border);
  background:
    linear-gradient(145deg, var(--surface-muted), var(--panel));
  box-shadow: 0 14px 32px rgba(19, 63, 103, 0.16);
  display: grid;
  place-items: center;
}

.logo-mark {
  width: 84%;
  height: 84%;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 22px rgba(19, 63, 103, 0.14);
  display: grid;
  place-items: center;
}

.site-logo {
  width: 82%;
  height: 82%;
  object-fit: contain;
}

.logo-fallback {
  font-size: clamp(22px, 2.2vw, 30px);
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--primary);
}

.brand-title-wrap {
  position: relative;
  width: min(100%, 860px);
  text-align: center;
  display: grid;
  gap: 4px;
}

.brand-title {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(40px, 8vw, 88px);
  line-height: 1.04;
  letter-spacing: 0.03em;
  background: linear-gradient(120deg, var(--primary), var(--accent));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.brand-subtitle {
  margin: 0;
  justify-self: end;
  max-width: 520px;
  text-align: right;
  color: var(--muted);
  font-size: clamp(14px, 1.8vw, 18px);
}

.brand-intro {
  position: relative;
  z-index: 1;
  margin: 0 auto;
  width: min(100%, 900px);
  padding: 12px 18px;
  border-radius: 16px;
  text-align: center;
  font-family: "STKaiti", "KaiTi", "Kaiti SC", "Noto Serif SC", serif;
  font-size: clamp(15px, 1.45vw, 19px);
  line-height: 1.72;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #171717;
  background: rgba(255, 255, 255, 0.56);
}

.feature-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.feature-card {
  padding: 12px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
  box-shadow: 0 8px 24px rgba(19, 63, 103, 0.1);
}

.feature-kicker {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--accent);
}

.feature-title {
  margin: 7px 0 0;
  font-size: 20px;
  font-family: Georgia, "Times New Roman", serif;
}

.feature-desc {
  margin: 7px 0 0;
  font-size: 14px;
  color: var(--muted);
}

.home-actions {
  position: relative;
  z-index: 1;
  justify-content: center;
}

.hero-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-width: clamp(240px, 34vw, 360px);
  min-height: 62px;
  padding: 0 34px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  font-family: "STKaiti", "KaiTi", "Noto Serif SC", serif;
  font-size: clamp(22px, 2.4vw, 30px);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.24);
  background: linear-gradient(135deg, var(--primary) 0%, #2f6f99 52%, var(--accent) 100%);
  box-shadow: 0 20px 40px rgba(19, 63, 103, 0.26);
}

.hero-primary:hover {
  transform: translateY(-2px) scale(1.015);
  box-shadow: 0 24px 44px rgba(19, 63, 103, 0.32);
}

:global(:root[data-theme="dark"]) .logo-orb {
  border-color: rgba(116, 202, 255, 0.34);
  background: linear-gradient(145deg, rgba(8, 20, 36, 0.9), rgba(14, 33, 58, 0.84));
}

:global(:root[data-theme="dark"]) .logo-mark {
  background: rgba(250, 252, 255, 0.97);
  box-shadow: 0 12px 26px rgba(2, 8, 23, 0.42);
}

:global(:root[data-theme="vivid"]) .logo-mark {
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 24px rgba(77, 150, 255, 0.24);
}

@media (max-width: 1080px) {
  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .home-layout {
    min-height: auto;
    margin-left: calc(50% - 50vw);
    padding: 2px 12px 14px;
  }

  .brand-intro {
    padding: 10px 14px;
    font-size: clamp(14px, 4.2vw, 17px);
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .brand-subtitle {
    justify-self: center;
    text-align: center;
  }

  .hero-primary {
    width: 100%;
    min-width: 0;
    font-size: clamp(20px, 6vw, 24px);
  }
}
</style>

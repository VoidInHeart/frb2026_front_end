<template>
  <section class="about-layout">
    <section class="about-card glass-card">
      <p class="summary-kicker">About Us</p>
      <h1 class="section-title about-title">研航智审团队</h1>
      <p class="about-desc">
        研航智审聚焦于“规则驱动 + 智能体编排”的论文评审场景，把解析能力、阶段审查与汇总推荐组织为一条可追踪、可协作、可持续优化的审查流水线。
      </p>

      <div class="about-points">
        <article class="about-point">
          <h2>我们的目标</h2>
          <p>让论文审查更标准化、更透明，帮助评审者快速聚焦关键问题与证据链。</p>
        </article>
        <article class="about-point">
          <h2>我们的方式</h2>
          <p>以规则基线保障稳定性，再通过能力编排增强复杂场景下的智能判断。</p>
        </article>
        <article class="about-point">
          <h2>我们的价值</h2>
          <p>提升评审效率，降低重复劳动，让专家把精力投入在高价值决策。</p>
        </article>
      </div>

      <div class="button-row about-actions">
        <RouterLink class="secondary-button about-action-link" to="/">返回主页</RouterLink>
        <RouterLink class="primary-button about-action-link" to="/upload">开启论文评审</RouterLink>
      </div>
    </section>
  </section>
</template>

<style scoped>
.about-layout {
  min-height: calc(100vh - var(--topbar-offset) - 40px);
  display: grid;
  align-items: start;
}

.about-card {
  padding: clamp(24px, 3vw, 36px);
  display: grid;
  gap: 16px;
}

.about-title {
  font-size: clamp(32px, 4.2vw, 52px);
}

.summary-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.about-desc {
  margin: 0;
  color: var(--muted);
  width: min(100%, 880px);
}

.about-points {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.about-point {
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px;
  background: var(--surface-muted);
}

.about-point h2 {
  margin: 0;
  font-size: 20px;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--primary);
}

.about-point p {
  margin: 8px 0 0;
  color: var(--muted);
}

.about-actions {
  justify-content: center;
}

.about-action-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-width: 184px;
  font-family: "STKaiti", "KaiTi", "Kaiti SC", "Noto Serif SC", serif;
  font-size: clamp(20px, 2vw, 24px);
  font-weight: 700;
  letter-spacing: 0.05em;
}

@media (max-width: 980px) {
  .about-points {
    grid-template-columns: 1fr;
  }

  .about-action-link {
    min-width: 0;
    width: 100%;
  }
}
</style>

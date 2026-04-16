<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  createReviewRun,
  fetchRunState,
  uploadPaper
} from "../services/api";
import { clearPendingUpload, getPendingUpload } from "../stores/pendingUpload";
import {
  reviewSession,
  setCurrentStage,
  setRunRecord,
  setRunState,
  setSubmission
} from "../stores/reviewSession";

const router = useRouter();

const uploadRequest = ref(getPendingUpload());
const resolvedSubmission = ref(null);
const phase = ref("queued");
const statusDetail = ref("正在准备解析任务...");
const errorMessage = ref("");
const retrying = ref(false);
const progress = ref(6);

let disposed = false;
let detailTimer = null;
let progressTimer = null;
let redirectTimer = null;

const phaseOrder = Object.freeze({
  queued: 0,
  parsing: 1,
  syncing: 2,
  ready: 3
});

const phaseProgressMap = Object.freeze({
  queued: { floor: 6, ceiling: 12 },
  parsing: { floor: 16, ceiling: 78 },
  syncing: { floor: 84, ceiling: 96 },
  ready: { floor: 100, ceiling: 100 }
});

const paperLabel = computed(() => {
  if (uploadRequest.value?.useDemo) {
    return uploadRequest.value?.mockProfile === "logic-pass"
      ? "逻辑通过示例"
      : "示例论文";
  }

  return (
    uploadRequest.value?.paperFile?.name ||
    uploadRequest.value?.markdownFile?.name ||
    "待解析论文"
  );
});

const sourceLabel = computed(() => {
  if (uploadRequest.value?.useDemo) {
    return "示例数据";
  }

  if (uploadRequest.value?.paperFile) {
    return "PDF 上传";
  }

  return "高级导入";
});

const statusTitle = computed(() => {
  if (errorMessage.value) {
    return "处理已中断";
  }

  if (phase.value === "parsing") {
    return "正在解析论文内容";
  }

  if (phase.value === "syncing") {
    return "正在创建 review run";
  }

  if (phase.value === "ready") {
    return "准备进入审查工作区";
  }

  return "正在准备任务";
});

const progressPercent = computed(() =>
  Math.max(0, Math.min(100, Math.round(progress.value)))
);

const progressLabel = computed(() => `${progressPercent.value}%`);

const progressStageLabel = computed(() => {
  if (errorMessage.value) {
    return "WAITING";
  }

  if (phase.value === "parsing") {
    return "PARSING";
  }

  if (phase.value === "syncing") {
    return "RUN SETUP";
  }

  if (phase.value === "ready") {
    return "READY";
  }

  return "QUEUED";
});

const waterStyle = computed(() => ({
  height: `${progressPercent.value}%`
}));

const phaseItems = computed(() => [
  {
    key: "queued",
    title: "接收上传请求",
    description: `已收到 ${paperLabel.value}`
  },
  {
    key: "parsing",
    title: "解析论文与资源",
    description: "生成 paper.md、paper_meta.json 与静态资源路径"
  },
  {
    key: "syncing",
    title: "创建 review run",
    description: "按新的 /runs 协议提交 paper bundle"
  },
  {
    key: "ready",
    title: "进入审查工作区",
    description: "run_id 与初始 run state 已就绪"
  }
]);

const primaryActionLabel = computed(() =>
  resolvedSubmission.value ? "重试创建 run" : "重新开始解析"
);

function stopDetailLoop() {
  if (detailTimer) {
    window.clearInterval(detailTimer);
    detailTimer = null;
  }
}

function stopProgressLoop() {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

function stopRedirectTimer() {
  if (redirectTimer) {
    window.clearTimeout(redirectTimer);
    redirectTimer = null;
  }
}

function playDetailLoop(messages) {
  stopDetailLoop();
  statusDetail.value = messages[0] ?? "";

  if (messages.length <= 1) {
    return;
  }

  let index = 0;
  detailTimer = window.setInterval(() => {
    index = (index + 1) % messages.length;
    statusDetail.value = messages[index];
  }, 1800);
}

function startProgressLoop(nextPhase) {
  stopProgressLoop();

  const range = phaseProgressMap[nextPhase] ?? phaseProgressMap.queued;
  progress.value = Math.max(progress.value, range.floor);

  if (range.floor === range.ceiling) {
    progress.value = range.ceiling;
    return;
  }

  progressTimer = window.setInterval(() => {
    const remaining = range.ceiling - progress.value;

    if (remaining <= 0.2) {
      progress.value = range.ceiling;
      stopProgressLoop();
      return;
    }

    const increment =
      remaining > 24 ? 1.3 : remaining > 10 ? 0.75 : remaining > 4 ? 0.34 : 0.16;

    progress.value = Math.min(
      range.ceiling,
      Number((progress.value + increment).toFixed(2))
    );
  }, 120);
}

function updatePhase(nextPhase) {
  phase.value = nextPhase;
  startProgressLoop(nextPhase);

  if (nextPhase === "parsing") {
    playDetailLoop([
      "正在读取论文文件并准备解析环境。",
      "这一阶段主要生成 paper.md 与 paper_meta.json。",
      "解析完成后会自动创建新的 review run。"
    ]);
    return;
  }

  if (nextPhase === "syncing") {
    playDetailLoop([
      "paper bundle 已准备完成，正在提交到 /runs。",
      "run 创建成功后会同步读取一次最新 state。"
    ]);
    return;
  }

  if (nextPhase === "ready") {
    playDetailLoop(["run_id 与初始 state 已就绪，正在进入审查工作区。"]);
    return;
  }

  playDetailLoop(["正在准备解析任务..."]);
}

function getPhaseState(key) {
  const currentOrder = phaseOrder[phase.value] ?? 0;
  const itemOrder = phaseOrder[key] ?? 0;

  if (itemOrder < currentOrder) {
    return "done";
  }

  if (itemOrder === currentOrder) {
    return errorMessage.value ? "waiting" : "active";
  }

  return "waiting";
}

async function finalizeSubmission(submission) {
  progress.value = Math.max(progress.value, phaseProgressMap.syncing.floor);
  updatePhase("syncing");

  const runRecord = await createReviewRun({
    paperTitle: submission.paperName,
    paperMarkdown: submission.paperMarkdown,
    paperMeta: submission.paperMeta
  });
  const initialRunState = await fetchRunState(runRecord.runId);

  if (disposed) {
    return;
  }

  setSubmission(submission);
  setRunRecord(runRecord);
  setRunState(initialRunState);
  setCurrentStage(initialRunState.nextStage ?? runRecord.currentStage ?? "format");
  clearPendingUpload();

  updatePhase("ready");

  stopRedirectTimer();
  redirectTimer = window.setTimeout(() => {
    if (!disposed) {
      router.replace({ name: "workspace" });
    }
  }, 420);
}

async function runUploadFlow() {
  if (!uploadRequest.value) {
    if (reviewSession.currentSubmission) {
      router.replace({ name: "workspace" });
      return;
    }

    router.replace({ name: "upload" });
    return;
  }

  errorMessage.value = "";
  retrying.value = true;

  try {
    let submission = resolvedSubmission.value;

    if (!submission) {
      progress.value = Math.min(progress.value, 18);
      updatePhase("parsing");

      submission = await uploadPaper({
        paperFile: uploadRequest.value.paperFile,
        markdownFile: uploadRequest.value.markdownFile,
        documentIrFile: uploadRequest.value.documentIrFile,
        imageBaseUrl: uploadRequest.value.imageBaseUrl,
        mockProfile: uploadRequest.value.mockProfile
      });

      if (disposed) {
        return;
      }

      resolvedSubmission.value = submission;
    }

    await finalizeSubmission(submission);
  } catch (error) {
    if (disposed) {
      return;
    }

    stopDetailLoop();
    stopProgressLoop();
    errorMessage.value =
      error instanceof Error ? error.message : "论文解析或 run 创建失败，请稍后重试。";
  } finally {
    retrying.value = false;
  }
}

function retryFlow() {
  runUploadFlow();
}

function backToUpload() {
  clearPendingUpload();
  router.replace({ name: "upload" });
}

onMounted(() => {
  updatePhase("queued");
  runUploadFlow();
});

onBeforeUnmount(() => {
  disposed = true;
  stopDetailLoop();
  stopProgressLoop();
  stopRedirectTimer();
});
</script>

<template>
  <section class="loading-layout">
    <section class="loading-hero glass-card">
      <div class="hero-copy">
        <span class="pill pill-accent">Run Bootstrap</span>
        <p class="summary-kicker">处理中</p>
        <h1 class="section-title loading-title">{{ statusTitle }}</h1>
        <p class="hero-text">{{ statusDetail }}</p>

        <div class="meta-row">
          <span class="pill pill-primary">{{ sourceLabel }}</span>
          <span class="pill pill-neutral">{{ paperLabel }}</span>
        </div>
      </div>

      <div class="hero-visual" aria-hidden="true">
        <div
          class="progress-vessel"
          :class="{
            'progress-vessel-error': Boolean(errorMessage),
            'progress-vessel-ready': phase === 'ready'
          }"
        >
          <div class="progress-grid"></div>
          <div class="progress-gloss"></div>
          <div class="progress-liquid" :style="waterStyle">
            <div class="progress-wave wave-back"></div>
            <div class="progress-wave wave-front"></div>
          </div>
          <div class="progress-readout">
            <strong>{{ progressLabel }}</strong>
            <span>{{ progressStageLabel }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="grid-two">
      <article class="glass-card phase-card">
        <p class="summary-kicker">任务流程</p>
        <div class="phase-list">
          <article
            v-for="(item, index) in phaseItems"
            :key="item.key"
            class="phase-item"
            :class="`phase-${getPhaseState(item.key)}`"
          >
            <div class="phase-badge">{{ index + 1 }}</div>
            <div class="phase-copy">
              <strong>{{ item.title }}</strong>
              <p>{{ item.description }}</p>
            </div>
          </article>
        </div>
      </article>

      <article class="glass-card phase-card">
        <p class="summary-kicker">状态说明</p>
        <div v-if="errorMessage" class="error-banner">
          {{ errorMessage }}
        </div>
        <div v-else class="status-panel">
          <p class="status-line">{{ statusTitle }}</p>
          <p class="status-note">
            当前页面会先完成解析，再创建新的 run，并把 `run_id` 与初始 state
            存到会话状态里。
          </p>
        </div>

        <div class="button-row">
          <button
            class="primary-button"
            type="button"
            :disabled="retrying"
            @click="retryFlow"
          >
            {{ retrying ? "处理中..." : primaryActionLabel }}
          </button>
          <button
            class="ghost-button"
            type="button"
            :disabled="retrying"
            @click="backToUpload"
          >
            返回上传页
          </button>
        </div>
      </article>
    </section>
  </section>
</template>

<style scoped>
.loading-layout {
  display: grid;
  gap: 22px;
}

.loading-hero,
.phase-card {
  padding: 28px;
}

.loading-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 24px;
  align-items: center;
}

.hero-copy {
  display: grid;
  gap: 14px;
}

.summary-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.loading-title {
  font-size: clamp(32px, 4vw, 52px);
  line-height: 1.04;
}

.hero-text {
  margin: 0;
  max-width: 56ch;
  color: var(--muted);
  font-size: 17px;
  line-height: 1.8;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-visual {
  display: grid;
  place-items: center;
  min-height: 340px;
}

.progress-vessel {
  position: relative;
  width: min(100%, 280px);
  height: 320px;
  overflow: hidden;
  border-radius: 36px;
  border: 1px solid rgba(19, 63, 103, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.28)),
    rgba(255, 255, 255, 0.4);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    inset 0 -14px 36px rgba(19, 63, 103, 0.08),
    0 28px 48px rgba(19, 63, 103, 0.18);
}

.progress-vessel-ready {
  border-color: rgba(47, 133, 90, 0.22);
}

.progress-vessel-error {
  border-color: rgba(192, 86, 33, 0.22);
}

.progress-grid,
.progress-gloss,
.progress-liquid,
.progress-readout {
  position: absolute;
  inset: 0;
}

.progress-grid {
  background:
    linear-gradient(
      180deg,
      rgba(19, 63, 103, 0.04) 0%,
      rgba(19, 63, 103, 0.01) 100%
    ),
    repeating-linear-gradient(
      0deg,
      transparent 0 32px,
      rgba(19, 63, 103, 0.06) 32px 33px
    );
  opacity: 0.75;
}

.progress-gloss {
  inset: 14px auto 14px 14px;
  width: 26%;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.54), transparent 75%);
  filter: blur(2px);
}

.progress-liquid {
  top: auto;
  height: 0;
  background:
    linear-gradient(180deg, rgba(138, 206, 244, 0.92), rgba(60, 140, 212, 0.94) 42%, rgba(18, 77, 136, 0.98));
  box-shadow: inset 0 14px 24px rgba(255, 255, 255, 0.18);
  transition: height 0.7s ease;
}

.progress-vessel-ready .progress-liquid {
  background:
    linear-gradient(180deg, rgba(137, 219, 181, 0.92), rgba(67, 180, 124, 0.96) 42%, rgba(34, 120, 76, 0.98));
}

.progress-vessel-error .progress-liquid {
  background:
    linear-gradient(180deg, rgba(246, 173, 85, 0.84), rgba(228, 115, 51, 0.9) 42%, rgba(192, 86, 33, 0.96));
}

.progress-wave {
  position: absolute;
  left: -12%;
  width: 124%;
  border-radius: 48% 52% 0 0 / 100% 100% 0 0;
}

.wave-back {
  top: -20px;
  height: 32px;
  background: rgba(255, 255, 255, 0.28);
  animation: drift 8s linear infinite;
}

.wave-front {
  top: -14px;
  height: 24px;
  background: rgba(255, 255, 255, 0.58);
  animation: drift 5.2s linear infinite reverse;
}

.progress-readout {
  z-index: 2;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 8px;
  text-align: center;
}

.progress-readout strong {
  font-size: clamp(44px, 8vw, 72px);
  line-height: 1;
  color: #163a61;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.8);
}

.progress-readout span {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(22, 58, 97, 0.78);
  font-weight: 700;
}

.phase-card {
  display: grid;
  gap: 18px;
}

.phase-list {
  display: grid;
  gap: 12px;
}

.phase-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(19, 63, 103, 0.1);
  background: rgba(255, 255, 255, 0.5);
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.phase-active {
  border-color: rgba(19, 63, 103, 0.35);
  background: rgba(255, 255, 255, 0.78);
  transform: translateY(-1px);
}

.phase-done {
  border-color: rgba(47, 133, 90, 0.22);
  background: rgba(47, 133, 90, 0.08);
}

.phase-badge {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-weight: 700;
  background: rgba(19, 63, 103, 0.1);
  color: var(--primary);
}

.phase-done .phase-badge {
  background: rgba(47, 133, 90, 0.18);
  color: var(--success);
}

.phase-copy {
  display: grid;
  gap: 6px;
}

.phase-copy strong,
.status-line {
  font-size: 18px;
}

.phase-copy p,
.status-note {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.status-panel {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid rgba(19, 63, 103, 0.1);
}

.status-line {
  margin: 0;
}

.error-banner {
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
  line-height: 1.7;
}

@keyframes drift {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(-12%);
  }
}

@media (max-width: 1080px) {
  .loading-hero {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    min-height: 280px;
  }
}

@media (max-width: 720px) {
  .loading-hero,
  .phase-card {
    padding: 22px;
  }

  .progress-vessel {
    width: min(100%, 240px);
    height: 280px;
    border-radius: 30px;
  }

  .progress-readout strong {
    font-size: 54px;
  }
}
</style>

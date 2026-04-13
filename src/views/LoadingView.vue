<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { submitPaperMeta, uploadPaper } from "../services/api";
import { clearPendingUpload, getPendingUpload } from "../stores/pendingUpload";
import {
  reviewSession,
  setCurrentStage,
  setSubmission,
  setTransmissionStatus
} from "../stores/reviewSession";

const router = useRouter();

const uploadRequest = ref(getPendingUpload());
const resolvedSubmission = ref(null);
const phase = ref("queued");
const statusDetail = ref("正在准备解析任务...");
const errorMessage = ref("");
const retrying = ref(false);

let disposed = false;
let detailTimer = null;

const phaseOrder = Object.freeze({
  queued: 0,
  parsing: 1,
  syncing: 2,
  ready: 3
});

const paperLabel = computed(() => {
  if (uploadRequest.value?.useDemo) {
    return uploadRequest.value?.mockProfile === "logic-pass"
      ? "逻辑审查通过样例"
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
    return "解析中断";
  }

  if (phase.value === "parsing") {
    return "正在解析论文内容";
  }

  if (phase.value === "syncing") {
    return "正在同步结构化结果";
  }

  if (phase.value === "ready") {
    return "解析完成";
  }

  return "正在准备上传任务";
});

const phaseItems = computed(() => [
  {
    key: "queued",
    title: "接收上传请求",
    description: `已收到 ${paperLabel.value}`
  },
  {
    key: "parsing",
    title: "解析论文与资源",
    description: "抽取 Markdown、图片引用和 paper_meta.json"
  },
  {
    key: "syncing",
    title: "同步审查输入",
    description: "把结构化结果送入后续审查流程"
  },
  {
    key: "ready",
    title: "进入审查工作区",
    description: "准备切换到格式审查页面"
  }
]);

const primaryActionLabel = computed(() =>
  resolvedSubmission.value ? "重试同步结果" : "重新开始解析"
);

function stopDetailLoop() {
  if (detailTimer) {
    window.clearInterval(detailTimer);
    detailTimer = null;
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

function updatePhase(nextPhase) {
  phase.value = nextPhase;

  if (nextPhase === "parsing") {
    playDetailLoop([
      "正在读取论文文件并准备解析环境。",
      "这一步通常和论文体积、图表数量有关。",
      "解析完成后会自动同步到审查工作区。"
    ]);
    return;
  }

  if (nextPhase === "syncing") {
    playDetailLoop([
      "论文正文已经提取完成，正在整理结构化元数据。",
      "马上就可以进入格式审查页面了。"
    ]);
    return;
  }

  if (nextPhase === "ready") {
    playDetailLoop(["解析结果已准备完成，正在进入审查工作区。"]);
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
  updatePhase("syncing");

  const transmission = await submitPaperMeta({
    submissionId: submission.submissionId,
    paperMeta: submission.paperMeta
  });

  if (disposed) {
    return;
  }

  setSubmission(submission);
  setCurrentStage("format");
  setTransmissionStatus(transmission);
  clearPendingUpload();

  updatePhase("ready");

  window.setTimeout(() => {
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
    errorMessage.value =
      error instanceof Error ? error.message : "论文解析失败，请稍后重试。";
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
});
</script>

<template>
  <section class="loading-layout">
    <section class="loading-hero glass-card">
      <div class="hero-copy">
        <span class="pill pill-accent">Parsing In Progress</span>
        <p class="summary-kicker">等待解析</p>
        <h1 class="section-title loading-title">{{ statusTitle }}</h1>
        <p class="hero-text">
          {{ statusDetail }}
        </p>

        <div class="meta-row">
          <span class="pill pill-primary">{{ sourceLabel }}</span>
          <span class="pill pill-neutral">{{ paperLabel }}</span>
        </div>
      </div>

      <div class="hero-visual" aria-hidden="true">
        <div class="signal-core"></div>
        <div class="signal-ring ring-one"></div>
        <div class="signal-ring ring-two"></div>
        <div class="signal-ring ring-three"></div>
      </div>
    </section>

    <section class="grid-two">
      <article class="glass-card phase-card">
        <p class="summary-kicker">解析流程</p>
        <div class="phase-list">
          <article
            v-for="item in phaseItems"
            :key="item.key"
            class="phase-item"
            :class="`phase-${getPhaseState(item.key)}`"
          >
            <div class="phase-badge">{{ phaseItems.findIndex((phase) => phase.key === item.key) + 1 }}</div>
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
            解析时间会受到论文页数、图片数量和本地解析服务状态影响。当前页面会自动继续，无需重复操作。
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
          <button class="ghost-button" type="button" :disabled="retrying" @click="backToUpload">
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
  position: relative;
  display: grid;
  place-items: center;
  min-height: 320px;
}

.signal-core {
  width: 132px;
  height: 132px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.95), transparent 28%),
    linear-gradient(135deg, rgba(19, 63, 103, 0.96), rgba(208, 122, 53, 0.82));
  box-shadow:
    0 0 0 18px rgba(255, 255, 255, 0.28),
    0 24px 48px rgba(19, 63, 103, 0.18);
}

.signal-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(19, 63, 103, 0.16);
  animation: orbit 10s linear infinite;
}

.ring-one {
  width: 188px;
  height: 188px;
}

.ring-two {
  width: 256px;
  height: 256px;
  border-style: dashed;
  animation-duration: 16s;
  animation-direction: reverse;
}

.ring-three {
  width: 320px;
  height: 320px;
  border-color: rgba(208, 122, 53, 0.22);
  animation-duration: 22s;
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

@keyframes orbit {
  from {
    transform: rotate(0deg) scale(1);
  }

  50% {
    transform: rotate(180deg) scale(1.03);
  }

  to {
    transform: rotate(360deg) scale(1);
  }
}

@media (max-width: 1080px) {
  .loading-hero {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    min-height: 240px;
  }
}

@media (max-width: 720px) {
  .loading-hero,
  .phase-card {
    padding: 22px;
  }

  .signal-core {
    width: 104px;
    height: 104px;
  }

  .ring-one {
    width: 156px;
    height: 156px;
  }

  .ring-two {
    width: 210px;
    height: 210px;
  }

  .ring-three {
    width: 260px;
    height: 260px;
  }
}
</style>

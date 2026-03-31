<script setup>
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { submitPaperMeta, uploadPaper } from "../services/api";
import { appearanceState } from "../stores/appearance";
import {
  reviewSession,
  setSubmission,
  setTransmissionStatus
} from "../stores/reviewSession";

const router = useRouter();

const form = reactive({
  paperFile: null,
  markdownFile: null,
  documentIrFile: null,
  imageBaseUrl: "/mock"
});

const loading = ref(false);
const errorMessage = ref("");
const dragOverField = reactive({
  paper: false,
  markdown: false,
  documentIr: false
});

const selectedRuleCount = computed(
  () => reviewSession.ruleLibrary.selectedSystemRuleIds.length
);
const hasCustomRules = computed(() =>
  Boolean(reviewSession.ruleLibrary.customRulesText.trim())
);

function handleFileChange(event, field) {
  const [file] = event.target.files ?? [];
  form[field] = file ?? null;
}

function handleDragOver(event, field) {
  event.preventDefault();
  dragOverField[field] = true;
}

function handleDragLeave(field) {
  dragOverField[field] = false;
}

function handleDrop(event, field) {
  event.preventDefault();
  dragOverField[field] = false;

  const [file] = event.dataTransfer?.files ?? [];
  if (file) {
    form[field] = file;
  }
}

async function startReview() {
  errorMessage.value = "";
  loading.value = true;

  try {
    const submission = await uploadPaper({
      paperFile: form.paperFile,
      markdownFile: form.markdownFile,
      documentIrFile: form.documentIrFile,
      imageBaseUrl: form.imageBaseUrl
    });

    setSubmission(submission);

    const transmission = await submitPaperMeta({
      submissionId: submission.submissionId,
      paperMeta: submission.paperMeta
    });

    setTransmissionStatus(transmission);
    router.push({ name: "workspace" });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "提交失败";
  } finally {
    loading.value = false;
  }
}

function goToRuleLibrary() {
  router.push({ name: "rule-library-management" });
}
</script>

<template>
  <section
    :class="['upload-layout', { 'upload-layout-dark': appearanceState.theme === 'dark' }]"
  >
    <div class="hero-panel glass-card">
      <span class="pill pill-accent">三页流程</span>
      <h1 class="section-title hero-title">上传论文，进入结构化评分流程</h1>
      <p class="hero-text">
        现在第一步除了上传解析产物，还可以先进入规则库管理页面完成规则筛选。后端后续返回的规则反馈，可以直接沿用这里保存的规则配置。
      </p>

      <div class="hero-grid">
        <article class="hero-card">
          <strong>01 上传与传输</strong>
          <p>
            支持上传原始论文，同时预留 `paper.md`、`paper_meta.json` 和图片基础路径；提交后会先把解析结果发给后端接口。
          </p>
        </article>
        <article class="hero-card">
          <strong>02 规则筛选</strong>
          <p>
            新增规则库管理页面，分别维护系统标准规则库与用户自建规则库，为后续问题反馈和评语生成做前置配置。
          </p>
        </article>
        <article class="hero-card">
          <strong>03 工作台与推荐</strong>
          <p>
            第二页继续展示论文、评语和推荐论文；后续接真实后端时，规则筛选结果也可以一并传过去。
          </p>
        </article>
      </div>

      <div class="rule-entry-panel">
        <div class="rule-entry-copy">
          <span class="pill pill-primary">规则库管理</span>
          <h2>先配置规则，再进入上传与评审流程</h2>
          <p>
            当前已选系统规则 {{ selectedRuleCount }} 条，{{ hasCustomRules ? "已维护自建规则" : "暂未填写自建规则" }}。
            你可以在规则库管理页勾选标准规则、上传文本并抽取自建规则。
          </p>
          <div class="rule-entry-stats">
            <span class="stat-chip">系统规则 {{ selectedRuleCount }}</span>
            <span class="stat-chip">自建规则 {{ hasCustomRules ? "已配置" : "未配置" }}</span>
          </div>
        </div>
        <button class="secondary-button rule-entry-button" type="button" @click="goToRuleLibrary">
          进入规则库管理
        </button>
      </div>
    </div>

    <section class="form-panel glass-card">
      <div>
        <p class="summary-kicker">第一个界面</p>
        <h2 class="section-title">上传论文</h2>
        <p class="section-subtitle">
          没接后端时会默认读取 `public/mock` 中的示例数据；接入真实后端后，只需要把
          `VITE_USE_MOCK` 改成 `false`。
        </p>
      </div>

      <div
        class="field-group drop-zone"
        :class="{ 'drop-zone-active': dragOverField.paper }"
        @dragover.prevent="handleDragOver($event, 'paper')"
        @dragenter.prevent="handleDragOver($event, 'paper')"
        @dragleave.prevent="handleDragLeave('paper')"
        @drop.prevent="handleDrop($event, 'paper')"
      >
        <label class="field-label" for="paper-file">论文文件</label>
        <input
          id="paper-file"
          class="file-input"
          type="file"
          accept=".pdf,.doc,.docx"
          @change="(event) => handleFileChange(event, 'paperFile')"
        />
        <div class="drop-zone-content">
          <p>{{ form.paperFile ? form.paperFile.name : "拖拽文件到此或点击上传" }}</p>
          <p class="drop-text" v-if="dragOverField.paper">松手上传</p>
        </div>
        <span class="field-hint">上传这个文件后，会优先走本地解析接口。</span>
      </div>

      <div
        class="field-group drop-zone"
        :class="{ 'drop-zone-active': dragOverField.markdown }"
        @dragover.prevent="handleDragOver($event, 'markdown')"
        @dragenter.prevent="handleDragOver($event, 'markdown')"
        @dragleave.prevent="handleDragLeave('markdown')"
        @drop.prevent="handleDrop($event, 'markdown')"
      >
        <label class="field-label" for="markdown-file">解析后的 `paper.md`（可选）</label>
        <input
          id="markdown-file"
          class="file-input"
          type="file"
          accept=".md,.markdown,.txt"
          @change="(event) => handleFileChange(event, 'markdownFile')"
        />
        <div class="drop-zone-content">
          <p>{{ form.markdownFile ? form.markdownFile.name : "拖拽文件到此或点击上传" }}</p>
          <p class="drop-text" v-if="dragOverField.markdown">松手上传</p>
        </div>
      </div>

      <div
        class="field-group drop-zone"
        :class="{ 'drop-zone-active': dragOverField.documentIr }"
        @dragover.prevent="handleDragOver($event, 'documentIr')"
        @dragenter.prevent="handleDragOver($event, 'documentIr')"
        @dragleave.prevent="handleDragLeave('documentIr')"
        @drop.prevent="handleDrop($event, 'documentIr')"
      >
        <label class="field-label" for="document-ir-file">
          解析后的 `paper_meta.json`（可选）
        </label>
        <input
          id="document-ir-file"
          class="file-input"
          type="file"
          accept=".json"
          @change="(event) => handleFileChange(event, 'documentIrFile')"
        />
        <div class="drop-zone-content">
          <p>{{ form.documentIrFile ? form.documentIrFile.name : "拖拽文件到此或点击上传" }}</p>
          <p class="drop-text" v-if="dragOverField.documentIr">松手上传</p>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label" for="image-base-url">图片资源基础路径</label>
        <input
          id="image-base-url"
          v-model="form.imageBaseUrl"
          class="text-input"
          type="text"
          placeholder="/mock"
        />
        <span class="field-hint">
          后端如果把 Markdown 中的图片托管到静态目录，可以把基础路径放在这里。
        </span>
      </div>

      <div v-if="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <div class="button-row">
        <button
          class="primary-button"
          type="button"
          :disabled="loading"
          @click="startReview"
        >
          {{ loading ? "正在提交..." : "提交并进入评分工作台" }}
        </button>
        <button
          class="ghost-button"
          type="button"
          :disabled="loading"
          @click="form.imageBaseUrl = '/mock'"
        >
          使用示例图片路径
        </button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.upload-layout {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 22px;
}

.hero-panel,
.form-panel {
  padding: 28px;
}

.hero-panel {
  display: grid;
  gap: 22px;
}

.hero-title {
  font-size: clamp(34px, 5vw, 54px);
  line-height: 1.04;
}

.hero-text {
  margin: 0;
  font-size: 18px;
  color: var(--muted);
  max-width: 680px;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.hero-card,
.rule-entry-panel {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(19, 63, 103, 0.12);
}

.hero-card {
  display: grid;
  gap: 8px;
}

.hero-card strong {
  color: var(--primary);
}

.hero-card p {
  margin: 0;
  color: var(--muted);
}

.rule-entry-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
}

.rule-entry-copy {
  display: grid;
  gap: 10px;
}

.rule-entry-copy h2,
.rule-entry-copy p {
  margin: 0;
}

.rule-entry-copy p {
  color: var(--muted);
}

.rule-entry-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stat-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
}

.rule-entry-button {
  min-width: 180px;
}

.form-panel {
  display: grid;
  gap: 18px;
  align-content: start;
}

.drop-zone {
  position: relative;
  border: 2px dashed rgba(94, 138, 223, 0.35);
  border-radius: 14px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.drop-zone-active {
  border-color: rgba(50, 96, 197, 0.85);
  background: rgba(255, 255, 255, 0.8);
}

.drop-zone .file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.drop-zone-content {
  position: relative;
  display: grid;
  gap: 8px;
  min-height: 70px;
  align-items: center;
  justify-items: center;
  text-align: center;
  pointer-events: none;
}

.drop-zone-content p {
  margin: 0;
}

.drop-text {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 24px;
  font-weight: 700;
  color: rgb(28, 40, 118);
  background: rgba(255, 255, 255, 0.78);
  border-radius: 10px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  pointer-events: none;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.error-banner {
  padding: 13px 14px;
  border-radius: 14px;
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
}

.upload-layout-dark .hero-card,
.upload-layout-dark .endpoint-panel {
  background: rgba(255, 255, 255, 0.18);
}

.upload-layout-dark .drop-zone {
  background: rgba(255, 255, 255, 0.12);
}

.upload-layout-dark .drop-zone-active {
  background: rgba(255, 255, 255, 0.2);
}

.upload-layout-dark .drop-text {
  background: rgba(255, 255, 255, 0.24);
}

@media (max-width: 1080px) {
  .upload-layout,
  .hero-grid,
  .rule-entry-panel {
    grid-template-columns: 1fr;
  }
}
</style>

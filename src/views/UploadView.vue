<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { submitPaperMeta, uploadPaper } from "../services/api";
import {
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

function handleFileChange(event, field) {
  const [file] = event.target.files ?? [];
  form[field] = file ?? null;
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
</script>

<template>
  <section class="upload-layout">
    <div class="hero-panel glass-card">
      <span class="pill pill-accent">三页流程</span>
      <h1 class="section-title hero-title">上传论文，进入结构化评审工作台</h1>
      <p class="hero-text">
        这个前端已经按你的流程拆成三步：先上传，再进入论文与评语并排展示页，最后从推荐列表进入单篇推荐论文详情页。
      </p>

      <div class="hero-grid">
        <article class="hero-card">
          <strong>01 上传与传输</strong>
          <p>
            支持上传原始论文，同时预留 `paper.md`、`paper_meta.json`
            和图片基础路径；提交后会先把锚点 sidecar 发送给后端接口。
          </p>
        </article>
        <article class="hero-card">
          <strong>02 评审工作台</strong>
          <p>
            左侧展示 Markdown 论文内容，并支持切换“是否显示 Markdown
            中的图片”；右侧展示评语、维度评分和推荐论文列表。
          </p>
        </article>
        <article class="hero-card">
          <strong>03 推荐论文详情</strong>
          <p>
            点击推荐论文即可进入详情页，后续你只需要把真实检索接口接进来即可。
          </p>
        </article>
      </div>

      <div class="endpoint-panel">
        <span class="pill pill-primary">已预留接口</span>
        <ul>
          <li>`POST /papers/parse` 上传与解析论文</li>
          <li>`POST /papers/paper-meta` 发送 paper_meta.json</li>
          <li>`POST /reviews/generate` 生成评语</li>
          <li>`POST /recommendations` 获取推荐论文</li>
          <li>`GET /recommendations/:paperId` 获取推荐论文详情</li>
        </ul>
      </div>
    </div>

    <section class="form-panel glass-card">
      <div>
        <p class="summary-kicker">第一界面</p>
        <h2 class="section-title">上传论文</h2>
        <p class="section-subtitle">
          没接后端时会默认读取 `public/mock` 中的示例数据；接入真实后端后，只需要把
          `VITE_USE_MOCK` 改成 `false`。
        </p>
      </div>

      <div class="field-group">
        <label class="field-label" for="paper-file">论文文件</label>
        <input
          id="paper-file"
          class="file-input"
          type="file"
          accept=".pdf,.doc,.docx"
          @change="(event) => handleFileChange(event, 'paperFile')"
        />
        <span class="field-hint">真实后端联调时至少上传这个文件。</span>
      </div>

      <div class="field-group">
        <label class="field-label" for="markdown-file">解析后的 `paper.md`（可选）</label>
        <input
          id="markdown-file"
          class="file-input"
          type="file"
          accept=".md,.markdown,.txt"
          @change="(event) => handleFileChange(event, 'markdownFile')"
        />
      </div>

      <div class="field-group">
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
          {{ loading ? "正在提交..." : "提交并进入评审工作台" }}
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
.endpoint-panel {
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

.hero-card p,
.endpoint-panel ul {
  margin: 0;
  color: var(--muted);
}

.endpoint-panel {
  display: grid;
  gap: 14px;
}

.endpoint-panel ul {
  padding-left: 18px;
  display: grid;
  gap: 10px;
}

.form-panel {
  display: grid;
  gap: 18px;
  align-content: start;
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

@media (max-width: 1080px) {
  .upload-layout,
  .hero-grid {
    grid-template-columns: 1fr;
  }
}
</style>

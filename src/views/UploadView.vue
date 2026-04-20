<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { stagePendingUpload } from "../stores/pendingUpload";
import { clearSession } from "../stores/reviewSession";

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
  paperFile: false,
  markdownFile: false,
  documentIrFile: false
});

const demoAvailable = import.meta.env.VITE_USE_MOCK !== "false";

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

async function startReview(options = {}) {
  const { useDemo = false, mockProfile = "default" } = options;
  const hasAdvancedArtifacts = form.markdownFile && form.documentIrFile;

  if (!useDemo && !form.paperFile && !hasAdvancedArtifacts) {
    errorMessage.value =
      "请上传 PDF，或在高级导入中同时提供 `paper.md` 与 `paper_meta.json`。";
    return;
  }

  errorMessage.value = "";
  loading.value = true;

  try {
    clearSession();
    stagePendingUpload({
      useDemo,
      paperFile: useDemo ? null : form.paperFile,
      markdownFile: useDemo ? null : form.markdownFile,
      documentIrFile: useDemo ? null : form.documentIrFile,
      imageBaseUrl: useDemo ? "/mock" : form.imageBaseUrl,
      mockProfile
    });
    await router.push({ name: "loading" });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "提交失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
    <section class="upload-layout">
    <section class="hero-panel glass-card">
      <h1 class="section-title hero-title">上传论文，进入三阶段审查与汇总</h1>
      <p class="hero-text">
        当前业务入口收敛为 PDF 论文上传。解析模块保持不动，前端重点重构为“格式审查、逻辑审查、方法与创新点审查、汇总”四段式工作流。
      </p>

      <div class="journey-grid">
        <article class="journey-card">
          <strong>01 格式审查</strong>
          <p>左侧展示解析后的论文，右侧集中展示格式问题，并决定是否进入下一阶段。</p>
        </article>
        <article class="journey-card">
          <strong>02 逻辑审查</strong>
          <p>承接原有分析能力，聚焦论证链路和证据闭环，必要时直接提前进入汇总。</p>
        </article>
        <article class="journey-card">
          <strong>03 方法与创新点审查</strong>
          <p>审视方法陈述、创新点边界与实验支撑是否对应，完成后进入独立汇总页。</p>
        </article>
        <article class="journey-card">
          <strong>04 汇总</strong>
          <p>汇总页左侧展示问题与证据链，右侧展示修改建议与推荐论文，并支持详情跳转。</p>
        </article>
      </div>
    </section>

    <section class="form-panel glass-card">
      <div>
        <p class="summary-kicker">上传入口</p>
        <h2 class="section-title">上传 PDF 论文</h2>
        <p class="section-subtitle">
          默认以 PDF 为主入口；如果你已经拿到了 `paper.md` 和 `paper_meta.json`，也可以在下方高级导入中直接复用。
        </p>
      </div>

      <div
        class="field-group drop-zone"
        :class="{ 'drop-zone-active': dragOverField.paperFile }"
        @dragover.prevent="handleDragOver($event, 'paperFile')"
        @dragenter.prevent="handleDragOver($event, 'paperFile')"
        @dragleave.prevent="handleDragLeave('paperFile')"
        @drop.prevent="handleDrop($event, 'paperFile')"
      >
        <label class="field-label" for="paper-file">PDF 论文文件</label>
        <input
          id="paper-file"
          class="file-input"
          type="file"
          accept=".pdf"
          @change="(event) => handleFileChange(event, 'paperFile')"
        />
        <div class="drop-zone-content">
          <p>{{ form.paperFile ? form.paperFile.name : "拖拽 PDF 到此，或点击上传" }}</p>
          <p v-if="dragOverField.paperFile" class="drop-text">松手即可上传</p>
        </div>
        <span class="field-hint">上传 PDF 后会优先走本地解析接口；未接后端时可使用示例数据。</span>
      </div>

      <details class="advanced-block">
        <summary>高级导入</summary>

        <div class="advanced-grid">
          <div
            class="field-group drop-zone compact-drop-zone"
            :class="{ 'drop-zone-active': dragOverField.markdownFile }"
            @dragover.prevent="handleDragOver($event, 'markdownFile')"
            @dragenter.prevent="handleDragOver($event, 'markdownFile')"
            @dragleave.prevent="handleDragLeave('markdownFile')"
            @drop.prevent="handleDrop($event, 'markdownFile')"
          >
            <label class="field-label" for="markdown-file">`paper.md`</label>
            <input
              id="markdown-file"
              class="file-input"
              type="file"
              accept=".md,.markdown,.txt"
              @change="(event) => handleFileChange(event, 'markdownFile')"
            />
            <div class="drop-zone-content compact-drop-zone-content">
              <p>{{ form.markdownFile ? form.markdownFile.name : "可选上传" }}</p>
            </div>
          </div>

          <div
            class="field-group drop-zone compact-drop-zone"
            :class="{ 'drop-zone-active': dragOverField.documentIrFile }"
            @dragover.prevent="handleDragOver($event, 'documentIrFile')"
            @dragenter.prevent="handleDragOver($event, 'documentIrFile')"
            @dragleave.prevent="handleDragLeave('documentIrFile')"
            @drop.prevent="handleDrop($event, 'documentIrFile')"
          >
            <label class="field-label" for="document-ir-file">`paper_meta.json`</label>
            <input
              id="document-ir-file"
              class="file-input"
              type="file"
              accept=".json"
              @change="(event) => handleFileChange(event, 'documentIrFile')"
            />
            <div class="drop-zone-content compact-drop-zone-content">
              <p>{{ form.documentIrFile ? form.documentIrFile.name : "可选上传" }}</p>
            </div>
          </div>
        </div>

        <div class="field-group">
          <label class="field-label" for="image-base-url">静态资源基础路径</label>
          <input
            id="image-base-url"
            v-model="form.imageBaseUrl"
            class="text-input"
            type="text"
            placeholder="/mock"
          />
          <span class="field-hint">
            当你直接导入预解析产物时，可以在这里指定图像和表格资源的基础路径。
          </span>
        </div>
      </details>

      <div v-if="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <div class="button-row">
        <button
          class="primary-button"
          type="button"
          :disabled="loading"
          @click="startReview()"
        >
          {{ loading ? "正在提交..." : "提交并进入解析预览" }}
        </button>

        <button
          v-if="demoAvailable"
          class="ghost-button"
          type="button"
          :disabled="loading"
          @click="startReview({ useDemo: true })"
        >
          使用示例论文
        </button>

        <button
          v-if="demoAvailable"
          class="ghost-button"
          type="button"
          :disabled="loading"
          @click="startReview({ useDemo: true, mockProfile: 'logic-pass' })"
        >
          使用逻辑通过样例
        </button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.upload-layout {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
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
  line-height: 1.8;
  max-width: 720px;
}

.journey-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.journey-card {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  gap: 8px;
}

.journey-card strong {
  color: var(--primary);
}

.journey-card p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
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

.drop-zone {
  position: relative;
  border: 2px dashed rgba(94, 138, 223, 0.35);
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.compact-drop-zone {
  padding: 12px;
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
  min-height: 90px;
  align-items: center;
  justify-items: center;
  text-align: center;
  pointer-events: none;
}

.compact-drop-zone-content {
  min-height: 48px;
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
  border-radius: 12px;
  backdrop-filter: blur(8px);
}

.advanced-block {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(19, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.46);
  display: grid;
  gap: 16px;
}

.advanced-block summary {
  cursor: pointer;
  font-weight: 700;
  color: var(--primary);
}

.advanced-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
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
  .journey-grid,
  .advanced-grid {
    grid-template-columns: 1fr;
  }
}
</style>

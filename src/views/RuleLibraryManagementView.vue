<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  extractCustomRules,
  fetchSystemRuleLibrary,
  saveRuleSelection
} from "../services/api";
import { readFileAsText } from "../utils/file";
import {
  markRuleLibrarySaved,
  reviewSession,
  setCustomRuleFileName,
  setCustomRulesText,
  setCustomRuleSourceText,
  setRuleLibraryCatalog,
  setSelectedSystemRuleIds,
  toggleSystemRuleSelection
} from "../stores/reviewSession";

const router = useRouter();

const loadingSystemRules = ref(false);
const extractingRules = ref(false);
const savingRules = ref(false);
const pageMessage = ref("");
const errorMessage = ref("");
const uploadedRuleFile = ref(null);

const ruleLibrary = computed(() => reviewSession.ruleLibrary);
const systemRules = computed(() => ruleLibrary.value.systemRules);
const selectedSystemRuleIds = computed(() => ruleLibrary.value.selectedSystemRuleIds);
const selectedRuleCount = computed(() => selectedSystemRuleIds.value.length);
const hasCustomRules = computed(() => Boolean(ruleLibrary.value.customRulesText.trim()));

async function loadSystemRules() {
  loadingSystemRules.value = true;
  errorMessage.value = "";

  try {
    const rules = await fetchSystemRuleLibrary();
    setRuleLibraryCatalog(rules);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "系统规则库加载失败";
  } finally {
    loadingSystemRules.value = false;
  }
}

function isSelected(ruleId) {
  return selectedSystemRuleIds.value.includes(ruleId);
}

function toggleRule(ruleId) {
  toggleSystemRuleSelection(ruleId);
  pageMessage.value = "";
}

function resetSystemSelection() {
  const defaultIds = systemRules.value
    .filter((item) => item.defaultSelected)
    .map((item) => item.id);

  setSelectedSystemRuleIds(defaultIds);
  pageMessage.value = "";
}

async function handleTextFileChange(event) {
  const [file] = event.target.files ?? [];
  if (!file) {
    return;
  }

  try {
    const text = await readFileAsText(file);
    uploadedRuleFile.value = file;
    setCustomRuleFileName(file.name);
    setCustomRuleSourceText(text);
    pageMessage.value = `已读取文件：${file.name}`;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "文本文件读取失败";
  }
}

async function handleExtractRules() {
  extractingRules.value = true;
  errorMessage.value = "";
  pageMessage.value = "";

  try {
    const result = await extractCustomRules({
      file: uploadedRuleFile.value,
      text: ruleLibrary.value.customRuleSourceText
    });

    setCustomRuleSourceText(result.sourceText ?? ruleLibrary.value.customRuleSourceText);
    setCustomRulesText(result.extractedRulesText ?? "");
    pageMessage.value = "自建规则已抽取完成，可在下方编辑框继续修改。";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "自建规则抽取失败";
  } finally {
    extractingRules.value = false;
  }
}

async function saveCurrentSelection() {
  savingRules.value = true;
  errorMessage.value = "";
  pageMessage.value = "";

  try {
    const result = await saveRuleSelection({
      selectedSystemRuleIds: selectedSystemRuleIds.value,
      customRulesText: ruleLibrary.value.customRulesText
    });

    markRuleLibrarySaved(result.savedAt ?? new Date().toISOString());
    pageMessage.value = "规则配置已保存，后续第二页可以直接消费这份配置。";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "规则配置保存失败";
  } finally {
    savingRules.value = false;
  }
}

function goBackToUpload() {
  router.push({ name: "upload" });
}

onMounted(() => {
  if (!systemRules.value.length) {
    loadSystemRules();
  }
});
</script>

<template>
  <section class="rule-library-layout">
    <section class="overview-panel glass-card">
      <div class="overview-head">
        <div class="overview-spacer" aria-hidden="true"></div>
        <div class="overview-title-block">
          <p class="summary-kicker">规则库管理</p>
          <h1 class="section-title">筛选系统规则，并维护自建规则库</h1>
        </div>
        <div class="overview-actions">
          <button class="ghost-button" type="button" @click="goBackToUpload">
            返回上传页
          </button>
          <button
            class="primary-button"
            type="button"
            :disabled="savingRules"
            @click="saveCurrentSelection"
          >
            {{ savingRules ? "正在保存..." : "保存当前规则配置" }}
          </button>
        </div>
      </div>

      <p class="overview-text">
        页面分为两部分：上半区用于筛选系统标准规则库，下半区用于上传文本并抽取用户自建规则。后续后端返回选中规则下的问题反馈时，可以直接沿用这里保存的选择结果。
      </p>

      <div class="overview-stats">
        <div class="metric-card">
          <span>系统规则已选</span>
          <strong>{{ selectedRuleCount }}</strong>
        </div>
        <div class="metric-card">
          <span>自建规则状态</span>
          <strong>{{ hasCustomRules ? "已抽取" : "待抽取" }}</strong>
        </div>
        <div class="metric-card">
          <span>最近保存时间</span>
          <strong>{{ ruleLibrary.savedAt ? new Date(ruleLibrary.savedAt).toLocaleString() : "未保存" }}</strong>
        </div>
      </div>

      <div v-if="pageMessage" class="success-banner">{{ pageMessage }}</div>
      <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>
    </section>

    <section class="management-panel">
      <article class="library-card glass-card">
        <div class="card-head">
          <div>
            <span class="pill pill-accent">系统标准规则库</span>
            <h2 class="section-title">筛选系统预置规则</h2>
            <p class="section-subtitle">
              后端可以在这里返回系统标准规则列表，前端支持勾选后保存选中结果。
            </p>
          </div>
          <div class="button-row">
            <button
              class="ghost-button"
              type="button"
              :disabled="loadingSystemRules"
              @click="loadSystemRules"
            >
              {{ loadingSystemRules ? "刷新中..." : "刷新规则库" }}
            </button>
            <button class="ghost-button" type="button" @click="resetSystemSelection">
              恢复默认选择
            </button>
          </div>
        </div>

        <div class="rule-grid">
          <label
            v-for="rule in systemRules"
            :key="rule.id"
            class="rule-card"
            :class="{ selected: isSelected(rule.id) }"
          >
            <input
              class="rule-checkbox"
              type="checkbox"
              :checked="isSelected(rule.id)"
              @change="toggleRule(rule.id)"
            />
            <div class="rule-card-content">
              <div class="rule-card-headline">
                <strong>{{ rule.title }}</strong>
                <span class="rule-category">{{ rule.category }}</span>
              </div>
              <p>{{ rule.summary }}</p>
              <div class="rule-meta">
                <span>{{ `问题数 ${rule.questionCount ?? 0}` }}</span>
                <span
                  v-for="tag in rule.tags"
                  :key="`${rule.id}-${tag}`"
                  class="rule-tag"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </label>
        </div>
      </article>

      <article class="library-card glass-card">
        <div class="card-head">
          <div>
            <span class="pill pill-primary">用户自建规则库</span>
            <h2 class="section-title">上传文本并抽取规则</h2>
            <p class="section-subtitle">
              这里预留了给后端调用大模型抽取规则的接口，返回结果会展示在可编辑文本框中。
            </p>
          </div>
          <button
            class="secondary-button"
            type="button"
            :disabled="extractingRules"
            @click="handleExtractRules"
          >
            {{ extractingRules ? "抽取中..." : "抽取自建规则" }}
          </button>
        </div>

        <div class="grid-two">
          <div class="field-group">
            <label class="field-label" for="custom-rule-file">上传规则说明文本</label>
            <input
              id="custom-rule-file"
              class="file-input"
              type="file"
              accept=".txt,.md"
              @change="handleTextFileChange"
            />
            <span class="field-hint">
              {{ ruleLibrary.customRuleFileName ? `当前文件：${ruleLibrary.customRuleFileName}` : "支持 txt 或 md 文本文件" }}
            </span>
          </div>

          <div class="field-group">
            <label class="field-label" for="custom-rule-source">原始规则说明</label>
            <textarea
              id="custom-rule-source"
              class="text-area"
              :value="ruleLibrary.customRuleSourceText"
              placeholder="在这里粘贴规则说明，或先上传文本文件。"
              @input="setCustomRuleSourceText($event.target.value)"
            />
            <span class="field-hint">后端可直接消费这里的文本做规则抽取。</span>
          </div>
        </div>

        <div class="field-group">
          <label class="field-label" for="custom-rule-result">抽取后的规则编辑框</label>
          <textarea
            id="custom-rule-result"
            class="text-area result-area"
            :value="ruleLibrary.customRulesText"
            placeholder="抽取完成后，规则会显示在这里，并支持手动编辑。"
            @input="setCustomRulesText($event.target.value)"
          />
          <span class="field-hint">这里保留最终给后端或后续页面使用的自建规则文本。</span>
        </div>
      </article>
    </section>
  </section>
</template>

<style scoped>
.rule-library-layout {
  display: grid;
  gap: 22px;
}

.overview-panel,
.library-card {
  padding: 28px;
}

.overview-panel {
  display: grid;
  gap: 18px;
}

.overview-head,
.card-head {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}

.overview-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 760px) minmax(0, 1fr);
  align-items: start;
}

.overview-spacer {
  min-height: 1px;
}

.overview-title-block {
  width: 100%;
  justify-self: center;
  text-align: center;
}

.overview-title-block .section-title {
  margin-bottom: 0;
}

.overview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-self: end;
}

.overview-text {
  margin: 0;
  color: var(--muted);
  font-size: 17px;
  max-width: 900px;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  gap: 8px;
}

.metric-card span {
  color: var(--muted);
  font-size: 14px;
}

.metric-card strong {
  font-size: 24px;
  color: var(--primary);
}

.management-panel {
  display: grid;
  gap: 22px;
}

.library-card {
  display: grid;
  gap: 20px;
}

.rule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.rule-card {
  display: flex;
  gap: 14px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(19, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.58);
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.rule-card:hover {
  transform: translateY(-2px);
}

.rule-card.selected {
  border-color: rgba(50, 96, 197, 0.48);
  box-shadow: 0 18px 34px rgba(25, 49, 115, 0.1);
}

.rule-checkbox {
  margin-top: 4px;
}

.rule-card-content {
  display: grid;
  gap: 10px;
}

.rule-card-headline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.rule-card p {
  margin: 0;
  color: var(--muted);
}

.rule-category,
.rule-tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
}

.rule-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  color: var(--muted);
  font-size: 13px;
}

.text-area {
  min-height: 180px;
  resize: vertical;
  border-radius: 16px;
  border: 1px solid rgba(19, 63, 103, 0.14);
  background: rgba(255, 255, 255, 0.78);
  padding: 14px 16px;
  font: inherit;
  color: var(--text);
}

.result-area {
  min-height: 220px;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.success-banner,
.error-banner {
  padding: 13px 14px;
  border-radius: 14px;
}

.success-banner {
  background: rgba(46, 125, 92, 0.12);
  border: 1px solid rgba(46, 125, 92, 0.18);
  color: #1e6d4a;
}

.error-banner {
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
}

@media (max-width: 1080px) {
  .overview-stats,
  .rule-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .overview-head,
  .card-head {
    flex-direction: column;
  }

  .overview-head {
    grid-template-columns: 1fr;
  }

  .overview-spacer {
    display: none;
  }

  .overview-actions {
    justify-self: start;
  }
}
</style>

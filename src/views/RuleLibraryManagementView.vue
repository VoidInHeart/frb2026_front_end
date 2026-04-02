<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { appearanceState } from "../stores/appearance";
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

const editingCustomRules = ref(false);
const showingAddRuleForm = ref(false);
const uploadedRuleFile = ref(null);
const draftSourceText = ref("");
const draftExtractedRulesText = ref("");
const draftFileName = ref("");

const ruleLibrary = computed(() => reviewSession.ruleLibrary);
const systemRules = computed(() => ruleLibrary.value.systemRules);
const selectedSystemRuleIds = computed(() => ruleLibrary.value.selectedSystemRuleIds);
const selectedRuleCount = computed(() => selectedSystemRuleIds.value.length);
const hasCustomRules = computed(() => Boolean(ruleLibrary.value.customRulesText.trim()));
const customRuleItems = computed(() => parseRuleLines(ruleLibrary.value.customRulesText));

function normalizeRuleLine(line) {
  return line.replace(/^\d+[.)、]\s*/, "").trim();
}

function parseRuleLines(text) {
  return text
    .split(/\r?\n/)
    .map((line) => normalizeRuleLine(line))
    .filter(Boolean);
}

function serializeRuleLines(items) {
  return items.map((item, index) => `${index + 1}. ${item}`).join("\n");
}

function resetDraftState() {
  uploadedRuleFile.value = null;
  draftSourceText.value = "";
  draftExtractedRulesText.value = "";
  draftFileName.value = "";
}

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

function toggleCustomRuleEditMode() {
  editingCustomRules.value = !editingCustomRules.value;

  if (!editingCustomRules.value) {
    showingAddRuleForm.value = false;
    resetDraftState();
  }

  pageMessage.value = "";
  errorMessage.value = "";
}

function openAddRuleForm() {
  showingAddRuleForm.value = true;
  pageMessage.value = "";
  errorMessage.value = "";

  if (!draftSourceText.value && ruleLibrary.value.customRuleSourceText) {
    draftSourceText.value = ruleLibrary.value.customRuleSourceText;
  }
}

function cancelAddRule() {
  showingAddRuleForm.value = false;
  resetDraftState();
  errorMessage.value = "";
}

function removeCustomRule(index) {
  const nextItems = [...customRuleItems.value];
  nextItems.splice(index, 1);

  setCustomRulesText(serializeRuleLines(nextItems));
  pageMessage.value = "已删除选中的自建规则。";
}

async function handleDraftTextFileChange(event) {
  const [file] = event.target.files ?? [];
  if (!file) {
    return;
  }

  try {
    const text = await readFileAsText(file);
    uploadedRuleFile.value = file;
    draftFileName.value = file.name;
    draftSourceText.value = text;
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
      text: draftSourceText.value
    });

    draftSourceText.value = result.sourceText ?? draftSourceText.value;
    draftExtractedRulesText.value =
      result.extractedRulesText ?? (result.rules ?? []).join("\n");
    pageMessage.value = "规则抽取完成，请确认后提交到自建规则库。";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "自建规则抽取失败";
  } finally {
    extractingRules.value = false;
  }
}

function confirmAddRules() {
  const newItems = parseRuleLines(draftExtractedRulesText.value);

  if (!newItems.length) {
    errorMessage.value = "请先抽取规则，或在编辑框里填写至少一条规则后再提交。";
    return;
  }

  const mergedItems = [...customRuleItems.value, ...newItems];
  setCustomRulesText(serializeRuleLines(mergedItems));
  setCustomRuleSourceText(draftSourceText.value);
  setCustomRuleFileName(draftFileName.value);

  pageMessage.value = `已新增 ${newItems.length} 条自建规则。`;
  showingAddRuleForm.value = false;
  resetDraftState();
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
  <section
    :class="[
      'rule-library-layout',
      { 'rule-library-layout-dark': ['dark', 'sci-fi'].includes(appearanceState.theme) }
    ]"
  >
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
        页面分为两部分：上半区用于筛选系统标准规则库，下半区用于维护用户自建规则。后续后端返回选中规则下的问题反馈时，可以直接沿用这里保存的选择结果。
      </p>

      <div class="overview-stats">
        <div class="metric-card">
          <span>系统规则已选</span>
          <strong>{{ selectedRuleCount }}</strong>
        </div>
        <div class="metric-card">
          <span>自建规则状态</span>
          <strong>{{ hasCustomRules ? "已配置" : "待配置" }}</strong>
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
            <h2 class="section-title">先展示已有规则，再进入编辑态</h2>
            <p class="section-subtitle">
              默认先展示当前已有的自建规则；点击右上角“编辑规则”后，可以删除规则或新增规则。
            </p>
          </div>
          <button class="secondary-button" type="button" @click="toggleCustomRuleEditMode">
            {{ editingCustomRules ? "完成编辑" : "编辑规则" }}
          </button>
        </div>

        <div class="custom-rule-list">
          <article
            v-for="(rule, index) in customRuleItems"
            :key="`${index}-${rule}`"
            class="custom-rule-card"
          >
            <div class="custom-rule-body">
              <span class="custom-rule-index">{{ `${index + 1}`.padStart(2, "0") }}</span>
              <p>{{ rule }}</p>
            </div>
            <button
              v-if="editingCustomRules"
              class="ghost-button compact-button"
              type="button"
              @click="removeCustomRule(index)"
            >
              删除
            </button>
          </article>

          <div v-if="!customRuleItems.length" class="empty-state custom-rule-empty">
            <p>当前还没有自建规则。</p>
            <p>点击“编辑规则”后即可新增并确认提交。</p>
          </div>
        </div>

        <div v-if="editingCustomRules" class="edit-toolbar">
          <button class="ghost-button" type="button" @click="openAddRuleForm">
            新增规则
          </button>
          <span class="field-hint">
            可以像成员管理一样先看已有条目，再按需删除或新增。
          </span>
        </div>

        <section v-if="editingCustomRules && showingAddRuleForm" class="draft-editor">
          <div class="draft-editor-head">
            <div>
              <h3>新增规则</h3>
              <p>这里保留上传文本、抽取规则和手动编辑的流程。</p>
            </div>
            <button class="ghost-button" type="button" @click="cancelAddRule">
              取消
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
                @change="handleDraftTextFileChange"
              />
              <span class="field-hint">
                {{ draftFileName ? `当前文件：${draftFileName}` : "支持 txt 或 md 文本文件" }}
              </span>
            </div>

            <div class="field-group">
              <label class="field-label" for="custom-rule-source">原始规则说明</label>
              <textarea
                id="custom-rule-source"
                class="text-area"
                :value="draftSourceText"
                placeholder="在这里粘贴规则说明，或先上传文本文件。"
                @input="draftSourceText = $event.target.value"
              />
              <span class="field-hint">后端可直接消费这里的文本做规则抽取。</span>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label" for="custom-rule-result">抽取后的规则编辑框</label>
            <textarea
              id="custom-rule-result"
              class="text-area result-area"
              :value="draftExtractedRulesText"
              placeholder="抽取完成后，规则会显示在这里，并支持手动修改。"
              @input="draftExtractedRulesText = $event.target.value"
            />
            <span class="field-hint">每一行视为一条规则，确认提交后会加入上面的自建规则列表。</span>
          </div>

          <div class="button-row">
            <button
              class="secondary-button"
              type="button"
              :disabled="extractingRules"
              @click="handleExtractRules"
            >
              {{ extractingRules ? "抽取中..." : "抽取规则" }}
            </button>
            <button class="primary-button" type="button" @click="confirmAddRules">
              确认提交新增规则
            </button>
          </div>
        </section>
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

.custom-rule-list {
  display: grid;
  gap: 12px;
}

.custom-rule-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(19, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.58);
}

.custom-rule-body {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  min-width: 0;
}

.custom-rule-body p {
  margin: 0;
  color: var(--text);
  line-height: 1.6;
}

.custom-rule-index {
  min-width: 38px;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
  text-align: center;
  font-size: 12px;
  font-weight: 700;
}

.custom-rule-empty {
  min-height: 120px;
}

.compact-button {
  min-width: 72px;
}

.edit-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.draft-editor {
  display: grid;
  gap: 18px;
  padding: 22px;
  border-radius: 22px;
  border: 1px dashed rgba(50, 96, 197, 0.34);
  background: rgba(255, 255, 255, 0.48);
}

.draft-editor-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.draft-editor-head h3,
.draft-editor-head p {
  margin: 0;
}

.draft-editor-head p {
  color: var(--muted);
  margin-top: 6px;
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

.rule-library-layout-dark .metric-card,
.rule-library-layout-dark .rule-card,
.rule-library-layout-dark .custom-rule-card,
.rule-library-layout-dark .draft-editor,
.rule-library-layout-dark .text-area {
  background: rgba(255, 255, 255, 0.12) !important;
  border-color: rgba(124, 195, 255, 0.16) !important;
  box-shadow: none !important;
}

.rule-library-layout-dark .rule-category,
.rule-library-layout-dark .rule-tag,
.rule-library-layout-dark .custom-rule-index {
  background: rgba(255, 255, 255, 0.12) !important;
  border: 1px solid rgba(124, 195, 255, 0.16) !important;
}

.rule-library-layout-dark .rule-card.selected {
  border-color: rgba(124, 195, 255, 0.34);
  box-shadow: none;
}

.rule-library-layout-dark .metric-card span,
.rule-library-layout-dark .rule-card p,
.rule-library-layout-dark .custom-rule-body p,
.rule-library-layout-dark .draft-editor-head p,
.rule-library-layout-dark .field-hint {
  color: #d7e3f1;
}

@media (max-width: 1080px) {
  .overview-stats,
  .rule-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .overview-head,
  .card-head,
  .draft-editor-head,
  .custom-rule-card {
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

  .custom-rule-card {
    align-items: stretch;
  }
}
</style>

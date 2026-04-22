import { readFileAsJson, readFileAsText } from "../utils/file";
import {
  APP_API_ENDPOINTS,
  LOCAL_PARSER_ENDPOINTS,
  UPLOAD_FORM_FIELDS
} from "./apiContract";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const PARSER_API_BASE_URL =
  import.meta.env.VITE_PARSER_API_BASE_URL || "http://127.0.0.1:8000";
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const USE_LOCAL_PARSER = import.meta.env.VITE_USE_LOCAL_PARSER !== "false";
const MOCK_RUN_STORAGE_KEY = "paper-review-mock-runs-v1";

const RUN_API_ENDPOINTS = Object.freeze({
  createRun: {
    method: "POST",
    path: "/runs"
  },
  getRunState: {
    method: "GET",
    path: "/runs/:runId/state"
  },
  triggerStage: {
    method: "POST",
    path: "/runs/:runId/stages/:stageName"
  },
  getStage: {
    method: "GET",
    path: "/runs/:runId/stages/:stageName"
  },
  getSummary: {
    method: "GET",
    path: "/runs/:runId/summary"
  },
  getRecommendations: {
    method: "GET",
    path: "/runs/:runId/recommendations"
  }
});

const REVIEW_STAGE_ORDER = Object.freeze([
  "format",
  "logic",
  "innovation",
  "summary"
]);

const REVIEW_STAGE_LABELS = Object.freeze({
  format: "格式审查",
  logic: "逻辑审查",
  innovation: "方法与创新点审查",
  summary: "汇总"
});

const RULE_LABELS = Object.freeze({
  "R-PF-DEMO-001": "文档结构与缩写预筛",
  "R-PF-REF-001": "参考文献噪声过滤",
  "R-TC-001": "术语与缩写一致性检查",
  "LOGIC-AUDIT-ISSUE": "逻辑链路审查"
});

const FINAL_STAGE_STATUSES = new Set([
  "completed",
  "skipped",
  "failed",
  "aborted"
]);

const LOCAL_PARSER_PROGRESS_POLL_MS = 500;

const mockRecommendations = [
  {
    id: "retrieval-augmented-peer-review",
    title: "Retrieval-Augmented Peer Review for Scientific Writing",
    authors: "L. Martin, J. Xu, H. Zhao",
    year: 2025,
    venue: "ACL",
    relevanceScore: 95,
    reason: "围绕学术论文评审中的证据检索与意见生成，适合作为系统设计参考。",
    keywords: ["peer review", "retrieval", "scientific writing"]
  },
  {
    id: "diffusion-forgery-benchmark",
    title: "Benchmarking Diffusion Forgery Detection with Multi-View Evidence",
    authors: "C. Wang, R. Patel, Y. Luo",
    year: 2024,
    venue: "CVPR",
    relevanceScore: 91,
    reason: "与当前论文的扩散生成伪造检测任务高度相关，可作为实验对比文献。",
    keywords: ["diffusion", "forgery detection", "benchmark"]
  },
  {
    id: "scholar-review-agent",
    title: "Scholar Review Agent: Structured Critique Generation for Research Papers",
    authors: "A. Singh, M. Chen",
    year: 2025,
    venue: "EMNLP Findings",
    relevanceScore: 88,
    reason: "强调结构化维度评分与改进建议生成，和右侧评语模块目标贴合。",
    keywords: ["LLM", "critique", "structured scoring"]
  }
];

const mockRecommendationDetails = {
  "retrieval-augmented-peer-review": {
    id: "retrieval-augmented-peer-review",
    title: "Retrieval-Augmented Peer Review for Scientific Writing",
    authors: "L. Martin, J. Xu, H. Zhao",
    year: 2025,
    venue: "ACL",
    relevanceScore: 95,
    abstract:
      "This paper proposes a retrieval-augmented architecture that grounds review comments in matched evidence from prior scientific papers and policy rubrics.",
    relevanceAnalysis:
      "这篇论文与当前系统中的推荐论文、评语生成链路高度一致，适合作为检索增强审稿的方法参考，也能帮助定义推荐理由字段。",
    keyTakeaways: [
      "将检索证据与评审维度绑定，减少空泛评语。",
      "推荐模块与评语模块共享底层表示，有助于降低系统耦合度。",
      "适合作为后续把锚点列表接入 RAG 流程的设计样板。"
    ],
    keywords: ["peer review", "retrieval", "grounding"],
    link: "#"
  },
  "diffusion-forgery-benchmark": {
    id: "diffusion-forgery-benchmark",
    title: "Benchmarking Diffusion Forgery Detection with Multi-View Evidence",
    authors: "C. Wang, R. Patel, Y. Luo",
    year: 2024,
    venue: "CVPR",
    relevanceScore: 91,
    abstract:
      "We revisit diffusion forgery detection using multi-view evidence spanning image artifacts, semantic clues, and synthetic trace analysis.",
    relevanceAnalysis:
      "如果你的论文主题聚焦扩散伪造检测，这篇工作可以直接作为相关工作与实验对标项，尤其适合展示 benchmark 和多维证据分析。",
    keyTakeaways: [
      "适合作为 related work 页面中的强相关基线。",
      "可帮助解释锚点列表如何映射到检测证据。",
      "能为推荐列表提供更可信的相似任务来源。"
    ],
    keywords: ["diffusion", "forgery detection", "evidence"],
    link: "#"
  },
  "scholar-review-agent": {
    id: "scholar-review-agent",
    title: "Scholar Review Agent: Structured Critique Generation for Research Papers",
    authors: "A. Singh, M. Chen",
    year: 2025,
    venue: "EMNLP Findings",
    relevanceScore: 88,
    abstract:
      "Scholar Review Agent decomposes paper assessment into novelty, technical depth, clarity, and experimental sufficiency, then synthesizes actionable critique.",
    relevanceAnalysis:
      "与当前前端右侧展示的分维度评分、优缺点和改进建议非常契合，适合借鉴字段设计与交互呈现。",
    keyTakeaways: [
      "支持多维度评分卡展示。",
      "强调摘要评论与可执行建议的双层输出结构。",
      "适合作为后续真实接口返回格式的参考。"
    ],
    keywords: ["review agent", "critique generation", "scoring"],
    link: "#"
  }
};

const mockSystemRuleLibraries = [
  {
    id: "system-clarity-001",
    title: "论文结构完整性",
    category: "结构规范",
    summary: "检查摘要、引言、方法、实验、结论等核心章节是否齐全且层次清晰。",
    tags: ["章节结构", "摘要", "实验"],
    questionCount: 6,
    defaultSelected: true
  },
  {
    id: "system-method-002",
    title: "方法描述严谨性",
    category: "技术内容",
    summary: "关注模型设定、符号定义、训练流程和关键超参数是否交代清楚。",
    tags: ["方法", "公式", "超参数"],
    questionCount: 8,
    defaultSelected: true
  },
  {
    id: "system-experiment-003",
    title: "实验设计充分性",
    category: "实验评估",
    summary: "检查数据集、基线、评价指标、消融实验和误差分析是否充分。",
    tags: ["实验", "基线", "消融"],
    questionCount: 10,
    defaultSelected: false
  },
  {
    id: "system-writing-004",
    title: "学术写作表达",
    category: "表达质量",
    summary: "评估术语一致性、图表说明、语言流畅性以及结论是否与证据匹配。",
    tags: ["写作", "图表", "一致性"],
    questionCount: 5,
    defaultSelected: false
  }
];

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }

  return response.json();
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function ensureObject(value) {
  return isPlainObject(value) ? value : {};
}

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function coerceStageName(stageName, fallback = "format") {
  return REVIEW_STAGE_ORDER.includes(stageName) ? stageName : fallback;
}

function buildApiUrl(pathTemplate, params = {}) {
  let path = pathTemplate;

  for (const [key, value] of Object.entries(params)) {
    path = path.replace(`:${key}`, encodeURIComponent(String(value ?? "")));
  }

  return `${API_BASE_URL}${path}`;
}

function createApiError({
  message,
  code = "REQUEST_FAILED",
  status = 500,
  data = null
}) {
  const error = new Error(message);
  error.code = code;
  error.status = status;
  error.data = data;
  return error;
}

async function fetchEnvelope(pathTemplate, options = {}, params = {}) {
  const response = await fetch(buildApiUrl(pathTemplate, params), options);

  let payload = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok || payload?.ok === false) {
    throw createApiError({
      message: payload?.message ?? `请求失败: ${response.status}`,
      code: payload?.code ?? `HTTP_${response.status}`,
      status: response.status,
      data: payload?.data ?? null
    });
  }

  return payload ?? {
    ok: true,
    code: "OK",
    message: "success",
    data: null
  };
}

function formatUploadBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "unknown";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function parseXhrJsonResponse(xhr) {
  try {
    return xhr.responseText ? JSON.parse(xhr.responseText) : null;
  } catch {
    return null;
  }
}

async function requestJsonWithUploadProgress(
  url,
  options = {},
  requestLabel = "upload",
  listeners = {}
) {
  if (typeof XMLHttpRequest === "undefined" || !options?.body) {
    return fetchJson(url, options);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let lastLoggedPercent = -5;
    let lastLoggedLoaded = 0;

    xhr.open(options.method ?? "POST", url, true);

    for (const [header, value] of Object.entries(options.headers ?? {})) {
      xhr.setRequestHeader(header, value);
    }

    console.info(`[upload] ${requestLabel} started`);

    xhr.upload.addEventListener("progress", (event) => {
      const fraction =
        event.lengthComputable && event.total > 0 ? event.loaded / event.total : null;

      if (typeof listeners.onUploadProgress === "function") {
        listeners.onUploadProgress({
          loaded: event.loaded,
          total: event.total,
          lengthComputable: event.lengthComputable,
          fraction,
          percent: fraction === null ? null : Math.round(fraction * 1000) / 10
        });
      }

      if (!event.lengthComputable) {
        if (event.loaded - lastLoggedLoaded >= 1024 * 1024) {
          lastLoggedLoaded = event.loaded;
          console.info(
            `[upload] ${requestLabel}: uploaded ${formatUploadBytes(event.loaded)}`
          );
        }
        return;
      }

      const percent = Math.floor((event.loaded / event.total) * 100);

      if (percent >= lastLoggedPercent + 5 || percent === 100) {
        lastLoggedPercent = percent;
        lastLoggedLoaded = event.loaded;
        console.info(
          `[upload] ${requestLabel}: ${percent}% (${formatUploadBytes(event.loaded)} / ${formatUploadBytes(event.total)})`
        );
      }
    });

    xhr.addEventListener("load", () => {
      const payload = parseXhrJsonResponse(xhr);

      if (xhr.status >= 200 && xhr.status < 300) {
        console.info(`[upload] ${requestLabel} completed with HTTP ${xhr.status}`);
        resolve(payload);
        return;
      }

      reject(
        createApiError({
          message: payload?.message ?? `请求失败: ${xhr.status}`,
          code: payload?.code ?? `HTTP_${xhr.status}`,
          status: xhr.status,
          data: payload?.data ?? null
        })
      );
    });

    xhr.addEventListener("error", () => {
      reject(new Error("网络请求失败"));
    });

    xhr.addEventListener("abort", () => {
      reject(new Error("请求已取消"));
    });

    xhr.send(options.body);
  });
}

function readMockRunStore() {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    return JSON.parse(window.sessionStorage.getItem(MOCK_RUN_STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function writeMockRunStore(store) {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(MOCK_RUN_STORAGE_KEY, JSON.stringify(store));
}

function saveMockRun(run) {
  const store = readMockRunStore();
  store[run.runId] = run;
  writeMockRunStore(store);
}

function getMockRun(runId) {
  return readMockRunStore()[runId] ?? null;
}

function requireMockRun(runId) {
  const run = getMockRun(runId);

  if (!run) {
    throw createApiError({
      message: "mock run not found",
      code: "RUN_NOT_FOUND",
      status: 404
    });
  }

  return run;
}

function createEmptyStageRuns() {
  return REVIEW_STAGE_ORDER.map((stageName) => ({
    stage_name: stageName,
    status: "pending"
  }));
}

function getNextStageName(stageName) {
  const index = REVIEW_STAGE_ORDER.indexOf(stageName);

  if (index === -1 || index === REVIEW_STAGE_ORDER.length - 1) {
    return null;
  }

  return REVIEW_STAGE_ORDER[index + 1];
}

function normalizeRunRecord(payload) {
  const data = ensureObject(payload?.data ?? payload);

  return {
    runId: data.run_id ?? data.runId ?? "",
    status: data.status ?? "created",
    currentStage: coerceStageName(
      data.current_stage ?? data.currentStage ?? data.next_stage ?? data.nextStage,
      "format"
    ),
    acceptedAt: data.accepted_at ?? data.acceptedAt ?? null,
    raw: data
  };
}

function normalizeStageRuns(stageRuns = []) {
  const byStage = new Map();

  for (const item of ensureArray(stageRuns)) {
    const stageName = coerceStageName(item?.stage_name ?? item?.stageName, null);

    if (!stageName) {
      continue;
    }

    byStage.set(stageName, {
      stageName,
      status: item?.status ?? "pending"
    });
  }

  return REVIEW_STAGE_ORDER.map((stageName) => ({
    stageName,
    status: byStage.get(stageName)?.status ?? "pending"
  }));
}

function estimateRunProgress(stageRuns = []) {
  const progressByStatus = {
    completed: 25,
    skipped: 25,
    failed: 25,
    aborted: 25,
    running: 12,
    waiting: 12,
    pending: 0
  };

  const progress = normalizeStageRuns(stageRuns).reduce(
    (total, item) => total + (progressByStatus[item.status] ?? 0),
    0
  );

  return Math.max(0, Math.min(100, progress));
}

function normalizeRunState(payload) {
  const data = ensureObject(payload?.data ?? payload);
  const stageRuns = normalizeStageRuns(data.stage_runs ?? data.stageRuns);
  const nextStage = coerceStageName(
    data.next_stage ?? data.nextStage ?? data.current_stage ?? data.currentStage,
    "format"
  );

  return {
    runId: data.run_id ?? data.runId ?? "",
    status: data.status ?? "created",
    currentStage: coerceStageName(
      data.current_stage ?? data.currentStage ?? nextStage,
      nextStage
    ),
    nextStage,
    allowedActions: ensureArray(data.allowed_actions ?? data.allowedActions).map(String),
    progress:
      typeof data.progress === "number"
        ? data.progress
        : estimateRunProgress(stageRuns),
    stageRuns,
    lastError: data.last_error ?? data.lastError ?? "",
    blockReasonCode: data.block_reason_code ?? data.blockReasonCode ?? "",
    blockReasonMessage:
      data.block_reason_message ?? data.blockReasonMessage ?? "",
    raw: data
  };
}

function getStageRunStatus(runState, stageName) {
  return (
    normalizeStageRuns(runState?.stageRuns ?? runState?.stage_runs)
      .find((item) => item.stageName === stageName)
      ?.status ?? "pending"
  );
}

function extractStagePayload(source) {
  const data = ensureObject(source?.data ?? source);

  return {
    stageStatus: data.stage_status ?? data.stageStatus ?? "completed",
    stageOutput: ensureObject(
      data.stage_output ??
        data.stageOutput ??
        data.result ??
        data.stage_result ??
        data.stageResult
    ),
    raw: data
  };
}

function looksLikeStageReview(value) {
  return (
    isPlainObject(value) &&
    Array.isArray(value.issues) &&
    (typeof value.headline === "string" ||
      typeof value.overview === "string" ||
      typeof value.stageLabel === "string")
  );
}

function attachStageReviewMeta(review, stageName, stageStatus, rawData) {
  return {
    ...review,
    stageId: review.stageId ?? stageName,
    stageLabel: review.stageLabel ?? REVIEW_STAGE_LABELS[stageName],
    stageStatus,
    severe: Boolean(review.severe),
    rawData: rawData ?? review.rawData ?? null
  };
}

function normalizeEvidenceList(value, fallbackMessage = "未返回结构化证据") {
  const normalized = ensureArray(value)
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }

      if (item == null) {
        return "";
      }

      return String(item);
    })
    .filter(Boolean)
    .slice(0, 6);

  return normalized.length ? normalized : [fallbackMessage];
}

function getRuleDisplayLabel(ruleId, fallback = "") {
  const normalizedRuleId = String(ruleId ?? "").trim();
  if (!normalizedRuleId) {
    return fallback;
  }

  return RULE_LABELS[normalizedRuleId] ?? fallback ?? normalizedRuleId;
}

function normalizeIssueFingerprintText(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff\s]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function getIssueSeverityRank(severity) {
  if (severity === "严重") {
    return 3;
  }

  if (severity === "一般") {
    return 2;
  }

  return 1;
}

function extractIssueSubjectToken(issue) {
  const source = [
    issue.title,
    issue.description,
    ...(ensureArray(issue.evidence) ?? [])
  ]
    .filter(Boolean)
    .join(" ");
  const match = source.match(/["'“”‘’（(]([A-Za-z][A-Za-z0-9-]{1,20}|abstract|摘要)["'“”‘’）)]/i);
  return normalizeIssueFingerprintText(match?.[1] ?? "");
}

function extractIssueCategorySignature(issue) {
  const source = `${issue.title ?? ""} ${issue.description ?? ""}`.toLowerCase();
  if (/abbreviation|alias|term|缩写|术语/.test(source)) {
    return "abbreviation";
  }
  if (/abstract|section|章节|摘要|必需章节/.test(source)) {
    return "section";
  }
  return normalizeIssueFingerprintText(issue.ruleLabel ?? issue.title ?? "").slice(0, 32);
}

function dedupeStageIssueCards(issues = []) {
  const merged = new Map();

  for (const rawIssue of ensureArray(issues)) {
    const issue = ensureObject(rawIssue);
    const ruleId = String(issue.ruleId ?? issue.rule_id ?? "").trim();
    const ruleLabel = String(issue.ruleLabel ?? getRuleDisplayLabel(ruleId, "")).trim();
    const subjectSig = extractIssueSubjectToken(issue);
    const categorySig = extractIssueCategorySignature(issue);
    const descriptionSig = normalizeIssueFingerprintText(issue.description);
    const evidenceSig = ensureArray(issue.evidence)
      .map((item) => normalizeIssueFingerprintText(item))
      .filter(Boolean)
      .slice(0, 2)
      .join("|");
    const locationSig = normalizeIssueFingerprintText(issue.location);
    const stageSig = normalizeIssueFingerprintText(issue.stageKey ?? issue.stageLabel ?? "");
    const fingerprint = `${stageSig}|${locationSig}|${subjectSig || descriptionSig || evidenceSig || issue.id}|${categorySig}`;

    if (!merged.has(fingerprint)) {
      merged.set(fingerprint, {
        ...issue,
        ruleId,
        ruleLabel,
        ruleIds: ruleId ? [ruleId] : [],
        ruleLabels: ruleLabel ? [ruleLabel] : [],
        evidence: normalizeEvidenceList(issue.evidence),
        mergedCount: 1
      });
      continue;
    }

    const current = merged.get(fingerprint);
    current.mergedCount += 1;
    current.ruleIds = Array.from(new Set([...current.ruleIds, ...(ruleId ? [ruleId] : [])]));
    current.ruleLabels = Array.from(
      new Set([...current.ruleLabels, ...(ruleLabel ? [ruleLabel] : [])])
    );
    current.evidence = Array.from(
      new Set([...normalizeEvidenceList(current.evidence), ...normalizeEvidenceList(issue.evidence)])
    ).slice(0, 8);
    if (getIssueSeverityRank(issue.severity) > getIssueSeverityRank(current.severity)) {
      current.severity = issue.severity;
    }
    if ((!current.suggestion || current.suggestion.length < String(issue.suggestion ?? "").length) && issue.suggestion) {
      current.suggestion = issue.suggestion;
    }
  }

  return Array.from(merged.values()).map((issue, index) => {
    const ruleSummary =
      issue.ruleLabels.length > 0
        ? issue.ruleLabels.join(" / ")
        : issue.ruleIds.join(" / ");
    const evidence = Array.from(new Set(issue.evidence));

    if (ruleSummary) {
      evidence.unshift(`规则来源 · ${ruleSummary}`);
    }

    if (issue.mergedCount > 1) {
      evidence.unshift(`已合并重复问题 · ${issue.mergedCount} 条`);
    }

    return {
      ...issue,
      id: issue.id ?? `dedup-issue-${index + 1}`,
      title: issue.title || ruleSummary || `问题 ${index + 1}`,
      ruleLabel: issue.ruleLabels[0] ?? issue.ruleLabel ?? "",
      evidence: evidence.slice(0, 8)
    };
  });
}

function mapGenericIssue(item, index, stageName = "summary") {
  const issue = ensureObject(item);
  const ruleId = issue.rule_id ?? issue.ruleId ?? "";
  const ruleLabel = getRuleDisplayLabel(ruleId, "");
  const title =
    issue.title ??
    issue.issue_title ??
    issue.issueTitle ??
    issue.name ??
    (ruleLabel || `${REVIEW_STAGE_LABELS[stageName] ?? "汇总"}问题 ${index + 1}`);

  return {
    id: issue.id ?? issue.issue_id ?? issue.issueId ?? `${stageName}-issue-${index + 1}`,
    title,
    severity: toStageSeverityLabel(
      issue.severity ?? issue.level ?? issue.status ?? issue.priority
    ),
    location:
      issue.location ??
      issue.anchor_id ??
      issue.anchorId ??
      issue.logical_node ??
      issue.dimension ??
      `${REVIEW_STAGE_LABELS[stageName] ?? "汇总"} ${index + 1}`,
    description:
      issue.description ??
      issue.analysis ??
      issue.summary ??
      issue.message ??
      issue.reason ??
      "后端尚未返回该问题的详细说明。",
    evidence: normalizeEvidenceList(
      issue.evidence ??
        issue.evidence_links ??
        issue.evidenceLinks ??
        issue.links ??
        issue.references
    ),
    ruleId,
    ruleLabel,
    suggestion:
      issue.suggestion ??
      issue.recommendation ??
      issue.next_action ??
      issue.nextAction ??
      ""
  };
}

function buildSkippedStageReview(stageName, stageStatus, stageOutput) {
  const stageLabel = REVIEW_STAGE_LABELS[stageName];
  const reason =
    stageOutput.reason_message ??
    stageOutput.reasonMessage ??
    stageOutput.reason_code ??
    stageOutput.reasonCode ??
    "STAGE_SKIPPED";

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel,
      severe: false,
      headline: `${stageLabel}已跳过`,
      overview: `当前阶段未返回有效分析结果：${reason}`,
      issues: [],
      followUpActions: []
    }),
    stageName,
    stageStatus,
    stageOutput
  );
}

function extractLogicAnalysis(source) {
  return ensureObject(
    source.logic_analysis ??
      source.logicAnalysis ??
      source.result?.logic_analysis ??
      source.result?.logicAnalysis ??
      source.data?.result?.logic_analysis ??
      source.data?.result?.logicAnalysis
  );
}

function extractReviewSummaryPayload(source) {
  return ensureObject(
    source.review_summary ??
      source.reviewSummary ??
      source.result_summary ??
      source.resultSummary ??
      source.summary ??
      source
  );
}

function buildFormatProgressOverview(stageOutput, issues = []) {
  const progress = ensureObject(stageOutput.prefilter_progress);
  const completedChapterCount = Number(progress.completed_chapter_count ?? progress.completedChapterCount ?? 0);
  const completedUnitCount = Number(progress.completed_unit_count ?? progress.completedUnitCount ?? 0);
  const latestChapter = {};
  const latestUnit = {};
  const overviewParts = [];

  if (completedChapterCount > 0 || completedUnitCount > 0) {
    overviewParts.push(`已累计完成 ${completedChapterCount || 0} 个章节、${completedUnitCount || 0} 个小节`);
  }

  if (latestChapter.chapter_title) {
    overviewParts.push(`最近完成章节：${latestChapter.chapter_title}`);
  } else if (latestUnit.unit_title) {
    overviewParts.push(`最近完成小节：${latestUnit.unit_title}`);
  }

  if (issues.length) {
    overviewParts.push(`当前已累计发现 ${issues.length} 条格式问题`);
  } else if (
    Array.isArray(stageOutput.violations) ||
    Array.isArray(stageOutput.risk_signals) ||
    Array.isArray(stageOutput.chapter_reviews)
  ) {
    overviewParts.push("当前累计结果已同步，暂未发现需要展示的格式问题");
  }

  return overviewParts.join("；");
}

function extractFormatStageIssues(stageOutput) {
  const report = ensureArray(
    stageOutput.issues?.length
      ? stageOutput.issues
      : [
          ...ensureArray(stageOutput.violations),
          ...ensureArray(stageOutput.risk_signals)
        ]
  );

  const issues = report.map((item, index) =>
    item?.rule_id || item?.status
      ? mapRuleAuditItemToFormatIssue(item, index)
      : mapGenericIssue(item, index, "format")
  );

  return dedupeStageIssueCards(issues);
}

function normalizeFormatStageReview(stageName, stageStatus, stageOutput) {
  if (looksLikeStageReview(stageOutput)) {
    return attachStageReviewMeta(stageOutput, stageName, stageStatus, stageOutput);
  }

  const issues =
    stageOutput.report || stageOutput.audit_items || stageOutput.items
      ? ensureArray(
          stageOutput.report ??
            stageOutput.audit_items ??
            stageOutput.items
        ).map((item, index) =>
          item?.rule_id || item?.status
            ? mapRuleAuditItemToFormatIssue(item, index)
            : mapGenericIssue(item, index, stageName)
        )
      : extractFormatStageIssues(stageOutput);
  const severe =
    Boolean(stageOutput.severe) ||
    issues.filter((item) => item.severity === "严重").length >= 2;

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel: REVIEW_STAGE_LABELS[stageName],
      severe,
      headline:
        stageOutput.headline ??
        (issues.length ? "格式审查已完成" : "格式审查暂无结构化结果"),
      overview:
        stageOutput.overview ??
        stageOutput.summary ??
        (issues.length
          ? "本阶段已返回格式相关问题。"
          : "后端尚未返回可展示的格式审查明细。"),
      issues,
      followUpActions: ensureArray(
        stageOutput.follow_up_actions ??
          stageOutput.followUpActions ??
          stageOutput.next_actions ??
          stageOutput.nextActions
      )
    }),
    stageName,
    stageStatus,
    stageOutput
  );
}

function buildDisplayableStageReview(stageName, payload) {
  const { stageStatus, stageOutput } = extractStagePayload(payload);

  if (["completed", "skipped"].includes(stageStatus) || stageOutput.available === false) {
    return normalizeStageReview(stageName, payload);
  }

  if (stageName !== "format" || !hasObjectContent(stageOutput)) {
    return null;
  }

  const issues = extractFormatStageIssues(stageOutput);
  const progressOverview = buildFormatProgressOverview(stageOutput, issues);
  const severe = issues.filter((item) => item.severity === "涓ラ噸").length >= 2;

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel: REVIEW_STAGE_LABELS[stageName],
      severe,
      headline: "格式审查进行中",
      overview: progressOverview || "后端已返回当前累计审查结果，正在继续处理后续章节。",
      issues,
      followUpActions: []
    }),
    stageName,
    stageStatus,
    stageOutput
  );
}

function normalizeLogicStageReview(stageName, stageStatus, stageOutput) {
  if (looksLikeStageReview(stageOutput)) {
    return attachStageReviewMeta(stageOutput, stageName, stageStatus, stageOutput);
  }

  const logicAnalysis = extractLogicAnalysis(stageOutput);
  const issues = ensureArray(
    logicAnalysis.issues ?? logicAnalysis.unresolved_issues
  ).map(mapTask1IssueToStageIssue);
  const severe =
    Boolean(stageOutput.severe) ||
    issues.filter((item) => item.severity === "严重").length >= 2;

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel: REVIEW_STAGE_LABELS[stageName],
      severe,
      headline:
        stageOutput.headline ??
        (severe ? "逻辑审查发现高优先级问题" : "逻辑审查已完成"),
      overview:
        stageOutput.overview ??
        logicAnalysis.core_argument_consistency?.conflict_summary ??
        logicAnalysis.reasoning_depth?.assessment ??
        "当前阶段已完成逻辑链路检查。",
      issues,
      followUpActions: issues.map((item) => item.suggestion).filter(Boolean)
    }),
    stageName,
    stageStatus,
    stageOutput
  );
}

function normalizeInnovationStageReview(stageName, stageStatus, stageOutput) {
  if (looksLikeStageReview(stageOutput)) {
    return attachStageReviewMeta(stageOutput, stageName, stageStatus, stageOutput);
  }

  const reviewSummary = extractReviewSummaryPayload(stageOutput);
  const weaknesses = ensureArray(reviewSummary.weaknesses ?? reviewSummary.issues);
  const issues = weaknesses.map((item, index) =>
    typeof item === "string"
      ? mapSummaryWeaknessToInnovationIssue(
          item,
          index,
          ensureArray(reviewSummary.nextActions ?? reviewSummary.next_actions)[index] ??
            "建议补强方法与创新点的直接证据。"
        )
      : mapGenericIssue(item, index, stageName)
  );

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel: REVIEW_STAGE_LABELS[stageName],
      severe: Boolean(stageOutput.severe),
      headline:
        stageOutput.headline ??
        reviewSummary.headline ??
        "方法与创新点审查已完成",
      overview:
        stageOutput.overview ??
        reviewSummary.summary ??
        "当前阶段已完成方法与创新点检查。",
      issues,
      followUpActions: ensureArray(
        reviewSummary.nextActions ??
          reviewSummary.next_actions ??
          stageOutput.followUpActions ??
          stageOutput.follow_up_actions
      )
    }),
    stageName,
    stageStatus,
    stageOutput
  );
}

function normalizeInnovationStageReviewV2(stageName, stageStatus, stageOutput) {
  if (looksLikeStageReview(stageOutput)) {
    return attachStageReviewMeta(stageOutput, stageName, stageStatus, stageOutput);
  }

  const reviewSummary = extractReviewSummaryPayload(
    stageOutput.innovation_summary ?? stageOutput.innovationSummary ?? stageOutput
  );
  const violations = ensureArray(stageOutput.violations);
  const weaknesses = ensureArray(reviewSummary.weaknesses ?? reviewSummary.issues);
  const issues = (violations.length ? violations : weaknesses).map((item, index) =>
    typeof item === "string"
      ? mapSummaryWeaknessToInnovationIssue(
          item,
          index,
          ensureArray(reviewSummary.nextActions ?? reviewSummary.next_actions)[index] ??
            "Add direct evidence for the innovation claim."
        )
      : mapGenericIssue(item, index, stageName)
  );
  const overviewParts = [
    reviewSummary.summary,
    reviewSummary.claim_quality ? `claim_quality: ${reviewSummary.claim_quality}` : "",
    reviewSummary.method_alignment
      ? `method_alignment: ${reviewSummary.method_alignment}`
      : "",
    reviewSummary.reproducibility_risk
      ? `reproducibility_risk: ${reviewSummary.reproducibility_risk}`
      : ""
  ].filter(Boolean);

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel: REVIEW_STAGE_LABELS[stageName],
      severe: Boolean(stageOutput.severe),
      headline:
        stageOutput.headline ??
        reviewSummary.headline ??
        "Innovation review finished",
      overview:
        stageOutput.overview ??
        (overviewParts.length ? overviewParts.join(" | ") : null) ??
        "The innovation stage snapshot is available.",
      issues,
      followUpActions: ensureArray(
        reviewSummary.nextActions ??
          reviewSummary.next_actions ??
          stageOutput.followUpActions ??
          stageOutput.follow_up_actions
      )
    }),
    stageName,
    stageStatus,
    stageOutput
  );
}

function normalizeStageReview(stageName, payload) {
  const { stageStatus, stageOutput, raw } = extractStagePayload(payload);

  if (stageStatus === "skipped" || stageOutput.available === false) {
    return buildSkippedStageReview(stageName, stageStatus, stageOutput);
  }

  if (stageName === "format") {
    return normalizeFormatStageReview(stageName, stageStatus, stageOutput);
  }

  if (stageName === "logic") {
    return normalizeLogicStageReview(stageName, stageStatus, stageOutput);
  }

  if (stageName === "innovation") {
    return normalizeInnovationStageReviewV2(stageName, stageStatus, stageOutput);
  }

  return attachStageReviewMeta(
    createStageReview({
      stageId: stageName,
      stageLabel: REVIEW_STAGE_LABELS[stageName],
      severe: false,
      headline: `${REVIEW_STAGE_LABELS[stageName]}已完成`,
      overview: "当前阶段已完成。",
      issues: ensureArray(stageOutput.issues).map((item, index) =>
        mapGenericIssue(item, index, stageName)
      ),
      followUpActions: []
    }),
    stageName,
    stageStatus,
    raw
  );
}

function normalizeStageSnapshotRecord(stageName, payload) {
  const { stageStatus, stageOutput, raw } = extractStagePayload(payload);

  return {
    stageName,
    stageStatus,
    stageOutput,
    review: stageName !== "summary" ? buildDisplayableStageReview(stageName, payload) : null,
    raw
  };
}

function mergeSuggestionCards(...groups) {
  const suggestionMap = new Map();

  for (const group of groups) {
    for (const item of ensureArray(group)) {
      const suggestion = typeof item === "string" ? { content: item } : ensureObject(item);
      const content = String(
        suggestion.content ?? suggestion.text ?? suggestion.message ?? ""
      ).trim();

      if (!content || suggestionMap.has(content)) {
        continue;
      }

      suggestionMap.set(content, {
        id:
          suggestion.id ??
          `summary-suggestion-${suggestionMap.size + 1}`,
        title: suggestion.title ?? "汇总建议",
        content,
        stageLabel: suggestion.stageLabel ?? suggestion.stage_label ?? "汇总"
      });
    }
  }

  return Array.from(suggestionMap.values());
}

async function loadMockPaperMeta() {
  try {
    return await fetchJson("/mock/paper_meta.json");
  } catch (error) {
    return fetchJson("/mock/document_ir.json");
  }
}

function makeSubmissionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `submission-${Date.now()}`;
}

function reportUploadLifecycle(onProgress, payload) {
  if (typeof onProgress === "function") {
    onProgress({
      ...payload,
      reportedAt: new Date().toISOString()
    });
  }
}

async function fetchLocalParserProgress(submissionId) {
  const endpoint = LOCAL_PARSER_ENDPOINTS.parsePaperProgress.path.replace(
    ":submissionId",
    encodeURIComponent(String(submissionId ?? ""))
  );
  const response = await fetch(`${PARSER_API_BASE_URL}${endpoint}`);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`local parser progress request failed: ${response.status}`);
  }

  return response.json();
}

function startLocalParserProgressMonitor({ submissionId, onProgress }) {
  if (
    typeof window === "undefined" ||
    !submissionId ||
    typeof onProgress !== "function"
  ) {
    return {
      stop() {}
    };
  }

  let stopped = false;
  let inFlight = false;

  const tick = async () => {
    if (stopped || inFlight) {
      return;
    }

    inFlight = true;

    try {
      const payload = await fetchLocalParserProgress(submissionId);

      if (!payload) {
        return;
      }

      reportUploadLifecycle(onProgress, {
        provider: "docling",
        source: "parser",
        submissionId,
        status: payload.status ?? "processing",
        phase: payload.phase ?? payload.status ?? "parsing",
        fraction:
          typeof payload.fraction === "number"
            ? payload.fraction
            : typeof payload.percent === "number"
              ? payload.percent / 100
              : null,
        percent: payload.percent ?? null,
        message: payload.message ?? "",
        currentChunk: payload.currentChunk ?? null,
        totalChunks: payload.totalChunks ?? null,
        pageStart: payload.pageStart ?? null,
        pageEnd: payload.pageEnd ?? null
      });

      if (["completed", "failed"].includes(payload.status ?? "")) {
        stopped = true;
      }
    } catch {
      // Ignore transient polling errors and let the main upload request decide success.
    } finally {
      inFlight = false;
    }
  };

  const timer = window.setInterval(() => {
    void tick();
  }, LOCAL_PARSER_PROGRESS_POLL_MS);

  void tick();

  return {
    stop() {
      stopped = true;
      window.clearInterval(timer);
    }
  };
}

function summarizeRuleLine(line, index) {
  const compact = line.replace(/^[-*0-9.\s]+/, "").trim();
  if (!compact) {
    return `规则 ${index + 1}`;
  }

  return compact.length > 36 ? `${compact.slice(0, 36)}...` : compact;
}

function buildMockExtractedRules(sourceText) {
  const normalized = sourceText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const seeds = normalized.length
    ? normalized.slice(0, 5)
    : [
        "论文必须明确说明研究问题与应用场景。",
        "核心方法需要说明输入输出与关键模块。",
        "实验部分需包含数据集、评价指标与主要基线。"
      ];

  const rules = seeds.map((line, index) => `${index + 1}. ${summarizeRuleLine(line, index)}`);

  return {
    sourceText,
    rules,
    extractedRulesText: rules.join("\n"),
    extractedAt: new Date().toISOString()
  };
}

export function getPaperMeta(submissionOrMeta) {
  if (!submissionOrMeta) {
    return null;
  }

  return submissionOrMeta.paperMeta ?? submissionOrMeta.documentIr ?? submissionOrMeta;
}

export function getPageCount(submissionOrMeta) {
  const meta = getPaperMeta(submissionOrMeta);
  return meta?.total_pages ?? meta?.pages?.length ?? 0;
}

export function getAnchorCount(submissionOrMeta) {
  const meta = getPaperMeta(submissionOrMeta);
  return (
    meta?.anchors?.length ??
    meta?.blocks?.length ??
    meta?.chunks?.length ??
    meta?.chunk_count ??
    meta?.chunkCount ??
    0
  );
}

export function getChunkCount(submissionOrMeta) {
  const meta = getPaperMeta(submissionOrMeta);
  return (
    meta?.chunk_count ??
    meta?.chunkCount ??
    meta?.chunks?.length ??
    meta?.summary?.group_count ??
    0
  );
}

export function getImageCount(submissionOrMeta) {
  const markdownText =
    submissionOrMeta?.paperMarkdown ??
    submissionOrMeta?.paper_md ??
    submissionOrMeta?.markdown_text ??
    "";

  if (typeof markdownText === "string" && markdownText.trim()) {
    const imageMatches = markdownText.match(/!\[[^\]]*\]\([^)]+\)/g);
    if (Array.isArray(imageMatches)) {
      return imageMatches.length;
    }
  }

  const meta = getPaperMeta(submissionOrMeta);
  return meta?.image_count ?? meta?.images?.length ?? 0;
}

export function countAnchorsByType(submissionOrMeta, type) {
  const meta = getPaperMeta(submissionOrMeta);
  return (meta?.anchors ?? []).filter((anchor) => anchor.type === type).length;
}

function buildMockSummary(metaSource) {
  const paperMeta = getPaperMeta(metaSource);
  const pageCount = getPageCount(paperMeta);
  const chunkCount = getChunkCount(metaSource);
  const imageCount = getImageCount(metaSource);
  const anchorCount = chunkCount;
  const figureCount = imageCount;
  const tableCount = 0;

  return {
    overallScore: Math.min(95, 72 + Math.round(pageCount / 2) + imageCount),
    verdict: "建议大修后进入下一轮评审",
    summary:
      "当前解析结果已经符合锚点列表式输出的方向，适合继续把评语生成、推荐检索等后续模块接到统一的 paper_meta.json 中。",
    strengths: [
      `已生成 ${pageCount} 页内容和 ${anchorCount} 条锚点，结构化程度比旧版更高。`,
      `图表锚点已拆分，当前包含 ${figureCount} 个 figure 锚点、${tableCount} 个 table 锚点。`,
      "Markdown 与 sidecar 元数据已分离，便于前端展示和后端程序读取。"
    ],
    weaknesses: [
      "当前评语结果仍为 mock，后续建议基于 paper_meta.json 的 anchors 做真实证据引用。",
      "推荐论文列表尚未根据新的锚点格式进行检索适配。",
      "如果后续甲方继续细化 anchor 命名规范，可能还需要同步调整。"
    ],
    nextActions: [
      "基于 paper_meta.json 的 anchors 接入真实评语接口。",
      "让推荐接口消费 figure、table、paragraph 三类锚点。",
      "把规范校验脚本纳入启动或 CI 流程。"
    ],
    dimensionScores: [
      { label: "结构完整度", score: 90 },
      { label: "可追溯性", score: 92 },
      { label: "展示友好度", score: 87 },
      { label: "联调准备度", score: 85 }
    ]
  };
}

function buildPaperBundle({ paperMarkdown, paperMeta }) {
  return {
    paper_md: paperMarkdown ?? "",
    paper_meta: paperMeta ?? {},
    assets: {
      figures_dir: "assets/figures",
      tables_dir: "assets/tables"
    }
  };
}

function buildMockTask1Audit(metaSource) {
  const meta = getPaperMeta(metaSource);
  const anchors = meta?.anchors ?? [];
  const paragraphAnchor = anchors.find((item) => item.type === "paragraph");
  const figureAnchor = anchors.find((item) => item.type === "figure");
  const tableAnchor = anchors.find((item) => item.type === "table");
  const mockProfile = meta?.__mockProfile ?? "default";

  if (mockProfile === "logic-pass") {
    return {
      code: 200,
      message: "success",
      data: {
        schema_version: "task1-chunked-long-audit-v1",
        mode: "llm_chunked_long",
        result: {
          logic_analysis: {
            core_argument_consistency: {
              is_consistent: true,
              conflict_summary: "核心论证链路基本闭合，当前逻辑审查可以继续推进到方法与创新点阶段。"
            },
            logic_dimensions: {
              research_problem_closure: {
                status: "pass",
                summary: "研究问题、方法目标与结论回扣关系较为清晰。",
                issue_ids: [],
                evidence_links: [paragraphAnchor?.anchor_id].filter(Boolean)
              },
              claim_evidence_conclusion_strength: {
                status: "pass",
                summary: "主要结论与实验结果之间的支撑关系较稳定。",
                issue_ids: [],
                evidence_links: [figureAnchor?.anchor_id, tableAnchor?.anchor_id].filter(Boolean)
              },
              figure_table_text_consistency: {
                status: "risk",
                summary: "个别图表仍可补一条更明确的解释句，但不影响进入下一阶段。",
                issue_ids: ["issue-pass-1"],
                evidence_links: [figureAnchor?.anchor_id].filter(Boolean)
              }
            },
            issues: [
              {
                issue_id: "issue-pass-1",
                logical_node: "figure_table_text_consistency",
                severity: "medium",
                analysis: "个别图表首现时的解释句还可以更直接一些，但整体不会阻断后续方法与创新点审查。",
                evidence_links: [figureAnchor?.anchor_id].filter(Boolean),
                scope: "local",
                dimension_keys: ["figure_table_text_consistency"],
                confidence: 0.7
              }
            ],
            reasoning_depth: {
              assessment: "推理链条整体连贯，当前更适合继续检查方法与创新点的表达质量。"
            },
            structure_rationality: {
              assessment: "结构基本合理，可以继续进入下一阶段。"
            },
            chunk_count: Math.max(1, Math.ceil((meta?.total_pages ?? 1) / 2))
          }
        }
      }
    };
  }

  return {
    code: 200,
    message: "success",
    data: {
      schema_version: "task1-chunked-long-audit-v1",
      mode: "llm_chunked_long",
      result: {
        logic_analysis: {
          core_argument_consistency: {
            is_consistent: false,
            conflict_summary: "检测到 3 处需要跨章节复核的逻辑风险。"
          },
          logic_dimensions: {
            research_problem_closure: {
              status: "risk",
              summary: "研究问题提出较清楚，但方法与结论的闭环解释还不够紧。",
              issue_ids: ["issue-1"],
              evidence_links: [paragraphAnchor?.anchor_id].filter(Boolean)
            },
            claim_evidence_conclusion_strength: {
              status: "risk",
              summary: "部分强结论缺少对应证据支撑，容易在评审时被追问。",
              issue_ids: ["issue-2"],
              evidence_links: [figureAnchor?.anchor_id, tableAnchor?.anchor_id].filter(Boolean)
            },
            figure_table_text_consistency: {
              status: "pass",
              summary: "主要图表与正文已经建立引用关系，但还可以再强化解释句。",
              issue_ids: [],
              evidence_links: [figureAnchor?.anchor_id].filter(Boolean)
            }
          },
          issues: [
            {
              issue_id: "issue-1",
              logical_node: "research_problem_closure",
              severity: "major",
              analysis: "摘要和引言已经提出研究目标，但方法章节缺少对关键假设的回扣。",
              evidence_links: [paragraphAnchor?.anchor_id].filter(Boolean),
              scope: "cross_chunk",
              dimension_keys: ["research_problem_closure"],
              confidence: 0.82
            },
            {
              issue_id: "issue-2",
              logical_node: "claim_evidence_conclusion_strength",
              severity: "major",
              analysis: "实验结果给出了提升趋势，但结论用词明显强于证据覆盖范围。",
              evidence_links: [tableAnchor?.anchor_id].filter(Boolean),
              scope: "global",
              dimension_keys: ["claim_evidence_conclusion_strength"],
              confidence: 0.79
            },
            {
              issue_id: "issue-3",
              logical_node: "figure_table_text_consistency",
              severity: "medium",
              analysis: "图表首次出现时缺少一条结论性解释句，读者需要自己推断图表意图。",
              evidence_links: [figureAnchor?.anchor_id].filter(Boolean),
              scope: "local",
              dimension_keys: ["figure_table_text_consistency"],
              confidence: 0.74
            }
          ],
          reasoning_depth: {
            assessment: "推理链条基本完整，但部分因果论证仍需更多解释性文字支撑。"
          },
          structure_rationality: {
            assessment: "结构总体合理，适合继续做面向评审的精修。"
          },
          chunk_count: Math.max(1, Math.ceil((meta?.total_pages ?? 1) / 2))
        }
      }
    }
  };
}

function normalizeTask1AuditResponse(response) {
  return response?.data?.result?.logic_analysis ?? {};
}

function makeActionSuggestion(issue) {
  const dimension = issue?.dimension_keys?.[0] ?? issue?.logical_node ?? "logic";

  const suggestionMap = {
    research_problem_closure: "建议把研究问题、方法假设和结论回扣放在同一条叙述链上，减少章节之间的断裂。",
    claim_evidence_conclusion_strength: "建议把强结论改成更审慎的表述，或补充更直接的实验和证据引用。",
    figure_table_text_consistency: "建议在图表第一次出现的位置补一条结论性解释句，并明确图表支撑的结论。",
    method_experiment_alignment: "建议补充方法声明与实验设置的一一对应关系，避免评审觉得验证不足。",
    scope_and_extrapolation_control: "建议限制外推表述的范围，并补充适用边界说明。"
  };

  return (
    suggestionMap[dimension] ??
    "建议把这条逻辑风险对应到更具体的章节位置，再补充直接证据或更谨慎的结论表述。"
  );
}

function scoreFromTask1Issues(issues = []) {
  const penaltyBySeverity = {
    critical: 18,
    major: 10,
    medium: 6,
    minor: 3
  };

  const score = issues.reduce(
    (total, issue) => total - (penaltyBySeverity[issue.severity] ?? 4),
    95
  );

  return Math.max(48, score);
}

export function mapTask1AuditToReviewSummary(logicAnalysis) {
  const issues = logicAnalysis?.issues ?? [];
  const dimensions = Object.entries(logicAnalysis?.logic_dimensions ?? {});
  const score = scoreFromTask1Issues(issues);
  const majorIssueCount = issues.filter((item) => item.severity === "major").length;
  const criticalIssueCount = issues.filter((item) => item.severity === "critical").length;

  return {
    overallScore: score,
    verdict:
      criticalIssueCount > 0
        ? "建议优先修复关键逻辑冲突"
        : majorIssueCount > 1
          ? "建议大修后再进入下一轮"
          : "建议补充说明后继续推进",
    summary:
      logicAnalysis?.core_argument_consistency?.conflict_summary ??
      logicAnalysis?.structure_rationality?.assessment ??
      "已完成全局逻辑分析。",
    strengths:
      dimensions
        .filter(([, value]) => value.status === "pass")
        .slice(0, 3)
        .map(([, value]) => value.summary) || [],
    weaknesses:
      issues.slice(0, 3).map((item) => item.analysis) ||
      ["当前还没有识别到明确弱点。"],
    nextActions:
      issues.slice(0, 3).map((item) => makeActionSuggestion(item)) ||
      ["建议结合规则分析结果继续做针对性修改。"],
    dimensionScores: dimensions.slice(0, 4).map(([key, value]) => ({
      label: key.replace(/_/g, " "),
      score: value.status === "pass" ? 90 : value.status === "risk" ? 72 : 58
    }))
  };
}

function buildMockTask2Audit() {
  return {
    msg: "审计成功",
    report: [
      {
        rule_id: "R-SYS-S002",
        status: "violated",
        location: "Figure 1",
        evidence: "核心图表首次出现时缺少充分解释句。",
        suggestion: "补充图表对应的结论性说明。"
      },
      {
        rule_id: "R-SYS-E004",
        status: "violated",
        location: "Experiment",
        evidence: "实验部分未完整交代边界场景与负面案例。",
        suggestion: "增加边界样本或误判分析。"
      },
      {
        rule_id: "R-AUTO-001",
        status: "violated",
        location: "Abstract",
        evidence: "摘要提出效率主张，但缺少跨数据集的直接验证。",
        suggestion: "补充大规模数据集上的效率对比。"
      }
    ]
  };
}

function mapTask2RuleToLibraryItem(rule, index) {
  return {
    id: rule.rule_id ?? rule.rule_name ?? `task2-rule-${index + 1}`,
    title: rule.rule_name ?? `规则 ${index + 1}`,
    category: rule.dimension ?? "规则库",
    summary:
      rule.description ??
      rule.prompt_fragment ??
      "后端返回的规则说明暂缺，前端已保留结构。",
    tags: rule.triggers ?? [rule.execution_type ?? "rule"],
    questionCount: 0,
    defaultSelected: rule.is_active ?? true,
    status: rule.status ?? "approved",
    executionType: rule.execution_type ?? "rule"
  };
}

export function isLocalParserEnabled() {
  return USE_LOCAL_PARSER;
}

async function uploadViaLocalParser(paperFile, { onProgress } = {}) {
  const submissionId = makeSubmissionId();
  const formData = new FormData();
  formData.append(UPLOAD_FORM_FIELDS.paper, paperFile);
  formData.append(UPLOAD_FORM_FIELDS.submissionId, submissionId);

  let data;
  const progressMonitor = startLocalParserProgressMonitor({
    submissionId,
    onProgress
  });

  reportUploadLifecycle(onProgress, {
    provider: "docling",
    source: "upload",
    submissionId,
    phase: "uploading",
    status: "processing",
    fraction: 0,
    percent: 0,
    message: `正在上传 ${paperFile?.name ?? "论文"} 到 Docling 解析服务...`
  });

  try {
    data = await requestJsonWithUploadProgress(
      `${PARSER_API_BASE_URL}${LOCAL_PARSER_ENDPOINTS.parsePaper.path}`,
      {
        method: "POST",
        body: formData
      },
      "local parser upload",
      {
        onUploadProgress: (progressEvent) => {
          reportUploadLifecycle(onProgress, {
            provider: "docling",
            source: "upload",
            submissionId,
            phase: "uploading",
            status: "processing",
            fraction:
              typeof progressEvent.fraction === "number"
                ? progressEvent.fraction
                : null,
            percent:
              typeof progressEvent.percent === "number"
                ? progressEvent.percent
                : null,
            message:
              typeof progressEvent.percent === "number"
                ? `正在上传论文到 Docling（${Math.round(progressEvent.percent)}%）...`
                : "正在上传论文到 Docling 解析服务..."
          });
        }
      }
    );
  } catch (error) {
    progressMonitor.stop();
    const message =
      error instanceof Error ? error.message : "unknown parser error";
    throw new Error(
      `本地解析服务不可用，请先启动 paper-review-system 接口。${message}`
    );
  }

  progressMonitor.stop();

  reportUploadLifecycle(onProgress, {
    provider: "docling",
    source: "parser",
    submissionId: data?.submissionId ?? submissionId,
    phase: "completed",
    status: "completed",
    fraction: 1,
    percent: 100,
    message: "Docling 解析完成，正在创建 review run..."
  });

  const normalizedPaperMeta = data.paperMeta ?? data.documentIr ?? {};

  return {
    submissionId: data.submissionId ?? submissionId,
    paperName: data.paperName ?? paperFile?.name ?? "未命名论文",
    paperMarkdown: data.paperMarkdown ?? "",
    paperAssetBase: data.paperAssetBase ?? "",
    paperMeta: normalizedPaperMeta,
    documentIr: normalizedPaperMeta,
    uploadedAt: new Date().toISOString(),
    sourceMode: "local-parser-api",
    artifacts: data.artifacts ?? null
  };
}

async function uploadViaLocalArtifacts({
  paperFile,
  markdownFile,
  documentIrFile,
  imageBaseUrl,
  mockProfile = "default",
  useMockFallback = false
}) {
  const hasLocalArtifacts = Boolean(markdownFile && documentIrFile);
  const paperMarkdown = hasLocalArtifacts
    ? await readFileAsText(markdownFile)
    : await fetch("/mock/paper.md").then((response) => response.text());
  const paperMeta = hasLocalArtifacts
    ? await readFileAsJson(documentIrFile)
    : await loadMockPaperMeta();
  const normalizedPaperMeta =
    !hasLocalArtifacts && mockProfile !== "default"
      ? {
          ...paperMeta,
          __mockProfile: mockProfile
        }
      : paperMeta;
  const mockPaperName =
    mockProfile === "logic-pass" ? "閫昏緫瀹℃煡閫氳繃鏍蜂緥" : "绀轰緥璁烘枃";

  return {
    submissionId: makeSubmissionId(),
    paperName:
      paperFile?.name ??
      normalizedPaperMeta?.title ??
      normalizedPaperMeta?.doc_id ??
      mockPaperName,
    paperMarkdown,
    paperAssetBase: imageBaseUrl || "/mock",
    paperMeta: normalizedPaperMeta,
    documentIr: normalizedPaperMeta,
    uploadedAt: new Date().toISOString(),
    sourceMode: hasLocalArtifacts ? "local-artifacts" : useMockFallback ? "mock" : "local-artifacts"
  };
}

export async function uploadPaper({
  paperFile,
  markdownFile,
  documentIrFile,
  imageBaseUrl,
  mockProfile = "default",
  onProgress
}) {
  const hasLocalArtifacts = markdownFile && documentIrFile;

  if (USE_LOCAL_PARSER && paperFile) {
    return uploadViaLocalParser(paperFile, { onProgress });
  }

  if (hasLocalArtifacts) {
    return uploadViaLocalArtifacts({
      paperFile,
      markdownFile,
      documentIrFile,
      imageBaseUrl,
      mockProfile
    });
  }

  if (!USE_MOCK) {
    const formData = new FormData();

    if (paperFile) {
      formData.append(UPLOAD_FORM_FIELDS.paper, paperFile);
    }

    if (markdownFile) {
      formData.append(UPLOAD_FORM_FIELDS.markdownFile, markdownFile);
    }

    if (documentIrFile) {
      formData.append(UPLOAD_FORM_FIELDS.paperMetaFile, documentIrFile);
      formData.append(UPLOAD_FORM_FIELDS.legacyDocumentIrFile, documentIrFile);
    }

    if (imageBaseUrl) {
      formData.append(UPLOAD_FORM_FIELDS.imageBaseUrl, imageBaseUrl);
    }

    const data = await requestJsonWithUploadProgress(
      `${API_BASE_URL}${APP_API_ENDPOINTS.parsePaper.path}`,
      {
        method: "POST",
        body: formData
      },
      "backend parse upload"
    );

    const paperMeta = data.paperMeta ?? data.documentIr ?? {};

    return {
      submissionId: data.submissionId ?? makeSubmissionId(),
      paperName: data.paperName ?? paperFile?.name ?? "未命名论文",
      paperMarkdown: data.paperMarkdown ?? "",
      paperAssetBase: data.paperAssetBase ?? imageBaseUrl ?? "",
      paperMeta,
      documentIr: paperMeta,
      uploadedAt: new Date().toISOString(),
      sourceMode: "api"
    };
  }

  const paperMarkdown = hasLocalArtifacts
    ? await readFileAsText(markdownFile)
    : await fetch("/mock/paper.md").then((response) => response.text());
  const paperMeta = hasLocalArtifacts
    ? await readFileAsJson(documentIrFile)
    : await loadMockPaperMeta();
  const normalizedPaperMeta =
    !hasLocalArtifacts && mockProfile !== "default"
      ? {
          ...paperMeta,
          __mockProfile: mockProfile
        }
      : paperMeta;
  const mockPaperName =
    mockProfile === "logic-pass" ? "逻辑审查通过样例" : "示例论文";

  return {
    submissionId: makeSubmissionId(),
    paperName: paperFile?.name ?? normalizedPaperMeta?.doc_id ?? mockPaperName,
    paperMarkdown,
    paperAssetBase: imageBaseUrl || "/mock",
    paperMeta: normalizedPaperMeta,
    documentIr: normalizedPaperMeta,
    uploadedAt: new Date().toISOString(),
    sourceMode: hasLocalArtifacts ? "local-artifacts" : "mock"
  };
}

export async function createReviewRun({
  paperTitle,
  paperMarkdown,
  documentIr,
  paperMeta,
  runtimeContext
}) {
  const meta = paperMeta ?? documentIr ?? {};
  const payload = {
    paper_title: paperTitle ?? meta?.doc_id ?? "Untitled Paper",
    paper_bundle: buildPaperBundle({
      paperMarkdown,
      paperMeta: meta
    }),
    runtime_context:
      runtimeContext ?? {
        capability_config: {
          recommendation: {
            mode: "off"
          }
        }
      }
  };

  if (!USE_MOCK) {
    const response = await requestJsonWithUploadProgress(
      buildApiUrl(RUN_API_ENDPOINTS.createRun.path),
      {
        method: RUN_API_ENDPOINTS.createRun.method,
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      },
      "create review run"
    );

    if (response?.ok === false) {
      throw createApiError({
        message: response?.message ?? "请求失败",
        code: response?.code ?? "REQUEST_FAILED",
        status: 500,
        data: response?.data ?? null
      });
    }

    return normalizeRunRecord(response);
  }

  await sleep(200);

  const runId =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `run-${Date.now()}`;
  const acceptedAt = new Date().toISOString();
  const run = {
    runId,
    acceptedAt,
    paperTitle: payload.paper_title,
    paperMarkdown: paperMarkdown ?? "",
    paperMeta: meta,
    stageReviews: {
      format: null,
      logic: null,
      innovation: null
    },
    summaryPayload: null,
    state: {
      run_id: runId,
      status: "created",
      current_stage: "format",
      next_stage: "format",
      progress: 0,
      stage_runs: createEmptyStageRuns(),
      allowed_actions: ["continue", "skip", "abort"],
      last_error: ""
    }
  };

  saveMockRun(run);

  return normalizeRunRecord({
    data: {
      run_id: runId,
      status: "created",
      current_stage: "format",
      accepted_at: acceptedAt
    }
  });
}

export async function fetchRunState(runId) {
  if (!runId) {
    throw createApiError({
      message: "run id is required",
      code: "RUN_NOT_FOUND",
      status: 404
    });
  }

  if (!USE_MOCK) {
    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.getRunState.path,
      {
        method: RUN_API_ENDPOINTS.getRunState.method
      },
      { runId }
    );

    return normalizeRunState(response);
  }

  await sleep(120);
  return normalizeRunState(requireMockRun(runId).state);
}

export async function fetchStageSnapshot({ runId, stageName }) {
  const normalizedStageName = coerceStageName(stageName, null);

  if (!runId || !normalizedStageName) {
    throw createApiError({
      message: "stage snapshot request is invalid",
      code: "STAGE_INVALID",
      status: 400
    });
  }

  const snapshot = await fetchStageRecord({
    runId,
    stageName: normalizedStageName
  });

  return snapshot.review;
}

export async function fetchStageRecord({ runId, stageName }) {
  const normalizedStageName = coerceStageName(stageName, null);

  if (!runId || !normalizedStageName) {
    throw createApiError({
      message: "stage snapshot request is invalid",
      code: "STAGE_INVALID",
      status: 400
    });
  }

  if (!USE_MOCK) {
    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.getStage.path,
      {
        method: RUN_API_ENDPOINTS.getStage.method
      },
      {
        runId,
        stageName: normalizedStageName
      }
    );

    return normalizeStageSnapshotRecord(normalizedStageName, response);
  }

  await sleep(100);

  const run = requireMockRun(runId);

  if (normalizedStageName === "summary" && run.summaryPayload) {
    return normalizeStageSnapshotRecord(normalizedStageName, {
      data: {
        stage_name: normalizedStageName,
        stage_status: "completed",
        stage_output: run.summaryPayload.result_summary ?? {}
      }
    });
  }

  const review = run.stageReviews[normalizedStageName];

  if (review) {
    return {
      stageName: normalizedStageName,
      stageStatus: review.stageStatus ?? "completed",
      stageOutput: review.rawData ?? {},
      review,
      raw: review.rawData ?? null
    };
  }

  return {
    stageName: normalizedStageName,
    stageStatus: getStageRunStatus(run.state, normalizedStageName),
    stageOutput: {},
    review: null,
    raw: null
  };
}

export async function triggerStageExecution({
  runId,
  stageName,
  action = "continue",
  operator = "frontend_user",
  reason = ""
}) {
  const normalizedStageName = coerceStageName(stageName, null);

  if (!runId || !normalizedStageName) {
    throw createApiError({
      message: "stage trigger request is invalid",
      code: "STAGE_INVALID",
      status: 400
    });
  }

  if (!USE_MOCK) {
    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.triggerStage.path,
      {
        method: RUN_API_ENDPOINTS.triggerStage.method,
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          action,
          operator,
          reason
        })
      },
      {
        runId,
        stageName: normalizedStageName
      }
    );

    const stageStatus =
      response?.data?.stage_status ??
      response?.data?.stageStatus ??
      response?.data?.control_state?.status;
    const hasStagePayload =
      isPlainObject(response?.data?.result) ||
      isPlainObject(response?.data?.stage_output) ||
      stageStatus === "skipped";

    if (stageStatus && FINAL_STAGE_STATUSES.has(stageStatus) && hasStagePayload) {
      return normalizeStageReview(normalizedStageName, response);
    }

    return null;
  }

  await sleep(180);

  const run = requireMockRun(runId);

  if (
    ["completed", "aborted", "failed"].includes(run.state.status) &&
    normalizedStageName !== "summary"
  ) {
    throw createApiError({
      message: "run state conflict",
      code: "RUN_STATE_CONFLICT",
      status: 409
    });
  }

  if (run.state.next_stage !== normalizedStageName) {
    throw createApiError({
      message: "requested stage is not allowed now",
      code: "STAGE_NOT_READY",
      status: 409,
      data: {
        run_id: runId,
        requested_stage: normalizedStageName,
        next_stage: run.state.next_stage,
        allowed_actions: run.state.allowed_actions
      }
    });
  }

  const stageRun = run.state.stage_runs.find(
    (item) => item.stage_name === normalizedStageName
  );

  if (stageRun) {
    stageRun.status = action === "abort" ? "aborted" : "running";
  }

  let review = null;
  let stageStatus = "completed";

  if (action === "abort") {
    stageStatus = "aborted";
    run.state.status = "aborted";
    run.state.current_stage = normalizedStageName;
    run.state.next_stage = normalizedStageName;
    run.state.allowed_actions = [];
    run.state.last_error = "run aborted by user";
  } else if (action === "skip") {
    stageStatus = "skipped";
    review = buildSkippedStageReview(normalizedStageName, stageStatus, {
      available: false,
      reason_code: "STAGE_SKIPPED",
      warnings: []
    });
  } else if (normalizedStageName === "format") {
    review = await runFormatReview({
      paperMarkdown: run.paperMarkdown,
      paperMeta: run.paperMeta
    });
  } else if (normalizedStageName === "logic") {
    review = await runLogicReview({
      paperMarkdown: run.paperMarkdown,
      paperMeta: run.paperMeta
    });
  } else if (normalizedStageName === "innovation") {
    review = await runInnovationReview({
      paperMarkdown: run.paperMarkdown,
      paperMeta: run.paperMeta
    });
  } else if (normalizedStageName === "summary") {
    const digest = buildReviewDigest({
      formatReview: run.stageReviews.format,
      logicReview: run.stageReviews.logic,
      innovationReview: run.stageReviews.innovation
    });

    run.summaryPayload = {
      run_id: runId,
      result_summary: {
        verdict: digest.verdict,
        overview: digest.overview,
        merged_issues: digest.issues.map((item) => ({
          id: item.id,
          title: item.title,
          severity: item.severity,
          stage_name: item.stageKey,
          location: item.location,
          description: item.description,
          evidence: item.evidence,
          suggestion: item.suggestion
        })),
        warnings: digest.skippedAfterStageLabel
          ? [`流程在 ${digest.skippedAfterStageLabel} 后提前收束。`]
          : [],
        suggestions: digest.modificationSuggestions
      }
    };
  }

  if (review && normalizedStageName in run.stageReviews) {
    run.stageReviews[normalizedStageName] = {
      ...review,
      stageStatus
    };
  }

  const nextStage = getNextStageName(normalizedStageName);

  if (stageRun) {
    stageRun.status = stageStatus;
  }

  if (stageStatus === "aborted") {
    run.state.progress = estimateRunProgress(run.state.stage_runs);
    saveMockRun(run);
    return null;
  }

  if (normalizedStageName === "summary" || !nextStage) {
    run.state.status = "completed";
    run.state.current_stage = "summary";
    run.state.next_stage = "summary";
    run.state.allowed_actions = [];
  } else {
    run.state.status = "running";
    run.state.current_stage = normalizedStageName;
    run.state.next_stage = nextStage;
    run.state.allowed_actions = ["continue", "skip", "abort"];
  }

  run.state.progress = estimateRunProgress(run.state.stage_runs);
  saveMockRun(run);

  return review;
}

export async function fetchRunSummary({
  runId,
  formatReview,
  logicReview,
  innovationReview
}) {
  if (!runId) {
    throw createApiError({
      message: "run id is required",
      code: "RUN_NOT_FOUND",
      status: 404
    });
  }

  if (!USE_MOCK) {
    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.getSummary.path,
      {
        method: RUN_API_ENDPOINTS.getSummary.method
      },
      { runId }
    );

    return normalizeSummaryDigest(response, {
      formatReview,
      logicReview,
      innovationReview
    });
  }

  await sleep(140);

  const run = requireMockRun(runId);

  if (!run.summaryPayload) {
    const digest = buildReviewDigest({
      formatReview: formatReview ?? run.stageReviews.format,
      logicReview: logicReview ?? run.stageReviews.logic,
      innovationReview: innovationReview ?? run.stageReviews.innovation
    });

    run.summaryPayload = {
      run_id: runId,
      result_summary: {
        verdict: digest.verdict,
        overview: digest.overview,
        merged_issues: digest.issues.map((item) => ({
          id: item.id,
          title: item.title,
          severity: item.severity,
          stage_name: item.stageKey,
          location: item.location,
          description: item.description,
          evidence: item.evidence,
          suggestion: item.suggestion
        })),
        warnings: digest.skippedAfterStageLabel
          ? [`流程在 ${digest.skippedAfterStageLabel} 后提前收束。`]
          : [],
        suggestions: digest.modificationSuggestions
      }
    };
    saveMockRun(run);
  }

  return normalizeSummaryDigest(
    {
      data: run.summaryPayload
    },
    {
      formatReview: formatReview ?? run.stageReviews.format,
      logicReview: logicReview ?? run.stageReviews.logic,
      innovationReview: innovationReview ?? run.stageReviews.innovation
    }
  );
}

export async function fetchRunSummaryRecord({
  runId,
  formatReview,
  logicReview,
  innovationReview
}) {
  if (!runId) {
    throw createApiError({
      message: "run id is required",
      code: "RUN_NOT_FOUND",
      status: 404
    });
  }

  if (!USE_MOCK) {
    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.getSummary.path,
      {
        method: RUN_API_ENDPOINTS.getSummary.method
      },
      { runId }
    );
    const resultSummary = ensureObject(
      response?.data?.result_summary ?? response?.data?.resultSummary
    );
    const isReady = Object.keys(resultSummary).length > 0;

    return {
      runId,
      resultSummary,
      isReady,
      digest: isReady
        ? normalizeSummaryDigest(response, {
            formatReview,
            logicReview,
            innovationReview
          })
        : null,
      raw: response?.data ?? null
    };
  }

  await sleep(140);

  const run = requireMockRun(runId);
  const resultSummary = ensureObject(run.summaryPayload?.result_summary);
  const isReady = Object.keys(resultSummary).length > 0;

  return {
    runId,
    resultSummary,
    isReady,
    digest: isReady
      ? normalizeSummaryDigest(
          {
            data: run.summaryPayload
          },
          {
            formatReview: formatReview ?? run.stageReviews.format,
            logicReview: logicReview ?? run.stageReviews.logic,
            innovationReview: innovationReview ?? run.stageReviews.innovation
          }
        )
      : null,
    raw: run.summaryPayload ?? null
  };
}

export async function submitPaperMeta({ submissionId, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr;

  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.submitPaperMeta.path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        submissionId,
        paperMeta: meta
      })
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 240));

  return {
    success: true,
    docId: meta?.doc_id ?? "unknown-doc",
    pageCount: getPageCount(meta),
    blockCount: getChunkCount(meta),
    sentAt: new Date().toISOString()
  };
}

export const submitDocumentIr = submitPaperMeta;

export async function runGlobalLogicAudit({ paperMarkdown, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr ?? {};

  if (!USE_MOCK) {
    const response = await fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.task1Audit.path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        mode: "chunked_long",
        paper_bundle: buildPaperBundle({
          paperMarkdown,
          paperMeta: meta
        })
      })
    });

    return normalizeTask1AuditResponse(response);
  }

  await new Promise((resolve) => window.setTimeout(resolve, 260));
  return normalizeTask1AuditResponse(buildMockTask1Audit(meta));
}

export async function generateReviewComment({ submissionId, paperMarkdown, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr;

  try {
    const logicAnalysis = await runGlobalLogicAudit({
      paperMarkdown,
      paperMeta: meta
    });

    return mapTask1AuditToReviewSummary(logicAnalysis);
  } catch (error) {
    if (!USE_MOCK) {
      throw error;
    }

    await new Promise((resolve) => window.setTimeout(resolve, 300));
    return buildMockSummary(meta);
  }
}

export async function runRuleBasedAudit({ paperMarkdown, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr ?? {};

  if (!USE_MOCK) {
    const response = await fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.task2Audit.path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        paper_text: paperMarkdown ?? "",
        meta_data: meta
      })
    });

    return response?.report ?? [];
  }

  await new Promise((resolve) => window.setTimeout(resolve, 240));
  return buildMockTask2Audit().report;
}

function slugifyRecommendationId(value, fallback = "recommended-paper") {
  const seed = String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return seed || fallback;
}

function normalizeRecommendationKeywords(rawKeywords, query = "") {
  const keywords = [];
  const pushKeyword = (value) => {
    const text = String(value ?? "").trim();

    if (!text || keywords.includes(text)) {
      return;
    }

    keywords.push(text);
  };

  if (Array.isArray(rawKeywords)) {
    rawKeywords.forEach(pushKeyword);
  } else if (typeof rawKeywords === "string") {
    rawKeywords
      .split(/[,;，；]/)
      .map((item) => item.trim())
      .filter(Boolean)
      .forEach(pushKeyword);
  }

  String(query ?? "")
    .split(/[\s,;，；:/()]+/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 3)
    .slice(0, 5)
    .forEach(pushKeyword);

  return keywords.slice(0, 5);
}

function buildRecommendationReason(item) {
  const reason =
    item.reason ??
    item.relevance_analysis ??
    item.relevanceAnalysis ??
    "";
  const reasonText = String(reason ?? "").trim();

  if (reasonText) {
    return reasonText;
  }

  const snippet = String(item.snippet ?? item.abstract ?? "").trim();
  const query = String(item.query ?? "").trim();
  const source = String(item.source ?? "").trim() || "外部检索";

  if (snippet) {
    return snippet;
  }

  if (query) {
    return `基于检索词“${query}”从 ${source} 命中，建议作为相关工作参考。`;
  }

  return `该推荐项来自 ${source}，当前未返回更详细的推荐理由。`;
}

function normalizeRecommendationItem(item, index) {
  const data = ensureObject(item);
  const title = data.title ?? `推荐论文 ${index + 1}`;
  const url = data.url ?? data.link ?? "";
  const authors = Array.isArray(data.authors)
    ? data.authors.map((one) => String(one ?? "").trim()).filter(Boolean).join(", ")
    : String(data.authors_text ?? data.authors ?? "").trim();
  const venue = String(data.venue ?? data.source ?? "").trim();
  const relevanceScoreRaw =
    data.relevanceScore ?? data.relevance_score ?? data.score ?? null;
  const citationCount = Number(
    data.citationCount ?? data.citation_count ?? 0
  );
  const abstractText = String(data.abstract ?? data.snippet ?? "").trim();
  const queryText = String(data.query ?? "").trim();
  const reason = buildRecommendationReason(data);
  const keywords = normalizeRecommendationKeywords(data.keywords, queryText);
  const keyTakeaways = ensureArray(data.key_takeaways ?? data.keyTakeaways);
  const normalizedRelevanceScore = Number(relevanceScoreRaw);

  return {
    ...data,
    id:
      data.id ??
      slugifyRecommendationId(url || title, `recommended-paper-${index + 1}`),
    title,
    authors,
    year: data.year ?? "",
    venue: venue || "外部检索",
    relevanceScore: Number.isFinite(normalizedRelevanceScore)
      ? normalizedRelevanceScore
      : null,
    citationCount: Number.isFinite(citationCount) ? citationCount : 0,
    reason,
    keywords,
    abstract: abstractText,
    relevanceAnalysis:
      String(data.relevanceAnalysis ?? data.relevance_analysis ?? "").trim() ||
      reason,
    keyTakeaways:
      keyTakeaways.length > 0
        ? keyTakeaways
        : [queryText ? `命中查询：${queryText}` : "该推荐项来自外部论文检索结果。"],
    link: String(data.link ?? url ?? "").trim(),
    url: String(url ?? "").trim(),
    rank: data.rank ?? index + 1
  };
}

export async function fetchRecommendations({
  runId,
  submissionId,
  documentIr,
  paperMeta
}) {
  const meta = paperMeta ?? documentIr;

  if (!USE_MOCK) {
    if (!runId) {
      throw createApiError({
        message: "run id is required",
        code: "RUN_NOT_FOUND",
        status: 404
      });
    }

    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.getRecommendations.path,
      {
        method: RUN_API_ENDPOINTS.getRecommendations.method
      },
      { runId }
    );
    const data = ensureObject(response?.data);
    const items = ensureArray(data.items);

    return items.map((item, index) => normalizeRecommendationItem(item, index));
  }

  await sleep(260);

  return mockRecommendations.map((item, index) => ({
    ...item,
    rank: index + 1,
    docId: meta?.doc_id ?? submissionId ?? runId
  }));
}

export async function fetchRecommendationsRecord({
  runId,
  submissionId,
  documentIr,
  paperMeta
}) {
  if (!USE_MOCK) {
    if (!runId) {
      throw createApiError({
        message: "run id is required",
        code: "RUN_NOT_FOUND",
        status: 404
      });
    }

    const response = await fetchEnvelope(
      RUN_API_ENDPOINTS.getRecommendations.path,
      {
        method: RUN_API_ENDPOINTS.getRecommendations.method
      },
      { runId }
    );
    const data = ensureObject(response?.data);
    const items = ensureArray(data.items).map((item, index) =>
      normalizeRecommendationItem(item, index)
    );
    const stageStatus = String(
      data.stage_status ?? data.stageStatus ?? "pending"
    ).trim() || "pending";
    const readyFlag = data.ready ?? data.is_ready ?? data.isReady;
    const isReady =
      typeof readyFlag === "boolean"
        ? readyFlag
        : ["completed", "failed", "skipped"].includes(stageStatus);

    return {
      runId,
      items,
      count: Number(data.count ?? items.length) || items.length,
      implemented: data.implemented !== false,
      isReady,
      stageStatus,
      runStatus: String(data.run_status ?? data.runStatus ?? "").trim(),
      raw: data
    };
  }

  const items = await fetchRecommendations({
    runId,
    submissionId,
    documentIr,
    paperMeta
  });

  return {
    runId,
    items,
    count: items.length,
    implemented: true,
    isReady: true,
    stageStatus: "completed",
    runStatus: "",
    raw: null
  };
}

export async function fetchRecommendationDetail(paperId) {
  if (!USE_MOCK) {
    try {
      const response = await fetchJson(
        `${API_BASE_URL}${APP_API_ENDPOINTS.getRecommendationDetail.path.replace(":paperId", paperId)}`
      );

      return response ? normalizeRecommendationItem(response, 0) : null;
    } catch (error) {
      if (
        error instanceof Error &&
        /404|not found/i.test(String(error.message ?? ""))
      ) {
        return null;
      }

      throw error;
    }
  }

  await new Promise((resolve) => window.setTimeout(resolve, 220));
  return mockRecommendationDetails[paperId] ?? null;
}

function pickAnchorsByType(meta, type, limit = 2) {
  return (meta?.anchors ?? []).filter((item) => item.type === type).slice(0, limit);
}

function formatAnchorEvidence(anchor, fallbackLabel) {
  if (!anchor) {
    return fallbackLabel;
  }

  const pageLabel =
    typeof anchor.page_no === "number" ? `第 ${anchor.page_no} 页` : "定位页待补充";
  const anchorLabel = anchor.anchor_id ?? `${anchor.type ?? "anchor"}-anchor`;
  return `${pageLabel} · ${anchorLabel}`;
}

function toStageSeverityLabel(rawSeverity) {
  const severityMap = {
    critical: "严重",
    major: "严重",
    medium: "一般",
    minor: "提示",
    violated: "一般",
    warning: "提示",
    passed: "提示"
  };

  return severityMap[rawSeverity] ?? "一般";
}

function createStageReview({
  stageId,
  stageLabel,
  severe,
  headline,
  overview,
  issues,
  followUpActions = []
}) {
  return {
    stageId,
    stageLabel,
    severe,
    headline,
    overview,
    issues: dedupeStageIssueCards(issues),
    followUpActions
  };
}

function makeWorkflowSuggestion(issue) {
  const dimension = issue?.dimension_keys?.[0] ?? issue?.logical_node ?? "logic";
  const suggestionMap = {
    research_problem_closure:
      "把研究问题、方法假设和结论回扣放在一条连续叙事链上，减少章节之间的断裂感。",
    claim_evidence_conclusion_strength:
      "降低过强结论的措辞，或者补充更直接的实验和证据引用。",
    figure_table_text_consistency:
      "在图表首次出现的位置补一条结论性解释句，明确图表到底支撑什么。",
    method_experiment_alignment:
      "补充方法声明与实验设计的一一对应关系，避免评审觉得验证不充分。",
    scope_and_extrapolation_control:
      "收紧外推范围，并补充适用边界说明。"
  };

  return (
    suggestionMap[dimension] ??
    "把当前问题映射到更具体的章节位置，再补充直接证据或更谨慎的表述。"
  );
}

function buildMockFormatReview(metaSource) {
  const meta = getPaperMeta(metaSource);
  const pageCount = getPageCount(meta);
  const paragraphAnchors = pickAnchorsByType(meta, "paragraph", 2);
  const figureAnchors = pickAnchorsByType(meta, "figure", 2);
  const tableAnchors = pickAnchorsByType(meta, "table", 1);
  const severe = pageCount > 0 && pageCount <= 4;

  const issues = severe
    ? [
        {
          id: "format-critical-1",
          title: "基础版式信息不足，难以支撑后续审查",
          severity: "严重",
          location: "摘要与正文过渡区",
          description:
            "当前稿件在封面、摘要和正文起始区之间缺少稳定的版式提示，格式层证据不足会直接影响后续逻辑与方法审查的定位效率。",
          evidence: [
            formatAnchorEvidence(paragraphAnchors[0], "摘要锚点待补充"),
            formatAnchorEvidence(paragraphAnchors[1], "正文起始锚点待补充")
          ],
          suggestion:
            "优先补齐标题、摘要和正文之间的显式结构提示，再继续进入后续审查。"
        },
        {
          id: "format-major-2",
          title: "图表首现位置缺少格式化引导",
          severity: "一般",
          location: "首个图表引用段落",
          description:
            "图表首次出现时缺少统一的引导句与编号解释，读者很难在第一次阅读时建立稳定的版式映射。",
          evidence: [
            formatAnchorEvidence(figureAnchors[0], "首个图锚点待补充"),
            formatAnchorEvidence(tableAnchors[0], "首个表锚点待补充")
          ],
          suggestion:
            "在每个核心图表首次出现处补一条简短的引导句，明确图表作用和编号对应关系。"
        }
      ]
    : [
        {
          id: "format-major-1",
          title: "摘要到正文的结构提示还不够显式",
          severity: "一般",
          location: "摘要结尾",
          description:
            "当前版面已经具备可读性，但摘要收束后没有马上交代正文的组织方式，格式层的信息引导还可以更明确。",
          evidence: [
            formatAnchorEvidence(paragraphAnchors[0], "摘要尾部锚点待补充"),
            formatAnchorEvidence(paragraphAnchors[1], "引言起始锚点待补充")
          ],
          suggestion:
            "在摘要结尾补一条结构提示句，告诉读者后文将如何展开问题、方法和实验。"
        },
        {
          id: "format-minor-2",
          title: "关键图表的首次呈现缺少统一说明",
          severity: "提示",
          location: "图表首现区",
          description:
            "核心图表已经被解析出来，但首次出现时缺少统一格式的说明语句，审查时需要额外来回定位。",
          evidence: [
            formatAnchorEvidence(figureAnchors[0], "图锚点待补充"),
            formatAnchorEvidence(tableAnchors[0], "表锚点待补充")
          ],
          suggestion:
            "统一图表首现说明格式，减少读者在图表与正文之间反复切换的成本。"
        }
      ];

  return createStageReview({
    stageId: "format",
    stageLabel: "格式审查",
    severe,
    headline: severe ? "格式层发现严重问题" : "格式层已完成首轮检查",
    overview: severe
      ? "格式层已经识别到会影响后续审查的高优先级问题，建议直接进入汇总并优先处理。"
      : "当前稿件可以进入下一阶段，但仍建议先把版式引导和图表首现说明收紧。",
    issues,
    followUpActions: [
      "统一摘要、引言和正文起始段的结构提示。",
      "为核心图表补齐首次出现时的简短说明句。"
    ]
  });
}

function mapTask1IssueToStageIssue(issue, index) {
  return {
    id: issue.issue_id ?? `logic-issue-${index + 1}`,
    title: issue.logical_node ? issue.logical_node.replace(/_/g, " ") : `逻辑问题 ${index + 1}`,
    severity: toStageSeverityLabel(issue.severity),
    location: issue.evidence_links?.[0] ?? `逻辑链路 ${index + 1}`,
    description: issue.analysis ?? "后端尚未返回该问题的详细分析。",
    evidence:
      issue.evidence_links?.length
        ? issue.evidence_links.map((item) => `证据锚点 · ${item}`)
        : ["证据链待后端补充"],
    suggestion: makeWorkflowSuggestion(issue)
  };
}

function buildMockInnovationReview(metaSource) {
  const meta = getPaperMeta(metaSource);
  const paragraphAnchors = pickAnchorsByType(meta, "paragraph", 2);
  const figureAnchors = pickAnchorsByType(meta, "figure", 1);
  const tableAnchors = pickAnchorsByType(meta, "table", 1);

  return createStageReview({
    stageId: "innovation",
    stageLabel: "方法与创新点审查",
    severe: false,
    headline: "方法与创新点审查已完成",
    overview:
      "当前稿件已经具备进入汇总环节的条件，但创新点归因和方法证明链还需要进一步压实。",
    issues: [
      {
        id: "innovation-major-1",
        title: "创新点陈述还不够聚焦",
        severity: "一般",
        location: "方法概述段",
        description:
          "创新点描述更像一组实现细节的堆叠，而不是清晰、可验证的学术主张，审稿人很难快速抓住贡献边界。",
        evidence: [
          formatAnchorEvidence(paragraphAnchors[0], "方法概述锚点待补充"),
          formatAnchorEvidence(figureAnchors[0], "创新示意图锚点待补充")
        ],
        suggestion:
          "把创新点拆成两到三个可验证主张，并分别对应后文中的实验或消融证据。"
      },
      {
        id: "innovation-major-2",
        title: "方法优势与实验收益的对应关系不够直接",
        severity: "一般",
        location: "实验对比段",
        description:
          "实验结果给出了整体提升，但没有把提升与具体方法设计逐一对应，导致创新点的说服力还不够集中。",
        evidence: [
          formatAnchorEvidence(tableAnchors[0], "实验表格锚点待补充"),
          formatAnchorEvidence(paragraphAnchors[1], "实验分析锚点待补充")
        ],
        suggestion:
          "为每个核心创新点补一条对应证据，把方法设计、消融结果和结论表达串成闭环。"
      }
    ],
    followUpActions: [
      "压缩创新点表述，让每条主张都能被后文直接验证。",
      "在实验分析里显式说明每个设计带来的具体收益。"
    ]
  });
}

function mapRuleAuditItemToFormatIssue(item, index) {
  const ruleId = item.rule_id ?? "";
  const ruleLabel = getRuleDisplayLabel(ruleId, "");
  return {
    id: ruleId || `format-issue-${index + 1}`,
    title: ruleLabel || ruleId || `格式问题 ${index + 1}`,
    severity: toStageSeverityLabel(item.severity ?? item.status),
    location: item.location ?? `格式定位 ${index + 1}`,
    description:
      item.message ?? item.evidence ?? "后端尚未返回格式问题的详细说明。",
    evidence: [
      item.location ? `定位区域 · ${item.location}` : "定位区域待补充",
      ruleLabel ? `规则名称 · ${ruleLabel}` : "规则名称待补充",
      ruleId ? `规则编号 · ${ruleId}` : "规则编号待补充"
    ],
    ruleId,
    ruleLabel,
    suggestion: item.suggestion ?? "建议统一当前区域的版式与说明方式。"
  };
}

function mapSummaryWeaknessToInnovationIssue(item, index, suggestion) {
  return {
    id: `innovation-summary-${index + 1}`,
    title: `方法与创新点问题 ${index + 1}`,
    severity: "一般",
    location: `方法与创新点审查 ${index + 1}`,
    description: item,
    evidence: [`汇总证据 · ${item}`],
    suggestion
  };
}

export async function runFormatReview({ paperMarkdown, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr ?? {};

  if (!USE_MOCK) {
    const report = await runRuleBasedAudit({
      paperMarkdown,
      paperMeta: meta
    });
    const issues = (report ?? []).slice(0, 4).map(mapRuleAuditItemToFormatIssue);
    const severe = issues.filter((item) => item.severity === "严重").length >= 2;

    return createStageReview({
      stageId: "format",
      stageLabel: "格式审查",
      severe,
      headline: severe ? "格式层发现严重问题" : "格式层已完成首轮检查",
      overview: severe
        ? "格式层问题已经达到阻断级别，建议直接进入汇总并优先处理。"
        : "格式层问题已经汇总完成，可以继续进入下一阶段。",
      issues,
      followUpActions: issues.map((item) => item.suggestion)
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 220));
  return buildMockFormatReview(meta);
}

export async function runLogicReview({ paperMarkdown, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr ?? {};
  const logicAnalysis = await runGlobalLogicAudit({
    paperMarkdown,
    paperMeta: meta
  });

  const issues = (logicAnalysis?.issues ?? []).map(mapTask1IssueToStageIssue);
  const severe = issues.filter((item) => item.severity === "严重").length >= 2;

  return createStageReview({
    stageId: "logic",
    stageLabel: "逻辑审查",
    severe,
    headline: severe ? "逻辑层发现高优先级风险" : "逻辑层可以继续推进",
    overview:
      logicAnalysis?.core_argument_consistency?.conflict_summary ??
      (severe
        ? "当前逻辑链路中存在多处高优先级冲突，建议先进入汇总并优先修复。"
        : "当前逻辑链路已完成检查，可以进入方法与创新点审查。"),
    issues,
    followUpActions: issues.map((item) => item.suggestion)
  });
}

export async function runInnovationReview({ paperMarkdown, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr ?? {};

  if (!USE_MOCK) {
    const reviewSummary = await generateReviewComment({
      paperMarkdown,
      paperMeta: meta
    });

    const issues = (reviewSummary?.weaknesses ?? [])
      .slice(0, 3)
      .map((item, index) =>
        mapSummaryWeaknessToInnovationIssue(
          item,
          index,
          reviewSummary?.nextActions?.[index] ?? "建议补强方法和创新点的直接证据。"
        )
      );

    return createStageReview({
      stageId: "innovation",
      stageLabel: "方法与创新点审查",
      severe: false,
      headline: "方法与创新点审查已完成",
      overview:
        reviewSummary?.summary ??
        "方法与创新点审查已完成，可以进入汇总环节。",
      issues,
      followUpActions: reviewSummary?.nextActions ?? []
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 240));
  return buildMockInnovationReview(meta);
}

function flattenStageIssues(stageKey, stageLabel, review) {
  return (review?.issues ?? []).map((issue, index) => ({
    ...issue,
    id: `${stageKey}-${issue.id ?? index + 1}`,
    stageKey,
    stageLabel
  }));
}

export function buildReviewDigest({
  formatReview,
  logicReview,
  innovationReview
}) {
  const stageEntries = [
    {
      key: "format",
      label: "格式审查",
      review: formatReview
    },
    {
      key: "logic",
      label: "逻辑审查",
      review: logicReview
    },
    {
      key: "innovation",
      label: "方法与创新点审查",
      review: innovationReview
    }
  ];

  const issues = stageEntries.flatMap(({ key, label, review }) =>
    flattenStageIssues(key, label, review)
  );

  const skippedStage = stageEntries.find(({ review }) => review?.severe);
  const completedCount = stageEntries.filter(({ review }) => Boolean(review)).length;
  const suggestionMap = new Map();

  for (const { key, label, review } of stageEntries) {
    for (const issue of review?.issues ?? []) {
      const content = issue.suggestion?.trim();

      if (!content || suggestionMap.has(content)) {
        continue;
      }

      suggestionMap.set(content, {
        id: `${key}-suggestion-${suggestionMap.size + 1}`,
        title: issue.title,
        content,
        stageLabel: label
      });
    }

    for (const action of review?.followUpActions ?? []) {
      const content = String(action ?? "").trim();

      if (!content || suggestionMap.has(content)) {
        continue;
      }

      suggestionMap.set(content, {
        id: `${key}-follow-up-${suggestionMap.size + 1}`,
        title: `${label}后续动作`,
        content,
        stageLabel: label
      });
    }
  }

  if (!suggestionMap.size) {
    suggestionMap.set("manual-check", {
      id: "manual-check",
      title: "人工复核",
      content: "建议保留一次人工抽检，确认摘要、实验与创新点三处表述一致。",
      stageLabel: "人工补充"
    });
  }

  if (!issues.length) {
    return {
      verdict: "建议继续人工复核",
      overview: "当前还没有足够的阶段结果可供汇总。",
      skippedAfterStage: "",
      skippedAfterStageLabel: "",
      issues: [],
      modificationSuggestions: Array.from(suggestionMap.values())
    };
  }

  if (skippedStage) {
    return {
      verdict: "建议先修复严重问题，再恢复后续审查",
      overview: `在${skippedStage.label}发现严重问题，流程已提前收束到汇总阶段。`,
      skippedAfterStage: skippedStage.key,
      skippedAfterStageLabel: skippedStage.review?.stageLabel ?? skippedStage.label,
      issues,
      modificationSuggestions: Array.from(suggestionMap.values())
    };
  }

  return {
    verdict:
      completedCount === stageEntries.length
        ? "建议进入论文修改与推荐论文对照"
        : "建议按当前结果先处理已识别问题",
    overview:
      completedCount === stageEntries.length
        ? "三阶段审查已完成，可以根据左侧问题和右侧修改建议安排修订。"
        : `已完成 ${completedCount} 个阶段的汇总，可继续补充后续阶段结果。`,
    skippedAfterStage: "",
    skippedAfterStageLabel: "",
    issues,
    modificationSuggestions: Array.from(suggestionMap.values())
  };
}

export function normalizeSummaryDigest(
  payload,
  { formatReview, logicReview, innovationReview } = {}
) {
  const data = ensureObject(payload?.data ?? payload);
  const resultSummary = ensureObject(
    data.result_summary ?? data.resultSummary ?? data.summary ?? data
  );
  const baseDigest = buildReviewDigest({
    formatReview,
    logicReview,
    innovationReview
  });
  const mergedIssues = ensureArray(
    resultSummary.merged_issues ?? resultSummary.mergedIssues ?? resultSummary.issues
  ).map((item, index) => {
    const issue = mapGenericIssue(item, index, "summary");
    const stageKey = coerceStageName(
      item?.stage_name ?? item?.stageName ?? item?.stage ?? item?.source_stage,
      "summary"
    );

    return {
      ...issue,
      stageKey,
      stageLabel: REVIEW_STAGE_LABELS[stageKey] ?? "汇总"
    };
  });
  const summarySuggestions = mergeSuggestionCards(
    resultSummary.suggestions,
    resultSummary.next_actions,
    resultSummary.nextActions
  );
  const warnings = ensureArray(resultSummary.warnings).map(String).filter(Boolean);

  return {
    ...baseDigest,
    verdict: resultSummary.verdict ?? baseDigest.verdict,
    overview:
      resultSummary.overview ??
      resultSummary.summary ??
      (warnings.length ? warnings.join(" ") : baseDigest.overview),
    issues: dedupeStageIssueCards(mergedIssues.length ? mergedIssues : baseDigest.issues),
    warnings,
    modificationSuggestions: mergeSuggestionCards(
      baseDigest.modificationSuggestions,
      summarySuggestions
    )
  };
}

export async function fetchSystemRuleLibrary({ status = "approved" } = {}) {
  if (!USE_MOCK) {
    const search = new URLSearchParams({ status });
    const response = await fetchJson(
      `${API_BASE_URL}${APP_API_ENDPOINTS.task2GetRules.path}?${search.toString()}`
    );

    return (response?.data ?? []).map(mapTask2RuleToLibraryItem);
  }

  await new Promise((resolve) => window.setTimeout(resolve, 180));
  return mockSystemRuleLibraries;
}

export async function saveRuleSelection({
  selectedSystemRuleIds = [],
  customRulesText = ""
}) {
  await new Promise((resolve) => window.setTimeout(resolve, 120));

  return {
    success: true,
    selectedSystemRuleIds,
    customRulesText,
    savedAt: new Date().toISOString()
  };
}

export async function extractCustomRules({ file, text }) {
  const sourceText = text?.trim()
    ? text.trim()
    : file
      ? await readFileAsText(file)
      : "";

  if (!sourceText) {
    throw new Error("请先上传文本文件或输入待抽取的规则说明。");
  }

  if (!USE_MOCK) {
    const response = await fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.task2ExtractRules.path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        review_text: sourceText
      })
    });

    const rules = response?.rules ?? [];

    return {
      sourceText,
      rules: rules.map((item) => item.rule_name ?? item.description ?? "").filter(Boolean),
      extractedRulesText: rules
        .map((item) => item.rule_name ?? item.description ?? "")
        .filter(Boolean)
        .join("\n"),
      extractedAt: new Date().toISOString(),
      raw: response
    };
  }

  await new Promise((resolve) => window.setTimeout(resolve, 260));
  return buildMockExtractedRules(sourceText);
}

export async function toggleBackendRule(ruleId) {
  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.task2ToggleRule.path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        rule_id: ruleId
      })
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 180));
  return {
    msg: `规则 ${ruleId} 状态已切换`
  };
}

function hasObjectContent(value) {
  return isPlainObject(value) && Object.keys(value).length > 0;
}

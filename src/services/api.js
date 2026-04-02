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
  return meta?.anchors?.length ?? meta?.blocks?.length ?? 0;
}

export function countAnchorsByType(submissionOrMeta, type) {
  const meta = getPaperMeta(submissionOrMeta);
  return (meta?.anchors ?? []).filter((anchor) => anchor.type === type).length;
}

function buildMockSummary(metaSource) {
  const paperMeta = getPaperMeta(metaSource);
  const pageCount = getPageCount(paperMeta);
  const anchorCount = getAnchorCount(paperMeta);
  const figureCount = countAnchorsByType(paperMeta, "figure");
  const tableCount = countAnchorsByType(paperMeta, "table");

  return {
    overallScore: Math.min(95, 72 + Math.round(pageCount / 2) + figureCount),
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

async function uploadViaLocalParser(paperFile) {
  const formData = new FormData();
  formData.append(UPLOAD_FORM_FIELDS.paper, paperFile);

  let data;

  try {
    data = await fetchJson(
      `${PARSER_API_BASE_URL}${LOCAL_PARSER_ENDPOINTS.parsePaper.path}`,
      {
        method: "POST",
        body: formData
      }
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "unknown parser error";
    throw new Error(
      `本地解析服务不可用，请先启动 paper-review-system 接口。${message}`
    );
  }

  const paperMeta = data.paperMeta ?? data.documentIr ?? {};

  return {
    submissionId: data.submissionId ?? makeSubmissionId(),
    paperName: data.paperName ?? paperFile?.name ?? "未命名论文",
    paperMarkdown: data.paperMarkdown ?? "",
    paperAssetBase: data.paperAssetBase ?? "",
    paperMeta,
    documentIr: paperMeta,
    uploadedAt: new Date().toISOString(),
    sourceMode: "local-parser-api",
    artifacts: data.artifacts ?? null
  };
}

export async function uploadPaper({
  paperFile,
  markdownFile,
  documentIrFile,
  imageBaseUrl
}) {
  const hasLocalArtifacts = markdownFile && documentIrFile;

  if (USE_LOCAL_PARSER && paperFile) {
    return uploadViaLocalParser(paperFile);
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

    const data = await fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.parsePaper.path}`, {
      method: "POST",
      body: formData
    });

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

  return {
    submissionId: makeSubmissionId(),
    paperName: paperFile?.name ?? paperMeta?.doc_id ?? "示例论文",
    paperMarkdown,
    paperAssetBase: imageBaseUrl || "/mock",
    paperMeta,
    documentIr: paperMeta,
    uploadedAt: new Date().toISOString(),
    sourceMode: hasLocalArtifacts ? "local-artifacts" : "mock"
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
    blockCount: getAnchorCount(meta),
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

export async function fetchRecommendations({ submissionId, documentIr, paperMeta }) {
  const meta = paperMeta ?? documentIr;

  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}${APP_API_ENDPOINTS.listRecommendations.path}`, {
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

  await new Promise((resolve) => window.setTimeout(resolve, 260));

  return mockRecommendations.map((item, index) => ({
    ...item,
    rank: index + 1,
    docId: meta?.doc_id ?? submissionId
  }));
}

export async function fetchRecommendationDetail(paperId) {
  if (!USE_MOCK) {
    return fetchJson(
      `${API_BASE_URL}${APP_API_ENDPOINTS.getRecommendationDetail.path.replace(":paperId", paperId)}`
    );
  }

  await new Promise((resolve) => window.setTimeout(resolve, 220));
  return mockRecommendationDetails[paperId] ?? null;
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

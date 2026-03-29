import { readFileAsJson, readFileAsText } from "../utils/file";

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
      "适合作为后续把 document_ir.json 接入 RAG 流程的设计样板。"
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
      "适合作为 related work 页面的强相关基线。",
      "可帮助解释 document_ir 中图文混排内容如何映射到检测证据。",
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

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }

  return response.json();
}

function makeSubmissionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `submission-${Date.now()}`;
}

function buildMockSummary(documentIr) {
  const pageCount = documentIr?.pages?.length ?? 0;
  const blockCount = documentIr?.blocks?.length ?? 0;
  const headingCount = (documentIr?.blocks ?? []).filter(
    (block) => block.type === "heading"
  ).length;

  return {
    overallScore: Math.min(95, 72 + headingCount + Math.round(pageCount / 2)),
    verdict: "建议大修后进入下一轮评审",
    summary:
      "论文已经具备较清晰的问题定义与结构化内容，但实验论证和贡献表述仍有加强空间，适合在补充证据后继续推进。",
    strengths: [
      `文档结构较完整，已解析出 ${pageCount} 页、${blockCount} 个内容块。`,
      "标题、摘要与正文层次清晰，适合做结构化评审与证据定位。",
      "Markdown 结果可直接用于左侧论文浏览区，便于联动图文与点评。"
    ],
    weaknesses: [
      "目前示例评语仍为 mock 结果，接入真实后端后建议结合规则和大模型双路生成。",
      "推荐论文列表尚未根据真实检索结果动态刷新，需要后端提供召回与排序。",
      "若图片资源由后端托管，需保证 Markdown 中相对路径与 image_base_url 对齐。"
    ],
    nextActions: [
      "补齐后端 /reviews/generate 的真实实现。",
      "将推荐接口返回的论文摘要、作者、来源期刊统一为前端约定字段。",
      "把 document_ir.json 与推荐召回逻辑打通，形成真正的内容相似推荐。"
    ],
    dimensionScores: [
      { label: "创新性", score: 84 },
      { label: "技术深度", score: 81 },
      { label: "表达清晰度", score: 89 },
      { label: "实验充分性", score: 78 }
    ]
  };
}

async function uploadViaLocalParser(paperFile) {
  const formData = new FormData();
  formData.append("paper", paperFile);

  let data;

  try {
    data = await fetchJson(`${PARSER_API_BASE_URL}/papers/parse`, {
      method: "POST",
      body: formData
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "unknown parser error";
    throw new Error(
      `本地解析服务不可用，请先启动 paper-review-system 接口。${message}`
    );
  }

  return {
    submissionId: data.submissionId ?? makeSubmissionId(),
    paperName: data.paperName ?? paperFile?.name ?? "未命名论文",
    paperMarkdown: data.paperMarkdown ?? "",
    paperAssetBase: data.paperAssetBase ?? "",
    documentIr: data.documentIr ?? {},
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
      formData.append("paper", paperFile);
    }

    if (markdownFile) {
      formData.append("markdown_file", markdownFile);
    }

    if (documentIrFile) {
      formData.append("document_ir_file", documentIrFile);
    }

    if (imageBaseUrl) {
      formData.append("image_base_url", imageBaseUrl);
    }

    const data = await fetchJson(`${API_BASE_URL}/papers/parse`, {
      method: "POST",
      body: formData
    });

    return {
      submissionId: data.submissionId ?? makeSubmissionId(),
      paperName: data.paperName ?? paperFile?.name ?? "未命名论文",
      paperMarkdown: data.paperMarkdown ?? "",
      paperAssetBase: data.paperAssetBase ?? imageBaseUrl ?? "",
      documentIr: data.documentIr ?? {},
      uploadedAt: new Date().toISOString(),
      sourceMode: "api"
    };
  }

  const paperMarkdown = hasLocalArtifacts
    ? await readFileAsText(markdownFile)
    : await fetch("/mock/paper.md").then((response) => response.text());
  const documentIr = hasLocalArtifacts
    ? await readFileAsJson(documentIrFile)
    : await fetchJson("/mock/document_ir.json");

  return {
    submissionId: makeSubmissionId(),
    paperName: paperFile?.name ?? documentIr?.doc_id ?? "示例论文",
    paperMarkdown,
    paperAssetBase: imageBaseUrl || "/mock",
    documentIr,
    uploadedAt: new Date().toISOString(),
    sourceMode: hasLocalArtifacts ? "local-artifacts" : "mock"
  };
}

export async function submitDocumentIr({ submissionId, documentIr }) {
  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}/papers/document-ir`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        submissionId,
        documentIr
      })
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 240));

  return {
    success: true,
    docId: documentIr?.doc_id ?? "unknown-doc",
    pageCount: documentIr?.pages?.length ?? 0,
    blockCount: documentIr?.blocks?.length ?? 0,
    sentAt: new Date().toISOString()
  };
}

export async function generateReviewComment({ submissionId, documentIr }) {
  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}/reviews/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        submissionId,
        documentIr
      })
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 300));
  return buildMockSummary(documentIr);
}

export async function fetchRecommendations({ submissionId, documentIr }) {
  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}/recommendations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        submissionId,
        documentIr
      })
    });
  }

  await new Promise((resolve) => window.setTimeout(resolve, 260));

  return mockRecommendations.map((item, index) => ({
    ...item,
    rank: index + 1,
    docId: documentIr?.doc_id ?? submissionId
  }));
}

export async function fetchRecommendationDetail(paperId) {
  if (!USE_MOCK) {
    return fetchJson(`${API_BASE_URL}/recommendations/${paperId}`);
  }

  await new Promise((resolve) => window.setTimeout(resolve, 220));
  return mockRecommendationDetails[paperId] ?? null;
}

export const LOCAL_PARSER_ENDPOINTS = Object.freeze({
  health: {
    method: "GET",
    path: "/health"
  },
  parsePaperProgress: {
    method: "GET",
    path: "/papers/parse-progress/:submissionId"
  },
  parsePaper: {
    method: "POST",
    path: "/papers/parse"
  }
});

export const APP_API_ENDPOINTS = Object.freeze({
  parsePaper: {
    method: "POST",
    path: "/papers/parse"
  },
  task1Audit: {
    method: "POST",
    path: "/api/task1/audit"
  },
  task2Audit: {
    method: "POST",
    path: "/api/task2/audit/"
  },
  task2ExtractRules: {
    method: "POST",
    path: "/api/task2/extract/"
  },
  task2GetRules: {
    method: "GET",
    path: "/api/task2/get_rules/"
  },
  task2ToggleRule: {
    method: "POST",
    path: "/api/task2/toggle_rule/"
  },
  submitPaperMeta: {
    method: "POST",
    path: "/papers/paper-meta"
  },
  generateReview: {
    method: "POST",
    path: "/reviews/generate"
  },
  listRecommendations: {
    method: "POST",
    path: "/recommendations"
  },
  getRecommendationDetail: {
    method: "GET",
    path: "/recommendations/:paperId"
  },
  listSystemRules: {
    method: "GET",
    path: "/api/task2/get_rules/"
  },
  saveRuleSelection: {
    method: "LOCAL",
    path: "sessionStorage:ruleLibrary"
  },
  extractCustomRules: {
    method: "POST",
    path: "/api/task2/extract/"
  }
});

export const UPLOAD_FORM_FIELDS = Object.freeze({
  paper: "paper",
  submissionId: "submission_id",
  markdownFile: "markdown_file",
  paperMetaFile: "paper_meta_file",
  legacyDocumentIrFile: "document_ir_file",
  imageBaseUrl: "image_base_url",
  customRuleFile: "rule_text_file",
  customRuleText: "rule_text"
});

/**
 * @typedef {Object} ParseProgressResponse
 * @property {string} submissionId
 * @property {"queued"|"processing"|"completed"|"failed"} status
 * @property {string} phase
 * @property {number} fraction
 * @property {number} percent
 * @property {string=} message
 * @property {number=} currentChunk
 * @property {number=} totalChunks
 * @property {number=} pageStart
 * @property {number=} pageEnd
 * @property {string} updatedAt
 */

/**
 * @typedef {Object} AnchorRecord
 * @property {string} anchor_id
 * @property {"paragraph"|"figure"|"table"} type
 * @property {number} page_no
 * @property {string=} section
 * @property {string=} text
 * @property {string=} figure_id
 * @property {string=} image_path
 * @property {string=} table_id
 * @property {string=} table_path
 * @property {string=} screenshot_path
 * @property {string=} caption
 */

/**
 * @typedef {Object} PaperMeta
 * @property {string} doc_id
 * @property {string} source_pdf
 * @property {number} total_pages
 * @property {string} parser_version
 * @property {AnchorRecord[]} anchors
 */

/**
 * @typedef {Object} ParseArtifacts
 * @property {string} markdownPath
 * @property {string} paperMetaPath
 * @property {string} bundleDir
 * @property {string} outputDir
 */

/**
 * @typedef {Object} ParsePaperResponse
 * @property {string} submissionId
 * @property {string} paperName
 * @property {string} paperMarkdown
 * @property {string} paperAssetBase
 * @property {PaperMeta} paperMeta
 * @property {ParseArtifacts=} artifacts
 */

/**
 * @typedef {Object} SubmitPaperMetaRequest
 * @property {string} submissionId
 * @property {PaperMeta} paperMeta
 */

/**
 * @typedef {Object} SubmitPaperMetaResponse
 * @property {boolean} success
 * @property {string} docId
 * @property {number} pageCount
 * @property {number} blockCount
 * @property {string} sentAt
 */

/**
 * @typedef {Object} ReviewDimensionScore
 * @property {string} label
 * @property {number} score
 */

/**
 * @typedef {Object} ReviewSummary
 * @property {number} overallScore
 * @property {string} verdict
 * @property {string} summary
 * @property {string[]} strengths
 * @property {string[]} weaknesses
 * @property {string[]} nextActions
 * @property {ReviewDimensionScore[]} dimensionScores
 */

/**
 * @typedef {Object} RecommendationItem
 * @property {string} id
 * @property {string} title
 * @property {string} authors
 * @property {number} year
 * @property {string} venue
 * @property {number} relevanceScore
 * @property {string} reason
 * @property {string[]} keywords
 * @property {number=} rank
 * @property {string=} docId
 */

/**
 * @typedef {Object} RecommendationDetail
 * @property {string} id
 * @property {string} title
 * @property {string} authors
 * @property {number} year
 * @property {string} venue
 * @property {number} relevanceScore
 * @property {string} abstract
 * @property {string} relevanceAnalysis
 * @property {string[]} keyTakeaways
 * @property {string[]} keywords
 * @property {string} link
 */

/**
 * @typedef {Object} RuleLibraryItem
 * @property {string} id
 * @property {string} title
 * @property {string} category
 * @property {string} summary
 * @property {string[]} tags
 * @property {number=} questionCount
 * @property {boolean=} defaultSelected
 */

/**
 * @typedef {Object} RuleSelectionPayload
 * @property {string[]} selectedSystemRuleIds
 * @property {string} customRulesText
 */

/**
 * @typedef {Object} RuleSelectionResponse
 * @property {boolean} success
 * @property {string[]} selectedSystemRuleIds
 * @property {string} customRulesText
 * @property {string} savedAt
 */

/**
 * @typedef {Object} CustomRuleExtractionResponse
 * @property {string} sourceText
 * @property {string} extractedRulesText
 * @property {string[]} rules
 * @property {string} extractedAt
 */

/**
 * @typedef {Object} LogicEvidenceLink
 * @property {string=} section_title
 * @property {string=} section
 * @property {string=} quote
 * @property {string=} snippet
 * @property {string=} full_text
 * @property {string=} anchor_id
 * @property {string=} anchor
 * @property {string=} reason
 */

/**
 * @typedef {Object} Task1AuditIssue
 * @property {string} issue_id
 * @property {string} logical_node
 * @property {string=} issue_title
 * @property {"critical"|"major"|"medium"|"minor"} severity
 * @property {string} analysis
 * @property {(string|LogicEvidenceLink)[]} evidence_links
 * @property {string=} scope
 * @property {string[]=} dimension_keys
 * @property {number=} confidence
 * @property {boolean=} needs_human_review
 */

/**
 * @typedef {Object} Task1DimensionResult
 * @property {"pass"|"risk"|"fail"} status
 * @property {string} summary
 * @property {string[]} issue_ids
 * @property {string[]} evidence_links
 */

/**
 * @typedef {Object} Task1LogicAnalysis
 * @property {{is_consistent:boolean, conflict_summary:string}=} core_argument_consistency
 * @property {Record<string, Task1DimensionResult>=} logic_dimensions
 * @property {Task1AuditIssue[]=} issues
 * @property {{assessment:string}=} reasoning_depth
 * @property {{assessment:string}=} structure_rationality
 * @property {number=} chunk_count
 */

/**
 * @typedef {Object} Task1AuditResponse
 * @property {number} code
 * @property {string} message
 * @property {{schema_version:string, mode:string, result:{logic_analysis:Task1LogicAnalysis}}=} data
 */

/**
 * @typedef {Object} Task2AuditItem
 * @property {string} rule_id
 * @property {"violated"|"passed"|"warning"=} status
 * @property {string=} location
 * @property {string=} evidence
 * @property {string=} suggestion
 */

/**
 * @typedef {Object} Task2AuditResponse
 * @property {string} msg
 * @property {Task2AuditItem[]} report
 */

/**
 * @typedef {Object} Task2ExtractedRule
 * @property {string=} rule_id
 * @property {string} rule_name
 * @property {string} dimension
 * @property {string} execution_type
 * @property {string[]=} triggers
 * @property {string=} description
 * @property {string=} prompt_fragment
 * @property {string=} severity
 * @property {boolean=} is_active
 * @property {string=} status
 */

/**
 * @typedef {Object} Task2ExtractRulesResponse
 * @property {string} msg
 * @property {number} extracted_total
 * @property {number} saved_to_pending
 * @property {Task2ExtractedRule[]} rules
 */

export const API_CONTRACT = Object.freeze({
  localParser: {
    parsePaper: {
      ...LOCAL_PARSER_ENDPOINTS.parsePaper,
      contentType: "multipart/form-data",
      requestFields: [UPLOAD_FORM_FIELDS.paper],
      responseShape: "ParsePaperResponse"
    }
  },
  frontendReserved: {
    parsePaper: {
      ...APP_API_ENDPOINTS.parsePaper,
      contentType: "multipart/form-data",
      requestFields: [
        UPLOAD_FORM_FIELDS.paper,
        UPLOAD_FORM_FIELDS.markdownFile,
        UPLOAD_FORM_FIELDS.paperMetaFile,
        UPLOAD_FORM_FIELDS.legacyDocumentIrFile,
        UPLOAD_FORM_FIELDS.imageBaseUrl
      ],
      responseShape: "ParsePaperResponse"
    },
    task1Audit: {
      ...APP_API_ENDPOINTS.task1Audit,
      contentType: "application/json",
      requestShape: "{ mode: 'chunked_long', paper_bundle: { paper_md, paper_meta, assets } }",
      responseShape: "Task1AuditResponse"
    },
    task2Audit: {
      ...APP_API_ENDPOINTS.task2Audit,
      contentType: "application/json",
      requestShape: "{ paper_text, meta_data }",
      responseShape: "Task2AuditResponse"
    },
    task2ExtractRules: {
      ...APP_API_ENDPOINTS.task2ExtractRules,
      contentType: "application/json",
      requestShape: "{ review_text }",
      responseShape: "Task2ExtractRulesResponse"
    },
    task2GetRules: {
      ...APP_API_ENDPOINTS.task2GetRules,
      contentType: "application/json",
      requestShape: "query: { status }",
      responseShape: "Task2ExtractedRule[]"
    },
    task2ToggleRule: {
      ...APP_API_ENDPOINTS.task2ToggleRule,
      contentType: "application/json",
      requestShape: "{ rule_id }",
      responseShape: "{ msg }"
    },
    submitPaperMeta: {
      ...APP_API_ENDPOINTS.submitPaperMeta,
      contentType: "application/json",
      requestShape: "SubmitPaperMetaRequest",
      responseShape: "SubmitPaperMetaResponse"
    },
    generateReview: {
      ...APP_API_ENDPOINTS.generateReview,
      contentType: "application/json",
      requestShape: "SubmitPaperMetaRequest",
      responseShape: "ReviewSummary"
    },
    listRecommendations: {
      ...APP_API_ENDPOINTS.listRecommendations,
      contentType: "application/json",
      requestShape: "SubmitPaperMetaRequest",
      responseShape: "RecommendationItem[]"
    },
    getRecommendationDetail: {
      ...APP_API_ENDPOINTS.getRecommendationDetail,
      contentType: "application/json",
      responseShape: "RecommendationDetail"
    },
    listSystemRules: {
      ...APP_API_ENDPOINTS.task2GetRules,
      contentType: "application/json",
      responseShape: "RuleLibraryItem[]"
    },
    saveRuleSelection: {
      ...APP_API_ENDPOINTS.saveRuleSelection,
      contentType: "local-session",
      requestShape: "RuleSelectionPayload",
      responseShape: "RuleSelectionResponse"
    },
    extractCustomRules: {
      ...APP_API_ENDPOINTS.task2ExtractRules,
      contentType: "application/json",
      requestShape: "{ review_text }",
      responseShape: "CustomRuleExtractionResponse"
    }
  }
});

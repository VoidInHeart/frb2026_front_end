export const LOCAL_PARSER_ENDPOINTS = Object.freeze({
  health: {
    method: "GET",
    path: "/health"
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
  }
});

export const UPLOAD_FORM_FIELDS = Object.freeze({
  paper: "paper",
  markdownFile: "markdown_file",
  paperMetaFile: "paper_meta_file",
  legacyDocumentIrFile: "document_ir_file",
  imageBaseUrl: "image_base_url"
});

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
    }
  }
});

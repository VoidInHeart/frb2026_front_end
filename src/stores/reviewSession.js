import { reactive, watch } from "vue";

const STORAGE_KEY = "paper-review-session-v4";

export const REVIEW_STAGE_IDS = Object.freeze([
  "format",
  "logic",
  "innovation",
  "summary"
]);

const DEFAULT_STAGE = "format";

function createWorkflowState() {
  return {
    currentStage: DEFAULT_STAGE,
    reviews: {
      format: null,
      logic: null,
      innovation: null
    },
    summary: null
  };
}

function createInitialState() {
  return {
    currentSubmission: null,
    runRecord: null,
    runState: null,
    recommendations: [],
    recommendationDetails: {},
    preferences: {
      showImages: true
    },
    workflow: createWorkflowState()
  };
}

function readStoredState() {
  if (typeof window === "undefined") {
    return createInitialState();
  }

  const raw = window.sessionStorage.getItem(STORAGE_KEY);

  if (!raw) {
    return createInitialState();
  }

  try {
    const parsed = JSON.parse(raw);

    return {
      ...createInitialState(),
      ...parsed,
      workflow: {
        ...createWorkflowState(),
        ...parsed.workflow,
        reviews: {
          ...createWorkflowState().reviews,
          ...parsed.workflow?.reviews
        }
      }
    };
  } catch {
    return createInitialState();
  }
}

export const reviewSession = reactive(readStoredState());

watch(
  reviewSession,
  (value) => {
    if (typeof window === "undefined") {
      return;
    }

    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  },
  { deep: true }
);

export function setSubmission(submission) {
  reviewSession.currentSubmission = submission;
  reviewSession.runRecord = null;
  reviewSession.runState = null;
  reviewSession.recommendations = [];
  reviewSession.recommendationDetails = {};
  reviewSession.workflow = createWorkflowState();
}

export function setRunRecord(record) {
  reviewSession.runRecord = record;
}

export function setRunState(state) {
  reviewSession.runState = state;
}

export function setRecommendations(items) {
  reviewSession.recommendations = items;
}

export function setRecommendationDetail(id, detail) {
  reviewSession.recommendationDetails = {
    ...reviewSession.recommendationDetails,
    [id]: detail
  };
}

export function setShowImages(showImages) {
  reviewSession.preferences.showImages = showImages;
}

export function setCurrentStage(stage) {
  if (!REVIEW_STAGE_IDS.includes(stage)) {
    return;
  }

  reviewSession.workflow.currentStage = stage;
}

export function setStageReview(stage, payload) {
  if (!(stage in reviewSession.workflow.reviews)) {
    return;
  }

  reviewSession.workflow.reviews[stage] = payload;
}

export function setWorkflowSummary(summary) {
  reviewSession.workflow.summary = summary;
}

export function clearSession() {
  Object.assign(reviewSession, createInitialState());
}

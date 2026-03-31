import { reactive, watch } from "vue";

const STORAGE_KEY = "paper-review-session-v1";

function createInitialState() {
  return {
    currentSubmission: null,
    transmissionStatus: null,
    reviewSummary: null,
    recommendations: [],
    recommendationDetails: {},
    preferences: {
      showImages: true
    },
    ruleLibrary: {
      systemRules: [],
      selectedSystemRuleIds: [],
      customRuleSourceText: "",
      customRulesText: "",
      customRuleFileName: "",
      savedAt: ""
    }
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
      ruleLibrary: {
        ...createInitialState().ruleLibrary,
        ...parsed.ruleLibrary
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
  reviewSession.transmissionStatus = null;
  reviewSession.reviewSummary = null;
  reviewSession.recommendations = [];
  reviewSession.recommendationDetails = {};
}

export function setTransmissionStatus(status) {
  reviewSession.transmissionStatus = status;
}

export function setReviewSummary(summary) {
  reviewSession.reviewSummary = summary;
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

export function setRuleLibraryCatalog(items) {
  reviewSession.ruleLibrary.systemRules = items;

  if (!reviewSession.ruleLibrary.selectedSystemRuleIds.length) {
    reviewSession.ruleLibrary.selectedSystemRuleIds = items
      .filter((item) => item.defaultSelected)
      .map((item) => item.id);
  }
}

export function setSelectedSystemRuleIds(ids) {
  reviewSession.ruleLibrary.selectedSystemRuleIds = [...ids];
}

export function toggleSystemRuleSelection(ruleId) {
  const ids = new Set(reviewSession.ruleLibrary.selectedSystemRuleIds);

  if (ids.has(ruleId)) {
    ids.delete(ruleId);
  } else {
    ids.add(ruleId);
  }

  reviewSession.ruleLibrary.selectedSystemRuleIds = [...ids];
}

export function setCustomRuleSourceText(text) {
  reviewSession.ruleLibrary.customRuleSourceText = text;
}

export function setCustomRulesText(text) {
  reviewSession.ruleLibrary.customRulesText = text;
}

export function setCustomRuleFileName(name) {
  reviewSession.ruleLibrary.customRuleFileName = name;
}

export function markRuleLibrarySaved(savedAt) {
  reviewSession.ruleLibrary.savedAt = savedAt;
}

export function clearSession() {
  Object.assign(reviewSession, createInitialState());
}

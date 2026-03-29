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
    return {
      ...createInitialState(),
      ...JSON.parse(raw)
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

export function clearSession() {
  Object.assign(reviewSession, createInitialState());
}

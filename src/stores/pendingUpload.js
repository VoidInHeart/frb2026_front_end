import { shallowRef } from "vue";

const pendingUpload = shallowRef(null);

export function stagePendingUpload(payload) {
  pendingUpload.value = payload
    ? {
        ...payload,
        stagedAt: new Date().toISOString()
      }
    : null;
}

export function getPendingUpload() {
  return pendingUpload.value;
}

export function clearPendingUpload() {
  pendingUpload.value = null;
}

<script setup>
import { computed } from "vue";
import { renderMarkdownHtml } from "../utils/markdown";

const props = defineProps({
  markdown: {
    type: String,
    default: ""
  },
  showImages: {
    type: Boolean,
    default: true
  },
  assetBase: {
    type: String,
    default: ""
  }
});

const renderedHtml = computed(() =>
  renderMarkdownHtml(props.markdown, {
    showImages: props.showImages,
    assetBase: props.assetBase
  })
);
</script>

<template>
  <article
    v-if="renderedHtml"
    class="article-frame markdown-preview"
    v-html="renderedHtml"
  ></article>
  <article v-else class="article-frame">
    <div class="empty-state">No markdown content available.</div>
  </article>
</template>

<style scoped>
.article-frame {
  color: #24292f;
}

.markdown-preview {
  padding: 0 6px 0 0;
  font-size: 16px;
  line-height: 1.75;
}

.markdown-preview :deep(*) {
  box-sizing: border-box;
}

.markdown-preview :deep(h1),
.markdown-preview :deep(h2),
.markdown-preview :deep(h3),
.markdown-preview :deep(h4),
.markdown-preview :deep(h5),
.markdown-preview :deep(h6) {
  margin: 1.4em 0 0.7em;
  line-height: 1.3;
  font-weight: 700;
  color: #0f2740;
}

.markdown-preview :deep(h1) {
  margin-top: 0;
  padding-bottom: 0.3em;
  border-bottom: 1px solid rgba(31, 42, 55, 0.12);
  font-size: 2em;
}

.markdown-preview :deep(h2) {
  padding-bottom: 0.25em;
  border-bottom: 1px solid rgba(31, 42, 55, 0.1);
  font-size: 1.5em;
}

.markdown-preview :deep(h3) {
  font-size: 1.25em;
}

.markdown-preview :deep(p),
.markdown-preview :deep(ul),
.markdown-preview :deep(ol),
.markdown-preview :deep(blockquote),
.markdown-preview :deep(table),
.markdown-preview :deep(pre) {
  margin: 0 0 16px;
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  padding-left: 2em;
}

.markdown-preview :deep(li + li) {
  margin-top: 0.35em;
}

.markdown-preview :deep(a) {
  color: #0969da;
  text-decoration: none;
}

.markdown-preview :deep(a:hover) {
  text-decoration: underline;
}

.markdown-preview :deep(blockquote) {
  padding: 0 1em;
  color: #57606a;
  border-left: 0.25em solid #d0d7de;
}

.markdown-preview :deep(code) {
  padding: 0.15em 0.35em;
  background: rgba(175, 184, 193, 0.2);
  border-radius: 6px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
}

.markdown-preview :deep(pre) {
  overflow: auto;
  padding: 16px;
  border-radius: 12px;
  background: #f6f8fa;
  border: 1px solid rgba(31, 42, 55, 0.08);
}

.markdown-preview :deep(pre code) {
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.markdown-preview :deep(hr) {
  height: 1px;
  margin: 24px 0;
  border: 0;
  background: #d8dee4;
}

.markdown-preview :deep(table) {
  display: block;
  width: 100%;
  overflow: auto;
  border-collapse: collapse;
}

.markdown-preview :deep(th),
.markdown-preview :deep(td) {
  padding: 8px 12px;
  border: 1px solid #d0d7de;
}

.markdown-preview :deep(th) {
  background: #f6f8fa;
  font-weight: 700;
}

.markdown-preview :deep(img) {
  display: block;
  max-width: 100%;
  max-height: 560px;
  margin: 18px auto;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 39, 64, 0.08);
}

.markdown-preview :deep(p > img:only-child) {
  margin-top: 8px;
}
</style>

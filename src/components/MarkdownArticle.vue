<script setup>
import { computed } from "vue";
import { parseMarkdownToBlocks } from "../utils/markdown";

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

const blocks = computed(() =>
  parseMarkdownToBlocks(props.markdown, {
    showImages: props.showImages,
    assetBase: props.assetBase
  })
);
</script>

<template>
  <article class="article-frame">
    <template v-if="blocks.length">
      <template v-for="(block, index) in blocks" :key="`${block.type}-${index}`">
        <h1
          v-if="block.type === 'heading' && block.level === 1"
          class="article-heading article-heading-1"
          v-html="block.html"
        ></h1>
        <h2
          v-else-if="block.type === 'heading' && block.level === 2"
          class="article-heading article-heading-2"
          v-html="block.html"
        ></h2>
        <h3
          v-else-if="block.type === 'heading'"
          class="article-heading article-heading-3"
          v-html="block.html"
        ></h3>
        <p
          v-else-if="block.type === 'paragraph'"
          class="article-paragraph"
          v-html="block.html"
        ></p>
        <blockquote
          v-else-if="block.type === 'blockquote'"
          class="article-quote"
          v-html="block.html"
        ></blockquote>
        <ul
          v-else-if="block.type === 'list' && !block.ordered"
          class="article-list"
        >
          <li
            v-for="(item, itemIndex) in block.items"
            :key="`list-${index}-${itemIndex}`"
            v-html="item.html"
          ></li>
        </ul>
        <ol
          v-else-if="block.type === 'list' && block.ordered"
          class="article-list"
        >
          <li
            v-for="(item, itemIndex) in block.items"
            :key="`olist-${index}-${itemIndex}`"
            v-html="item.html"
          ></li>
        </ol>
        <hr v-else-if="block.type === 'divider'" class="article-divider" />
        <figure v-else-if="block.type === 'image'" class="article-image-card">
          <img :src="block.src" :alt="block.alt" class="article-image" />
          <figcaption>{{ block.alt }}</figcaption>
        </figure>
      </template>
    </template>
    <div v-else class="empty-state">当前没有可展示的 Markdown 内容。</div>
  </article>
</template>

<style scoped>
.article-frame {
  display: grid;
  gap: 16px;
}

.article-heading {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: #102f4c;
}

.article-heading-1 {
  font-size: 32px;
}

.article-heading-2 {
  font-size: 24px;
}

.article-heading-3 {
  font-size: 20px;
}

.article-paragraph {
  margin: 0;
  font-size: 16px;
  color: var(--text);
  line-height: 1.8;
}

.article-quote {
  margin: 0;
  padding: 14px 18px;
  border-left: 4px solid rgba(208, 122, 53, 0.6);
  background: rgba(208, 122, 53, 0.08);
  border-radius: 0 14px 14px 0;
  color: #78451d;
}

.article-list {
  margin: 0;
  padding-left: 22px;
  display: grid;
  gap: 10px;
}

.article-divider {
  width: 100%;
  border: none;
  border-top: 1px solid rgba(19, 63, 103, 0.14);
}

.article-image-card {
  margin: 0;
  padding: 16px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(19, 63, 103, 0.1);
  border-radius: 22px;
  display: grid;
  gap: 12px;
}

.article-image {
  width: 100%;
  border-radius: 16px;
  object-fit: contain;
  max-height: 520px;
  background: #fff;
}

.article-image-card figcaption {
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}

:deep(a) {
  color: var(--primary);
  text-decoration: underline;
}

:deep(code) {
  padding: 2px 6px;
  background: rgba(19, 63, 103, 0.08);
  border-radius: 8px;
}
</style>

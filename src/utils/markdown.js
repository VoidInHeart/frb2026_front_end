function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(text) {
  return escapeHtml(text).replaceAll("`", "&#96;");
}

function formatInline(text) {
  let result = escapeHtml(text);

  result = result.replace(/`([^`]+)`/g, "<code>$1</code>");
  result = result.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  result = result.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  result = result.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_match, label, url) =>
      `<a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`
  );

  return result;
}

function normalizeBase(basePath) {
  if (!basePath) {
    return "";
  }

  return basePath.endsWith("/") ? basePath.slice(0, -1) : basePath;
}

export function resolveAssetUrl(src, basePath = "") {
  if (!src) {
    return "";
  }

  if (/^(https?:|data:|blob:|\/)/.test(src)) {
    return src;
  }

  const cleanBase = normalizeBase(basePath);
  return cleanBase ? `${cleanBase}/${src}` : src;
}

function flushParagraph(blocks, buffer) {
  if (!buffer.length) {
    return;
  }

  blocks.push({
    type: "paragraph",
    html: formatInline(buffer.join(" "))
  });
  buffer.length = 0;
}

function flushList(blocks, listBuffer) {
  if (!listBuffer.length) {
    return;
  }

  blocks.push({
    type: "list",
    ordered: listBuffer.every((item) => item.ordered),
    items: listBuffer.map((item) => ({
      html: formatInline(item.text)
    }))
  });
  listBuffer.length = 0;
}

function flushQuote(blocks, quoteBuffer) {
  if (!quoteBuffer.length) {
    return;
  }

  blocks.push({
    type: "blockquote",
    html: formatInline(quoteBuffer.join(" "))
  });
  quoteBuffer.length = 0;
}

export function parseMarkdownToBlocks(
  markdown,
  { showImages = true, assetBase = "" } = {}
) {
  const lines = String(markdown ?? "").replaceAll("\r\n", "\n").split("\n");
  const blocks = [];
  const paragraphBuffer = [];
  const listBuffer = [];
  const quoteBuffer = [];

  const flushAll = () => {
    flushParagraph(blocks, paragraphBuffer);
    flushList(blocks, listBuffer);
    flushQuote(blocks, quoteBuffer);
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushAll();
      continue;
    }

    const imageMatch = line.match(/^!\[(.*?)\]\((.+?)\)$/);

    if (imageMatch) {
      flushAll();

      if (showImages) {
        blocks.push({
          type: "image",
          alt: imageMatch[1],
          src: resolveAssetUrl(imageMatch[2], assetBase)
        });
      }
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);

    if (headingMatch) {
      flushAll();
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        html: formatInline(headingMatch[2])
      });
      continue;
    }

    const quoteMatch = line.match(/^>\s?(.*)$/);

    if (quoteMatch) {
      flushParagraph(blocks, paragraphBuffer);
      flushList(blocks, listBuffer);
      quoteBuffer.push(quoteMatch[1]);
      continue;
    }

    const orderedMatch = line.match(/^(\d+)\.\s+(.+)$/);
    const unorderedMatch = line.match(/^[-*]\s+(.+)$/);

    if (orderedMatch || unorderedMatch) {
      flushParagraph(blocks, paragraphBuffer);
      flushQuote(blocks, quoteBuffer);
      listBuffer.push({
        ordered: Boolean(orderedMatch),
        text: orderedMatch ? orderedMatch[2] : unorderedMatch[1]
      });
      continue;
    }

    if (/^---+$/.test(line)) {
      flushAll();
      blocks.push({ type: "divider" });
      continue;
    }

    paragraphBuffer.push(line);
  }

  flushAll();

  return blocks;
}

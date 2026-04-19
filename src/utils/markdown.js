import MarkdownIt from "markdown-it";

const FORMULA_BLOCK_TOKEN_PREFIX = "DOC_FORMULA_BLOCK_";

function normalizeBase(basePath) {
  if (!basePath) {
    return "";
  }

  return basePath.endsWith("/") ? basePath.slice(0, -1) : basePath;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function preserveFormulaBlocks(markdown) {
  const formulas = [];
  const transformed = markdown.replace(
    /(^|\n)\$\$\s*\n?([\s\S]*?)\n?\$\$(?=\n|$)/g,
    (match, leading, content) => {
      const formula = String(content ?? "").trim();

      if (!formula) {
        return match;
      }

      const index = formulas.push(formula) - 1;
      return `${leading}${FORMULA_BLOCK_TOKEN_PREFIX}${index}`;
    }
  );

  return {
    markdown: transformed,
    formulas
  };
}

function injectFormulaBlocks(html, formulas) {
  if (!formulas.length) {
    return html;
  }

  return html.replace(
    new RegExp(`<p>\\s*${FORMULA_BLOCK_TOKEN_PREFIX}(\\d+)\\s*</p>`, "g"),
    (match, indexText) => {
      const formula = formulas[Number(indexText)];

      if (!formula) {
        return match;
      }

      return [
        '<div class="math-block" data-docling-formula="true">',
        '<div class="math-block-label">Formula</div>',
        `<pre class="math-block-body"><code>${escapeHtml(formula)}</code></pre>`,
        "</div>"
      ].join("");
    }
  );
}

export function resolveAssetUrl(src, basePath = "") {
  if (!src) {
    return "";
  }

  if (/^(https?:|data:|blob:|\/|#)/.test(src)) {
    return src;
  }

  const cleanBase = normalizeBase(basePath);
  return cleanBase ? `${cleanBase}/${src}` : src;
}

function createMarkdownRenderer({ showImages = true, assetBase = "" } = {}) {
  const md = new MarkdownIt({
    html: false,
    linkify: true,
    typographer: true,
    breaks: false
  });

  const defaultImageRenderer =
    md.renderer.rules.image ||
    ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options));

  md.renderer.rules.image = (tokens, idx, options, env, self) => {
    if (!showImages) {
      return "";
    }

    const token = tokens[idx];
    const srcIndex = token.attrIndex("src");

    if (srcIndex >= 0) {
      token.attrs[srcIndex][1] = resolveAssetUrl(token.attrs[srcIndex][1], assetBase);
    }

    return defaultImageRenderer(tokens, idx, options, env, self);
  };

  const defaultLinkOpenRenderer =
    md.renderer.rules.link_open ||
    ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options));

  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx];
    const hrefIndex = token.attrIndex("href");

    if (hrefIndex >= 0) {
      const currentHref = token.attrs[hrefIndex][1];
      token.attrs[hrefIndex][1] = resolveAssetUrl(currentHref, assetBase);
    }

    token.attrSet("target", "_blank");
    token.attrSet("rel", "noreferrer");

    return defaultLinkOpenRenderer(tokens, idx, options, env, self);
  };

  return md;
}

export function renderMarkdownHtml(markdown, options = {}) {
  const source = String(markdown ?? "").trim();

  if (!source) {
    return "";
  }

  const { markdown: normalizedSource, formulas } = preserveFormulaBlocks(source);
  const renderer = createMarkdownRenderer(options);
  return injectFormulaBlocks(renderer.render(normalizedSource), formulas);
}

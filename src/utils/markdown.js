import MarkdownIt from "markdown-it";

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

  const renderer = createMarkdownRenderer(options);
  return renderer.render(source);
}

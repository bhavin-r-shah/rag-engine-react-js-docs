import { createHash } from 'node:crypto';
import { toMarkdown } from 'mdast-util-to-markdown';
import { mdxToMarkdown } from 'mdast-util-mdx';

const PRESENTATION_ONLY = new Set(['InlineToc']);

function plainText(node) {
  if (typeof node.value === 'string') return node.value;
  if (node.type === 'image') return node.alt ?? '';
  return (node.children ?? []).map(plainText).join('');
}

function sanitizeChildren(children = []) {
  return children.flatMap((child) => {
    const sanitized = sanitize(child);
    if (!sanitized) return [];
    return sanitized.type === 'root' ? sanitized.children : [sanitized];
  });
}

function sanitize(node) {
  if (node.type === 'yaml') return null;
  if ((node.type === 'mdxJsxFlowElement' || node.type === 'mdxJsxTextElement') && PRESENTATION_ONLY.has(node.name)) {
    return null;
  }
  if (node.type === 'mdxjsEsm') return null;
  if (node.type === 'mdxJsxFlowElement' || node.type === 'mdxJsxTextElement') {
    const children = sanitizeChildren(node.children);
    if (children.length === 0) return null;
    return node.type === 'mdxJsxTextElement'
      ? { type: 'text', value: children.map(plainText).join('') }
      : { type: 'root', children };
  }
  const copy = { ...node };
  if (node.children) copy.children = sanitizeChildren(node.children);
  return copy;
}

function headingTitle(tree) {
  const heading = tree.children.find((node) => node.type === 'heading' && node.depth === 1);
  return heading ? plainText(heading).replace(/\s*\{\/\*.*?\*\/\}\s*$/, '').trim() : null;
}

function fallbackTitle(document) {
  const segment = document.route.split('/').filter(Boolean).at(-1);
  return segment ? decodeURIComponent(segment) : 'React';
}

export function normalizeDocument(parsed) {
  const sanitizedTree = sanitize(parsed.tree) ?? { type: 'root', children: [] };
  const displayMarkdown = toMarkdown(sanitizedTree, { extensions: [mdxToMarkdown()] })
    .replace(/\s+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  const title = parsed.frontmatter.title ?? parsed.frontmatter.meta ?? headingTitle(parsed.tree) ?? fallbackTitle(parsed);
  const retrievalBody = plainText(sanitizedTree)
    .replace(/\{\/\*.*?\*\/\}/g, '')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  const retrievalText = [`Title: ${title}`, `Route: ${parsed.route}`, retrievalBody].filter(Boolean).join('\n\n');

  return {
    sourcePath: parsed.sourcePath,
    sourceUrl: parsed.sourceUrl,
    route: parsed.route,
    docType: parsed.docType,
    sourceHash: parsed.sourceHash,
    title,
    frontmatter: parsed.frontmatter,
    warnings: parsed.warnings,
    retrievalText,
    displayMarkdown,
    contentHash: createHash('sha256').update(retrievalText).digest('hex')
  };
}

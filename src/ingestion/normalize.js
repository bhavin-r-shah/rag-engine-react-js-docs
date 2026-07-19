import { createHash } from 'node:crypto';

function cleanMarkdownText(value) {
  return value
    .replace(/\{\/\*.*?\*\/\}/g, '')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/<\/?[A-Za-z][^>]*>/g, ' ')
    .replace(/^\s{0,3}(?:[-*+] |\d+[.)] |>\s?)/gm, '')
    .replace(/[*_~]+/g, '')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function headingTitle(tree) {
  const heading = tree.children.find((node) => node.type === 'heading' && node.depth === 1);
  return heading ? cleanMarkdownText(heading.value) : null;
}

function fallbackTitle(document) {
  const segment = document.route.split('/').filter(Boolean).at(-1);
  return segment ? decodeURIComponent(segment) : 'React';
}

function renderDisplayNode(node) {
  if (node.type === 'mdxWrapper') return '';
  return node.raw.replace(/\{\/\*.*?\*\/\}/g, '').trimEnd();
}

function retrievalNode(node) {
  if (node.type === 'mdxWrapper') return '';
  if (node.type === 'code') return node.value.trim();
  return cleanMarkdownText(node.value);
}

export function normalizeDocument(parsed) {
  const displayMarkdown = parsed.tree.children
    .map(renderDisplayNode)
    .filter(Boolean)
    .join('\n\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  const title = parsed.frontmatter.title ?? parsed.frontmatter.meta ?? headingTitle(parsed.tree) ?? fallbackTitle(parsed);
  const retrievalBody = parsed.tree.children
    .map(retrievalNode)
    .filter(Boolean)
    .join('\n\n')
    .trim();
  const warnings = [...parsed.warnings];
  if (!retrievalBody) warnings.push('Document contains no searchable body content.');
  const retrievalText = [`Title: ${title}`, `Route: ${parsed.route}`, retrievalBody].filter(Boolean).join('\n\n');

  return {
    sourcePath: parsed.sourcePath,
    sourceUrl: parsed.sourceUrl,
    route: parsed.route,
    docType: parsed.docType,
    sourceHash: parsed.sourceHash,
    title,
    frontmatter: parsed.frontmatter,
    warnings,
    retrievalText,
    displayMarkdown,
    contentHash: createHash('sha256').update(retrievalText).digest('hex')
  };
}

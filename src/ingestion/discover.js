import { createHash } from 'node:crypto';
import { readdir, readFile, realpath, stat } from 'node:fs/promises';
import path from 'node:path';

const SUPPORTED_EXTENSIONS = new Set(['.md', '.mdx']);

export function routeFromRelativePath(relativePath) {
  const extension = path.extname(relativePath);
  const flattened = relativePath.slice(0, -extension.length);
  const segments = flattened.split('--').filter(Boolean);

  if (segments.at(-1) === 'index') segments.pop();
  return `/${segments.map(encodeURIComponent).join('/')}` || '/';
}

export function classifyRoute(route) {
  return route.split('/').filter(Boolean)[0] ?? 'home';
}

export function canonicalUrl(route, baseUrl = 'https://react.dev') {
  return new URL(route, baseUrl).toString().replace(/\/$/, route === '/' ? '/' : '');
}

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) files.push(...await walk(entryPath));
    if (entry.isFile() && SUPPORTED_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      files.push(entryPath);
    }
  }
  return files;
}

export async function discoverDocuments(corpusDirectory, options = {}) {
  const root = await realpath(corpusDirectory);
  if (!(await stat(root)).isDirectory()) throw new Error(`Corpus is not a directory: ${root}`);

  const documents = [];
  const seenRoutes = new Map();
  for (const sourcePath of await walk(root)) {
    const resolvedPath = await realpath(sourcePath);
    if (resolvedPath !== root && !resolvedPath.startsWith(`${root}${path.sep}`)) {
      throw new Error(`Source escapes corpus root: ${sourcePath}`);
    }

    const relativePath = path.relative(root, resolvedPath).split(path.sep).join('/');
    const route = routeFromRelativePath(relativePath);
    if (seenRoutes.has(route)) {
      throw new Error(`Duplicate canonical route ${route}: ${seenRoutes.get(route)} and ${relativePath}`);
    }
    seenRoutes.set(route, relativePath);
    const rawMarkdown = await readFile(resolvedPath, 'utf8');
    documents.push({
      sourcePath: relativePath,
      route,
      docType: classifyRoute(route),
      sourceUrl: canonicalUrl(route, options.baseUrl),
      sourceHash: createHash('sha256').update(rawMarkdown).digest('hex'),
      rawMarkdown
    });
  }
  return documents;
}

import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { discoverDocuments, routeFromRelativePath } from '../src/ingestion/discover.js';
import { parseDocument } from '../src/ingestion/parse.js';
import { normalizeDocument } from '../src/ingestion/normalize.js';

test('converts flattened source names into React routes', () => {
  assert.equal(routeFromRelativePath('reference--react--useEffect.md'), '/reference/react/useEffect');
  assert.equal(routeFromRelativePath('learn--index.mdx'), '/learn');
  assert.equal(routeFromRelativePath('index.md'), '/');
});

test('discovers supported documents in stable order', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'react-rag-'));
  await mkdir(path.join(root, 'nested'));
  await writeFile(path.join(root, 'learn--b.md'), '# B');
  await writeFile(path.join(root, 'learn--a.mdx'), '# A');
  await writeFile(path.join(root, 'ignored.txt'), 'ignore');
  await writeFile(path.join(root, 'nested', 'reference--react--use.md'), '# use');

  const documents = await discoverDocuments(root);
  assert.deepEqual(documents.map((document) => document.sourcePath), [
    'learn--a.mdx',
    'learn--b.md',
    'nested/reference--react--use.md'
  ]);
  assert.equal(documents[0].docType, 'learn');
  assert.equal(documents[0].sourceUrl, 'https://react.dev/learn/a');
});

test('parses and normalizes front matter, MDX wrappers, and code safely', () => {
  const rawMarkdown = `---\nmeta: "useWidget"\n---\n\n<Intro>\n\nUse the \`useWidget\` Hook.\n\n</Intro>\n\n<InlineToc />\n\n## Usage {/*usage*/}\n\n\`\`\`js src/App.js active\nuseWidget();\n\`\`\`\n`;
  const parsed = parseDocument({
    sourcePath: 'reference--react--useWidget.md',
    sourceUrl: 'https://react.dev/reference/react/useWidget',
    route: '/reference/react/useWidget',
    docType: 'reference',
    sourceHash: 'source',
    rawMarkdown
  });
  const normalized = normalizeDocument(parsed);

  assert.equal(normalized.title, 'useWidget');
  assert.match(normalized.retrievalText, /Use the useWidget Hook/);
  assert.match(normalized.displayMarkdown, /```js src\/App\.js active/);
  assert.doesNotMatch(normalized.displayMarkdown, /InlineToc|<Intro>/);
  assert.doesNotMatch(normalized.retrievalText, /meta:/);
  assert.equal(normalized.contentHash.length, 64);
});

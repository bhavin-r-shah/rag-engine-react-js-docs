#!/usr/bin/env node
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { ingestDocuments } from './ingestion/index.js';

const corpusDirectory = path.resolve(process.argv[2] ?? 'react-js-docs');
const outputPath = path.resolve(process.argv[3] ?? 'output/normalized-documents.json');

try {
  const documents = await ingestDocuments(corpusDirectory);
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify({ generatedAt: new Date().toISOString(), documents }, null, 2)}\n`);
  const warningCount = documents.reduce((count, document) => count + document.warnings.length, 0);
  console.log(`Normalized ${documents.length} documents to ${outputPath} (${warningCount} warnings).`);
} catch (error) {
  console.error(`Ingestion failed: ${error.message}`);
  process.exitCode = 1;
}

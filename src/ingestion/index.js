import { discoverDocuments } from './discover.js';
import { parseDocument } from './parse.js';
import { normalizeDocument } from './normalize.js';

export async function ingestDocuments(corpusDirectory, options = {}) {
  const discovered = await discoverDocuments(corpusDirectory, options);
  return discovered.map(parseDocument).map(normalizeDocument);
}

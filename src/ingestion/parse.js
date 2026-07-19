function parseScalar(value) {
  const trimmed = value.trim();
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1).replace(/\\([\\"'])/g, '$1');
  }
  if (trimmed === 'true') return true;
  if (trimmed === 'false') return false;
  if (trimmed === 'null' || trimmed === '~') return null;
  if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) return Number(trimmed);
  return trimmed;
}

function parseFrontmatter(lines, warnings) {
  if (lines[0]?.trim() !== '---') return { frontmatter: {}, bodyStart: 0 };
  const closingIndex = lines.slice(1).findIndex((line) => line.trim() === '---');
  if (closingIndex < 0) {
    warnings.push('YAML front matter is missing its closing delimiter.');
    return { frontmatter: {}, bodyStart: 0 };
  }

  const frontmatter = {};
  for (const line of lines.slice(1, closingIndex + 1)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    const match = /^([A-Za-z][\w-]*):\s*(.*)$/.exec(line);
    if (!match) {
      warnings.push(`Unsupported YAML front matter line: ${line}`);
      continue;
    }
    frontmatter[match[1]] = parseScalar(match[2]);
  }
  return { frontmatter, bodyStart: closingIndex + 2 };
}

function parseBlocks(lines, bodyStart, warnings) {
  const children = [];
  let index = bodyStart;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = /^(\s*)(`{3,}|~{3,})(.*)$/.exec(line);
    if (fence) {
      const marker = fence[2][0];
      const minimumLength = fence[2].length;
      const info = fence[3].trim();
      const [lang = '', ...metaParts] = info.split(/\s+/).filter(Boolean);
      const content = [];
      const raw = [line];
      index += 1;
      while (index < lines.length && !new RegExp(`^\\s*${marker}{${minimumLength},}\\s*$`).test(lines[index])) {
        content.push(lines[index]);
        raw.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) raw.push(lines[index++]);
      else warnings.push(`Unclosed code fence beginning with: ${line.trim()}`);
      children.push({ type: 'code', lang, meta: metaParts.join(' '), value: content.join('\n'), raw: raw.join('\n') });
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      children.push({ type: 'heading', depth: heading[1].length, value: heading[2], raw: line });
      index += 1;
      continue;
    }

    if (/^\s*<\/?[A-Z][\w.]*(?:\s[^>]*)?\/?>(?:\s*)$/.test(line)) {
      children.push({ type: 'mdxWrapper', value: line.trim(), raw: line });
      index += 1;
      continue;
    }

    const paragraph = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() &&
      !/^(\s*)(`{3,}|~{3,})/.test(lines[index]) &&
      !/^#{1,6}\s+/.test(lines[index]) &&
      !/^\s*<\/?[A-Z][\w.]*(?:\s[^>]*)?\/?>(?:\s*)$/.test(lines[index])) {
      paragraph.push(lines[index++]);
    }
    children.push({ type: 'textBlock', value: paragraph.join('\n'), raw: paragraph.join('\n') });
  }
  return { type: 'root', children };
}

export function parseDocument(document) {
  const warnings = [];
  const lines = document.rawMarkdown.replace(/\r\n?/g, '\n').split('\n');
  const { frontmatter, bodyStart } = parseFrontmatter(lines, warnings);
  const tree = parseBlocks(lines, bodyStart, warnings);
  return { ...document, frontmatter, tree, warnings };
}

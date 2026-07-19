import yaml from 'js-yaml';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkMdx from 'remark-mdx';
import remarkFrontmatter from 'remark-frontmatter';

const parser = unified().use(remarkParse).use(remarkMdx).use(remarkFrontmatter, ['yaml']);

function visit(node, callback, ancestors = []) {
  callback(node, ancestors);
  for (const child of node.children ?? []) visit(child, callback, [...ancestors, node]);
}

export function parseDocument(document) {
  const tree = parser.parse(document.rawMarkdown);
  const warnings = [];
  let frontmatter = {};

  const yamlNode = tree.children.find((node) => node.type === 'yaml');
  if (yamlNode) {
    try {
      frontmatter = yaml.load(yamlNode.value) ?? {};
      if (typeof frontmatter !== 'object' || Array.isArray(frontmatter)) {
        warnings.push('Front matter must be a mapping; it was ignored.');
        frontmatter = {};
      }
    } catch (error) {
      warnings.push(`Invalid YAML front matter: ${error.message}`);
    }
  }

  visit(tree, (node) => {
    if (node.type === 'html') warnings.push('Raw HTML was preserved as text and was never executed.');
  });

  return { ...document, frontmatter, tree, warnings };
}

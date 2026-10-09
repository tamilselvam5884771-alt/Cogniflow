import React from 'react';

/**
 * Parse inline formatting: **bold**, *italic*, `code`
 */
function parseInline(text) {
  if (!text) return null;

  // Tokenize bold, italic, code
  const tokens = [];
  let remaining = text;
  let key = 0;

  // Regex matches: **bold**, *italic*, `code`
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push(text.substring(lastIndex, match.index));
    }

    const matchedStr = match[0];
    if (matchedStr.startsWith('**') && matchedStr.endsWith('**')) {
      tokens.push(
        <strong key={`bold-${key++}`} className="font-semibold text-gray-100">
          {matchedStr.slice(2, -2)}
        </strong>
      );
    } else if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
      tokens.push(
        <code key={`code-${key++}`} className="inline-code">
          {matchedStr.slice(1, -1)}
        </code>
      );
    } else if (matchedStr.startsWith('*') && matchedStr.endsWith('*')) {
      tokens.push(
        <em key={`em-${key++}`} className="italic text-gray-300">
          {matchedStr.slice(1, -1)}
        </em>
      );
    }

    lastIndex = match.index + matchedStr.length;
  }

  if (lastIndex < text.length) {
    tokens.push(text.substring(lastIndex));
  }

  return tokens.length > 0 ? tokens : text;
}

/**
 * Format markdown string into React elements cleanly
 */
export function FormattedMessage({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let currentList = null;
  let currentListType = null; // 'ul' | 'ol'
  let key = 0;

  const flushList = () => {
    if (currentList) {
      if (currentListType === 'ol') {
        elements.push(
          <ol key={`ol-${key++}`} className="markdown-ol">
            {currentList}
          </ol>
        );
      } else {
        elements.push(
          <ul key={`ul-${key++}`} className="markdown-ul">
            {currentList}
          </ul>
        );
      }
      currentList = null;
      currentListType = null;
    }
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim();

    if (!line) {
      flushList();
      return;
    }

    // Check headings
    if (line.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`h4-${key++}`} className="markdown-h4">
          {parseInline(line.slice(4))}
        </h4>
      );
    } else if (line.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${key++}`} className="markdown-h3">
          {parseInline(line.slice(3))}
        </h3>
      );
    } else if (line.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`h2-${key++}`} className="markdown-h2">
          {parseInline(line.slice(2))}
        </h2>
      );
    }
    // Check unordered list item
    else if (line.startsWith('* ') || line.startsWith('- ') || line.startsWith('• ')) {
      if (currentListType !== 'ul') {
        flushList();
        currentListType = 'ul';
        currentList = [];
      }
      const itemText = line.replace(/^(\*|-|•)\s+/, '');
      currentList.push(
        <li key={`li-${index}`} className="markdown-li">
          {parseInline(itemText)}
        </li>
      );
    }
    // Check ordered list item (e.g. 1. )
    else if (/^\d+\.\s+/.test(line)) {
      if (currentListType !== 'ol') {
        flushList();
        currentListType = 'ol';
        currentList = [];
      }
      const itemText = line.replace(/^\d+\.\s+/, '');
      currentList.push(
        <li key={`oli-${index}`} className="markdown-li">
          {parseInline(itemText)}
        </li>
      );
    }
    // Regular paragraph
    else {
      flushList();
      elements.push(
        <p key={`p-${key++}`} className="markdown-p">
          {parseInline(line)}
        </p>
      );
    }
  });

  flushList();

  return <div className="formatted-markdown">{elements}</div>;
}

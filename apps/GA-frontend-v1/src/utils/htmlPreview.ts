export function getHtmlPreviewContent(content: string, type: 'html' | 'svg' | 'json' = 'html'): string {
  const scrollbarStyle = `
  /* Custom Scrollbar */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    background-color: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
    transition: background-color 0.2s ease;
  }
  ::-webkit-scrollbar-thumb:hover {
    background-color: rgba(0, 0, 0, 0.35);
  }
  ::-webkit-scrollbar-corner {
    background-color: transparent;
  }
  html {
    height: 100%;
    overflow: hidden;
  }
  body {
    height: 100%;
    overflow-y: overlay;
    box-sizing: border-box;
  }`;

  const preventLinkNavigationScript = `
  <script>
    document.addEventListener('click', function(e) {
      const link = e.target.closest('a');
      if (link) {
        const href = link.getAttribute('href');
        
        // Handle anchor links (internal navigation) manually
        if (href && href.startsWith('#')) {
          e.preventDefault();
          
          if (href === '#') return;
          
          const targetId = href.substring(1);
          const targetElement = document.getElementById(targetId) || document.getElementsByName(targetId)[0];
          if (targetElement) {
            // Use window.scrollTo instead of scrollIntoView to prevent parent window scrolling
          // Calculate absolute position relative to the document
          // Note: Our injected CSS makes body the scroll container (html is overflow: hidden)
          const scrollContainer = document.body;
          const elementPosition = targetElement.getBoundingClientRect().top;
          const offsetPosition = elementPosition + scrollContainer.scrollTop;
          
          scrollContainer.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
          });
          }
          return;
        }
        
        // Prevent empty links and javascript: links
        if (!href || href.startsWith('javascript:')) {
          e.preventDefault();
          return;
        }
        
        // Force external links to open in new tab
        if (href && !href.startsWith('#')) {
           link.target = '_blank';
        }
      }
    });
  </script>`;

  if (type === 'html') {
    let trimmed = content.trim();
    
    trimmed = trimmed.replace(/<script[^>]*src=["']\/@vite\/client["'][^>]*><\/script>/gi, '');
    trimmed = trimmed.replace(/<script[^>]*src=["']\/src\/main\.ts.*["'][^>]*><\/script>/gi, '');
    trimmed = trimmed.replace(/<script[^>]*type=["']module["'][^>]*>[\s\S]*?<\/script>/gi, '');
    
    // If it's a full document, inject scrollbar style and script
    if (trimmed.toLowerCase().startsWith('<!doctype html') || trimmed.toLowerCase().startsWith('<html')) {
      let modifiedContent = trimmed;
      
      // Inject CSS
      const lowerContent = modifiedContent.toLowerCase();
      const headIndex = lowerContent.lastIndexOf('</head>');
      if (headIndex !== -1) {
        modifiedContent = modifiedContent.substring(0, headIndex) + 
                          `<style>${scrollbarStyle}</style></head>` + 
                          modifiedContent.substring(headIndex + 7);
      }
      
      // Inject Script
      // Re-calculate lowerContent because modifiedContent changed
      const lowerContent2 = modifiedContent.toLowerCase();
      const bodyIndex = lowerContent2.lastIndexOf('</body>');
      
      if (bodyIndex !== -1) {
        modifiedContent = modifiedContent.substring(0, bodyIndex) + 
                          `${preventLinkNavigationScript}</body>` + 
                          modifiedContent.substring(bodyIndex + 7);
      } else {
        // Fallback if no body tag
        modifiedContent += preventLinkNavigationScript;
      }
      
      return modifiedContent;
    }
    // Wrap fragment in a default template
    return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base target="_blank">
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 24px;
    color: #333;
    line-height: 1.6;
    background-color: #fff;
  }
  img { max-width: 100%; height: auto; border-radius: 4px; }
  pre { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
  code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 0.9em; background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }
  blockquote { border-left: 4px solid #e2e8f0; margin: 0; padding-left: 16px; color: #64748b; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #e2e8f0; padding: 8px; text-align: left; }
  th { background-color: #f8fafc; }
${scrollbarStyle}
</style>
</head>
<body>
${trimmed}
${preventLinkNavigationScript}
</body>
</html>`;
  }
  
  // SVG Handling - wrap in HTML to center/scale if needed, or just return as is
  // For now, returning content as is is usually fine for iframe srcdoc if it's a valid SVG
  if (type === 'svg') {
    return content;
  }

  // JSON Handling - generate a beautiful syntax-highlighted JSON viewer
  if (type === 'json') {
    return getJsonPreviewContent(content);
  }

  return content;
}

/**
 * Generate a formatted, syntax-highlighted JSON viewer HTML page
 */
function getJsonPreviewContent(jsonString: string): string {
  let parsed: any;
  let isValidJson = true;
  let formattedJson = '';

  try {
    parsed = JSON.parse(jsonString);
    formattedJson = JSON.stringify(parsed, null, 2);
  } catch {
    isValidJson = false;
    formattedJson = jsonString;
  }

  const escapedJson = formattedJson
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --key-color: #d63384;
    --string-color: #198754;
    --number-color: #0d6efd;
    --boolean-color: #6f42c1;
    --null-color: #6c757d;
    --brace-color: #495057;
    --bg-color: #f8f9fa;
    --line-hover-bg: rgba(13, 110, 253, 0.06);
    --gutter-color: #adb5bd;
    --error-color: #dc3545;
    --text-color: #212529;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', 'Liberation Mono', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-color);
    background: #fff;
    padding: 16px 0;
    overflow-y: auto;
    height: 100%;
  }

  .line {
    display: flex;
    padding: 0 16px;
    min-height: 21px;
    align-items: flex-start;
  }

  .line:hover {
    background: var(--line-hover-bg);
  }

  .line-number {
    flex-shrink: 0;
    width: 44px;
    text-align: right;
    padding-right: 12px;
    color: var(--gutter-color);
    user-select: none;
    font-size: 12px;
    line-height: 1.6;
  }

  .line-content {
    white-space: pre-wrap;
    word-break: break-all;
    flex: 1;
    min-width: 0;
  }

  .error-box {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 16px;
    padding: 12px 16px;
    background: #fff3f3;
    border: 1px solid #fecaca;
    border-radius: 8px;
    color: var(--error-color);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
  }

  .error-icon {
    flex-shrink: 0;
    margin-top: 1px;
  }

  .error-content-title {
    font-weight: 600;
    margin-bottom: 4px;
  }

  .invalid-json {
    color: var(--text-color);
  }

  .invalid-json .line-content {
    cursor: default;
  }

  .toggle {
    display: inline-block;
    width: 12px;
    cursor: pointer;
    user-select: none;
    color: var(--brace-color);
    transition: transform 0.15s ease;
    margin-right: 2px;
  }

  .toggle.collapsed {
    transform: rotate(-90deg);
  }

  .toggle.empty {
    visibility: hidden;
  }

  .collapsed-hidden {
    display: none;
  }

  .key { color: var(--key-color); }
  .string { color: var(--string-color); }
  .number { color: var(--number-color); }
  .boolean { color: var(--boolean-color); }
  .null { color: var(--null-color); }
  .brace { color: var(--brace-color); }

  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background-color: transparent; }
  ::-webkit-scrollbar-thumb { background-color: rgba(0,0,0,0.15); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background-color: rgba(0,0,0,0.3); }
</style>
</head>
<body>
${isValidJson ? renderJsonHtml(parsed) : renderInvalidJsonHtml(escapedJson)}
<script>
  document.addEventListener('click', function(e) {
    const toggle = e.target.closest('.toggle');
    if (!toggle) return;
    const line = toggle.closest('.line');
    if (!line) return;
    let depth = parseInt(line.dataset.depth || '0');
    toggle.classList.toggle('collapsed');
    const isCollapsed = toggle.classList.contains('collapsed');
    let next = line.nextElementSibling;
    while (next) {
      const nextDepth = parseInt(next.dataset.depth || '0');
      if (nextDepth <= depth) break;
      if (isCollapsed) {
        next.classList.add('collapsed-hidden');
      } else {
        next.classList.remove('collapsed-hidden');
      }
      next = next.nextElementSibling;
    }
  });
<\/script>
</body>
</html>`;
}

function renderJsonHtml(obj: any, depth: number = 0): string {
  if (obj === null) return '<span class="null">null</span>';
  if (typeof obj === 'boolean') return '<span class="boolean">' + obj + '</span>';
  if (typeof obj === 'number') return '<span class="number">' + obj + '</span>';
  if (typeof obj === 'string') return '<span class="string">"</span><span class="string">' + escapeHtml(obj) + '</span><span class="string">"</span>';

  if (Array.isArray(obj)) {
    if (obj.length === 0) return '<span class="brace">[]</span>';
    let html = '<span class="brace">[</span>';
    const innerLines: string[] = [];
    for (let i = 0; i < obj.length; i++) {
      innerLines.push('<div class="line" data-depth="' + (depth + 1) + '"><span class="line-number"></span><span class="line-content">' + renderJsonHtml(obj[i], depth + 1) + (i < obj.length - 1 ? '<span class="brace">,</span>' : '') + '</span></div>');
    }
    const toggle = '<span class="toggle">▼</span>';
    return toggle + html + '\n' + innerLines.join('\n') + '\n<div class="line" data-depth="' + depth + '"><span class="line-number"></span><span class="line-content"><span class="brace">]</span></span></div>';
  }

  const keys = Object.keys(obj);
  if (keys.length === 0) return '<span class="brace">{}</span>';
  let html = '<span class="brace">{</span>';
  const innerLines: string[] = [];
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    innerLines.push('<div class="line" data-depth="' + (depth + 1) + '"><span class="line-number"></span><span class="line-content"><span class="key">"</span><span class="key">' + escapeHtml(k) + '</span><span class="key">"</span><span class="brace">: </span>' + renderJsonHtml(obj[k], depth + 1) + (i < keys.length - 1 ? '<span class="brace">,</span>' : '') + '</span></div>');
  }
  const toggle = '<span class="toggle">▼</span>';
  return toggle + html + '\n' + innerLines.join('\n') + '\n<div class="line" data-depth="' + depth + '"><span class="line-number"></span><span class="line-content"><span class="brace">}</span></span></div>';
}

function renderInvalidJsonHtml(escapedJson: string): string {
  const lines = escapedJson.split('\n');
  return '<div class="error-box">' +
    '<svg class="error-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc3545" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>' +
    '<div><div class="error-content-title">JSON 解析失败</div><div>以下内容不是有效的 JSON，已显示原始文本：</div></div>' +
    '</div>\n' +
    '<div class="invalid-json">' +
    lines.map((line, i) => '<div class="line"><span class="line-number">' + (i + 1) + '</span><span class="line-content">' + (line || '&nbsp;') + '</span></div>').join('\n') +
    '</div>';
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Group only adjacent images; prose, captions, links and code keep their order.
export function stackMarkdownImages(html: string): string {
  const template = document.createElement('template');
  template.innerHTML = html;
  if (template.content.querySelectorAll('img').length < 2) return html;

  // Markdown can put a heading and the first image in the same paragraph.
  // Split those paragraphs so adjacent images still form one gallery.
  template.content.querySelectorAll('p').forEach(paragraph => {
    if (!Array.from(paragraph.children).some(child => child.tagName === 'IMG')) return;
    const fragment = document.createDocumentFragment();
    let text = paragraph.cloneNode(false) as HTMLParagraphElement;
    const flushText = () => {
      if (text.textContent?.trim() || Array.from(text.children).some(child => child.tagName !== 'BR')) fragment.append(text);
      text = paragraph.cloneNode(false) as HTMLParagraphElement;
    };
    Array.from(paragraph.childNodes).forEach(child => {
      if (child instanceof HTMLImageElement) {
        flushText();
        fragment.append(child);
      } else text.append(child);
    });
    flushText();
    paragraph.replaceWith(fragment);
  });

  function isGap(node: Node): boolean {
    return (node.nodeType === Node.TEXT_NODE && !node.textContent?.trim()) ||
      (node instanceof Element && node.tagName === 'BR');
  }

  function imagesIn(node: Node): HTMLImageElement[] | null {
    if (node instanceof HTMLImageElement) return [node];
    if (!(node instanceof Element) || node.tagName !== 'P') return null;
    const children = Array.from(node.childNodes);
    if (!children.every(child => child instanceof HTMLImageElement || isGap(child))) return null;
    const images = children.filter((child): child is HTMLImageElement => child instanceof HTMLImageElement);
    return images.length ? images : null;
  }

  function visit(parent: ParentNode) {
    let run: Node[] = [];
    let images: HTMLImageElement[] = [];
    function flush() {
      if (images.length > 1) {
        const stack = document.createElement('div');
        stack.className = 'image-gallery-slot';
        stack.dataset.images = JSON.stringify(images.map(image => ({
          url: image.getAttribute('src') || '', name: image.alt || '图片'
        })));
        run[0].parentNode!.insertBefore(stack, run[0]);
        run.forEach(node => node.parentNode === stack.parentNode && node.parentNode?.removeChild(node));
      } else {
        run.forEach(node => {
          if (node instanceof Element && node.tagName === 'P') visit(node);
        });
      }
      run = [];
      images = [];
    }
    Array.from(parent.childNodes).forEach(node => {
      const found = imagesIn(node);
      if (found) {
        run.push(node);
        images.push(...found);
      } else if (isGap(node) && run.length) {
        run.push(node);
      } else {
        flush();
        if (node instanceof Element && ['P', 'DIV', 'BLOCKQUOTE', 'LI', 'UL', 'OL'].includes(node.tagName)) visit(node);
      }
    });
    flush();
  }
  visit(template.content);
  return template.innerHTML;
}


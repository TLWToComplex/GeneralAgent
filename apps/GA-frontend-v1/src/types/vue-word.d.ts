declare module '@vue-word/canvas-editor' {
  const Editor: new (...args: any[]) => any;
  export default Editor;
  export type IElement = any;
}

declare module '@vue-word/index.vue' {
  const Component: any;
  export default Component;
}

declare module '@vue-word/utils/docxImporter' {
  export function parseDocxToElements(file: File): Promise<any[]>;
}

declare module '@vue-word/utils/docxExporter' {
  export function exportDocxFile(elements: any[], fileName?: string): Promise<void>;
}

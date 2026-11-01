declare module 'markdown-it-katex' {
  import MarkdownIt from 'markdown-it';

  interface KatexOptions {
    throwOnError?: boolean;
    errorColor?: string;
    strict?: boolean | string;
    trust?: boolean;
    macros?: Record<string, string>;
    fleqn?: boolean;
    leqno?: boolean;
    minRuleThickness?: number;
    colorIsTextColor?: boolean;
    maxSize?: number;
    maxExpand?: number;
    globalGroup?: boolean;
  }

  function katex(md: MarkdownIt, options?: KatexOptions): void;
  export = katex;
}
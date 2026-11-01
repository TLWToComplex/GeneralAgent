declare module 'luckyexcel' {
  const LuckyExcel: {
    transformExcelToLucky(
      file: File,
      callback: (exportJson: any) => void
    ): void;
    transformExcelToLuckyByUrl(
      url: string,
      name: string,
      callback: (exportJson: any) => void
    ): void;
    default: any;
  };
  export default LuckyExcel;
}

declare module '@vue-excel/utils/export' {
  export function exportExcel(sheets: any[], filename: string): void;
}

declare module '@vue-excel/utils/is' {
  export function isFunction(value: unknown): value is (...args: any[]) => any;
}

declare module '@vue-excel/dist/plugins/js/plugin.js';

declare module '@vue-excel/dist/luckysheet.umd.js';

interface Window {
  luckysheet: {
    create: (config: any) => void;
    destroy: () => void;
    resize: () => void;
    getAllSheets: () => any[];
    [key: string]: any;
  };
}

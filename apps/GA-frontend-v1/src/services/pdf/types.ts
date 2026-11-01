/**
 * PDF导出相关的类型定义
 */

// 导出格式类型
export type ExportFormat = 'pdf' | 'text' | 'markdown'

// 导出质量类型
export type ExportQuality = 'normal' | 'high'

// 纸张尺寸类型
export type PaperSize = 'a3' | 'a4' | 'a5' | 'b4' | 'b5' | 'letter' | 'legal'

// 导出选项接口
export interface ExportOptions {
  format: ExportFormat
  includeThinking: boolean
  includeSystemMessages: boolean
  includeToolCalls?: boolean
  quality?: ExportQuality
  paperSize?: PaperSize
  scale?: number
  includeRoleLabels?: boolean
  simplifyContent?: boolean
  includeCodeblockSyntax?: boolean
  includeMetadata?: boolean
  includeTimestamp?: boolean
}

// PDF导出特定选项
export interface PdfExportOptions extends ExportOptions {
  format: 'pdf'
  quality: ExportQuality
  paperSize: PaperSize
  scale: number
  copyrightPosition: 'page-bottom' | 'last-page'
}

// 文本导出特定选项
export interface TextExportOptions extends ExportOptions {
  format: 'text'
  includeRoleLabels: boolean
  simplifyContent: boolean
}

// Markdown导出特定选项
export interface MarkdownExportOptions extends ExportOptions {
  format: 'markdown'
  includeCodeblockSyntax: boolean
  includeMetadata: boolean
}

// 导出进度信息
export interface ExportProgress {
  stage: string
  percent: number
}

// 预览配置
export interface PreviewConfig {
  paperSize: PaperSize
  scale: number
  includeThinking: boolean
  includeSystemMessages: boolean
  includeToolCalls?: boolean
  copyrightPosition: 'page-bottom' | 'last-page'
}

// 纸张尺寸配置
export interface PaperDimensions {
  width: number
  height: number
  aspectRatio: number
  label: string
}

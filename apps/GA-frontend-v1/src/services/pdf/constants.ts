import type { PaperDimensions } from './types'

/**
 * PDF导出相关常量
 */

// 纸张尺寸配置（单位：mm）
export const PAPER_SIZES: Record<string, PaperDimensions> = {
  a3: {
    width: 297,
    height: 420,
    aspectRatio: 420 / 297, // 高/宽比例
    label: 'A3 (297×420mm)'
  },
  a4: {
    width: 210,
    height: 297,
    aspectRatio: 297 / 210, // 高/宽比例
    label: 'A4 (210×297mm)'
  },
  a5: {
    width: 148,
    height: 210,
    aspectRatio: 210 / 148, // 高/宽比例
    label: 'A5 (148×210mm)'
  },
  b4: {
    width: 250,
    height: 353,
    aspectRatio: 353 / 250, // 高/宽比例
    label: 'B4 (250×353mm)'
  },
  b5: {
    width: 176,
    height: 250,
    aspectRatio: 250 / 176, // 高/宽比例
    label: 'B5 (176×250mm)'
  },
  letter: {
    width: 215.9,
    height: 279.4,
    aspectRatio: 279.4 / 215.9, // 高/宽比例
    label: 'Letter (215.9×279.4mm)'
  },
  legal: {
    width: 215.9,
    height: 355.6,
    aspectRatio: 355.6 / 215.9, // 高/宽比例
    label: 'Legal (215.9×355.6mm)'
  }
}

// 导出进度阶段
export const EXPORT_STAGES = {
  PREPARING: '准备导出...',
  GENERATING_CONTENT: '生成内容...',
  RENDERING_PAGE: '渲染页面...',
  PROCESSING_CONTENT: '处理内容...',
  PROCESSING_MARKDOWN: '处理Markdown内容...',
  COMPLETED: '导出完成',
  FAILED: '导出失败'
}

// 角色配置
export const ROLE_CONFIG = {
  user: {
    label: '用户',
    icon: '用',
    color: '#87d068'
  },
  assistant: {
    label: '助手',
    icon: '助',
    color: '#1890ff'
  },
  system: {
    label: '系统',
    icon: '系',
    color: '#fa8c16'
  },
  tool: {
    label: '工具',
    icon: '工',
    color: '#722ed1'
  }
}

// 导出容器样式配置
export const EXPORT_CONTAINER_CONFIG = {
  width: 760,
  padding: 38, // 行107: 从35改为38
  backgroundColor: '#f5f7fa',
  fontFamily: 'Arial, "Microsoft YaHei", sans-serif'
}

// 质量配置
export const QUALITY_CONFIG = {
  normal: {
    scale: 2.5,
    format: 'JPEG' as const,
    quality: 0.92,
    targetDpi: 144,
    imageCompression: 'FAST' as const
  },
  high: {
    scale: 4,
    format: 'PNG' as const,
    quality: 1,
    targetDpi: 200,
    imageCompression: 'MEDIUM' as const
  }
}

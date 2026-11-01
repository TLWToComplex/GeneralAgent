import type { IElement } from '@vue-word/canvas-editor';
import { parseDocxToElements } from '@vue-word/utils/docxImporter';
import { exportDocxFile } from '@vue-word/utils/docxExporter';

const DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

type DocxBinary = ArrayBuffer | ArrayBufferView;
type DocxSource = DocxBinary | string;
type EditorInstance = any;

const isArrayBufferView = (value: unknown): value is ArrayBufferView => ArrayBuffer.isView(value);

const toArrayBuffer = (value: DocxBinary): ArrayBuffer => {
  if (value instanceof ArrayBuffer) return value;
  return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength) as ArrayBuffer;
};

export const isUrlLikeDocxSource = (value: string) => /^https?:\/\//i.test(value) || value.startsWith('/');

export const normalizeDocxFileName = (value?: string, fallback = 'document.docx') => {
  if (!value) return fallback;
  const trimmed = value.trim();
  if (!trimmed) return fallback;
  const base = trimmed.split('?')[0].split('#')[0];
  const segment = base.split('/').filter(Boolean).pop() || trimmed;
  let decoded = segment;
  try {
    decoded = decodeURIComponent(segment);
  } catch {
    decoded = segment;
  }
  const clean = decoded.trim();
  if (!clean) return fallback;
  return clean.toLowerCase().endsWith('.docx') ? clean : `${clean}.docx`;
};

export const resolveDocxSourceBuffer = async (source: DocxSource): Promise<ArrayBuffer> => {
  if (source instanceof ArrayBuffer || isArrayBufferView(source)) {
    return toArrayBuffer(source);
  }
  const url = source.trim();
  if (!url) {
    throw new Error('文档链接为空');
  }
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`文档加载失败 (${response.status})`);
  }
  return await response.arrayBuffer();
};

export const importDocxIntoEditor = async (
  editor: EditorInstance,
  source: DocxSource,
  fileName = 'document.docx'
) => {
  const arrayBuffer = await resolveDocxSourceBuffer(source);
  const file = new File([arrayBuffer], normalizeDocxFileName(fileName), { type: DOCX_MIME });
  try {
    const elements = await parseDocxToElements(file);
    editor.command.executeSetValue({ main: elements });
  } catch (error) {
    const command = editor.command as {
      executeImportDocx?: (payload: { arrayBuffer: ArrayBuffer }) => void;
    };
    if (!command.executeImportDocx) {
      throw error;
    }
    command.executeImportDocx({ arrayBuffer });
  }
};

export const getEditorMainElements = (editor: EditorInstance): IElement[] => {
  const data = editor.command.getValue() as { data?: { main?: IElement[] }; main?: IElement[] };
  return data?.data?.main || data?.main || [];
};

export const exportEditorToDocx = async (editor: EditorInstance, fileName = 'document.docx') => {
  const elements = getEditorMainElements(editor);
  await exportDocxFile(elements, normalizeDocxFileName(fileName));
};

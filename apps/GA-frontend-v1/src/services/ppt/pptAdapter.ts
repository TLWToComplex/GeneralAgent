const PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';

type PptBinary = ArrayBuffer | ArrayBufferView;
export type PptSource = PptBinary | string;

const isArrayBufferView = (value: unknown): value is ArrayBufferView => ArrayBuffer.isView(value);

const toArrayBuffer = (value: PptBinary): ArrayBuffer => {
  if (value instanceof ArrayBuffer) return value;
  return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength) as ArrayBuffer;
};

export const isUrlLikePptSource = (value: string) => /^https?:\/\//i.test(value) || value.startsWith('/');

export const normalizePptFileName = (value?: string, fallback = 'presentation.pptx') => {
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
  return /\.(ppt|pptx)$/i.test(clean) ? clean : `${clean}.pptx`;
};

export const resolvePptSourceBuffer = async (source: PptSource): Promise<ArrayBuffer> => {
  if (source instanceof ArrayBuffer || isArrayBufferView(source)) {
    return toArrayBuffer(source);
  }

  const url = source.trim();
  if (!url) {
    throw new Error('演示文稿链接为空');
  }

  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });

  if (!response.ok) {
    throw new Error(`演示文稿加载失败 (${response.status})`);
  }

  return await response.arrayBuffer();
};

export const createPptFile = (source: PptBinary, fileName?: string) => {
  const arrayBuffer = toArrayBuffer(source);
  return new File([arrayBuffer], normalizePptFileName(fileName), { type: PPTX_MIME });
};

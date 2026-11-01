import WordSvg from '@/assets/image/svg/Word.svg';
import PdfSvg from '@/assets/image/svg/pdf-icon.svg';
import TxtSvg from '@/assets/image/svg/Txt.svg';
import MarkdownSvg from '@/assets/image/svg/Markdown.svg';
import ExcelSvg from '@/assets/image/svg/Excel.svg';
import PptSvg from '@/assets/image/svg/PPT.svg';
import ImageSvg from '@/assets/image/svg/image.svg';

export const getFileIconSrc = (filename: string) => {
  const name = (filename || '').toLowerCase().trim();

  if (name.endsWith('.pdf')) return PdfSvg;
  if (name.endsWith('.doc') || name.endsWith('.docx')) return WordSvg;
  if (name.endsWith('.txt')) return TxtSvg;
  if (name.endsWith('.md') || name.endsWith('.markdown')) return MarkdownSvg;
  if (name.endsWith('.ppt') || name.endsWith('.pptx')) return PptSvg;
  if (name.endsWith('.csv') || name.endsWith('.xls') || name.endsWith('.xlsx')) return ExcelSvg;
  if (name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.bmp')) return ImageSvg;

  return '';
};

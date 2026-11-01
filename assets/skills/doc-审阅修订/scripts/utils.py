"""
doc-审阅修订 通用工具函数

提供文件路径处理、日志输出、XML/颜色辅助等功能。
纯 Python，UTF-8 全链路原生。
v0.2.0 — 从 doc-格式化 分叉，集成 Track Changes 修订追踪。
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime
from lxml import etree

# ──────────────────────────────────────────────
# XML / OOXML 命名空间
# ──────────────────────────────────────────────

NSMAP = {
    'w':   'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r':   'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'mc':  'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wp':  'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a':   'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'v':   'urn:schemas-microsoft-com:vml',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
}

# 注册命名空间以支持 xpath 查询
for prefix, uri in NSMAP.items():
    try:
        etree.register_namespace(prefix, uri)
    except Exception:
        pass  # 某些版本 lxml 对重复注册宽容度不同


# ──────────────────────────────────────────────
# 文件路径处理
# ──────────────────────────────────────────────

def ensure_dir(path):
    """确保目录存在，不存在则创建。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_copy(src, dst):
    """安全复制文件——先复制到临时位置，确认完成后再替换。"""
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        raise FileNotFoundError(f"源文件不存在: {src}")

    tmp = dst.with_suffix('.tmp' + dst.suffix)
    shutil.copy2(src, tmp)
    tmp.replace(dst)
    return dst


def safe_write_docx(doc, filepath, strip_bold=True):
    """
    安全写入 docx 文件。
    先写临时文件，确认成功后再替换目标文件。

    Args:
        strip_bold: 写入前是否从文档 XML 中清除所有 w:b 加粗标记。
                    用于解决 python-docx 在保存时可能恢复 run.bold 的问题。
    """
    filepath = Path(filepath)
    tmp_path = filepath.with_suffix('.tmp.docx')

    # 确保目录存在
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # 写入前清除所有 w:b 标记（如果启用）
    if strip_bold:
        try:
            _strip_xml_bold(doc)
        except Exception:
            pass

    # 写入临时文件
    doc.save(str(tmp_path))

    # 验证临时文件有效
    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
        raise IOError(f"写入临时文件失败: {tmp_path}")

    # 替换目标文件
    tmp_path.replace(filepath)
    return filepath


def _strip_xml_bold(doc):
    """从文档所有段落的 XML run 中强制清除 w:b 元素。"""
    from docx.oxml.ns import qn
    # 遍历正文段落
    for para in doc.paragraphs:
        for r in para._p.findall(qn('w:r')):
            rPr = r.find(qn('w:rPr'))
            if rPr is not None:
                b = rPr.find(qn('w:b'))
                if b is not None:
                    rPr.remove(b)
    # 遍历页眉页脚
    for section in doc.sections:
        for header in section.header.paragraphs if section.header else []:
            for r in header._p.findall(qn('w:r')):
                rPr = r.find(qn('w:rPr'))
                if rPr is not None:
                    b = rPr.find(qn('w:b'))
                    if b is not None:
                        rPr.remove(b)
        for footer in section.footer.paragraphs if section.footer else []:
            for r in footer._p.findall(qn('w:r')):
                rPr = r.find(qn('w:rPr'))
                if rPr is not None:
                    b = rPr.find(qn('w:b'))
                    if b is not None:
                        rPr.remove(b)


def enable_track_revisions_in_doc(doc):
    """
    在保存前通过 python-docx 的 settings part 启用修订追踪。

    替代原来的 enable_track_revisions（事后 ZIP 操作），
    避免二次 ZIP 打包导致文档结构损坏/乱码。

    Word 需要 <w:trackRevisions/> 才会以"所有标记"模式显示修订。
    """
    W = NSMAP['w']

    try:
        settings_xml = doc.settings._element
    except Exception:
        log.warning("未找到 settings part，跳过修订追踪启用")
        return False

    # 添加 <w:trackRevisions/>
    if settings_xml.find(f'{{{W}}}trackRevisions') is None:
        etree.SubElement(settings_xml, f'{{{W}}}trackRevisions')
        log.info("已启用修订追踪 (<w:trackRevisions/>)")

    # 移除可能阻碍修订显示的 documentProtection
    prot = settings_xml.find(f'{{{W}}}documentProtection')
    if prot is not None:
        settings_xml.remove(prot)
        log.info("已移除 documentProtection（避免干扰修订显示）")

    return True


def enable_track_revisions(filepath):
    """
    （已废弃）后处理：在 docx 的 settings.xml 中启用修订追踪。

    请使用 enable_track_revisions_in_doc(doc) 替代，
    在 doc.save() 之前调用，避免二次 ZIP 打包导致的乱码问题。

    保留此函数用于向后兼容。
    """
    import zipfile
    import io

    filepath = Path(filepath)
    W = NSMAP['w']

    # 读取原始数据
    with open(filepath, 'rb') as f:
        raw = f.read()

    input_zip = zipfile.ZipFile(io.BytesIO(raw), 'r')
    output_buf = io.BytesIO()

    with zipfile.ZipFile(output_buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in input_zip.infolist():
            data = input_zip.read(item.filename)
            if item.filename == 'word/settings.xml':
                root = etree.fromstring(data)

                # 添加 <w:trackRevisions/>
                if root.find(f'{{{W}}}trackRevisions') is None:
                    etree.SubElement(root, f'{{{W}}}trackRevisions')
                    log.info("已启用修订追踪 (<w:trackRevisions/>)")

                # 移除可能阻碍修订显示的 documentProtection
                prot = root.find(f'{{{W}}}documentProtection')
                if prot is not None:
                    root.remove(prot)
                    log.info("已移除 documentProtection（避免干扰修订显示）")

                data = etree.tostring(root, xml_declaration=True,
                                      encoding='UTF-8', standalone=True)

            zout.writestr(item, data)

    input_zip.close()

    # 写回文件
    with open(filepath, 'wb') as f:
        f.write(output_buf.getvalue())

    return filepath


def backup_file(filepath):
    """为文件创建 .bak 备份，返回备份路径。"""
    p = Path(filepath)
    if not p.exists():
        return None
    bak = p.with_suffix(p.suffix + '.bak')
    shutil.copy2(p, bak)
    return bak


def resolve_path(path):
    """解析 ~ 和相对路径为绝对路径。"""
    return str(Path(os.path.expanduser(path)).resolve())


def validate_input_file(filepath):
    """验证输入文件是否存在且为 .docx。"""
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"输入文件不存在: {filepath}")
    if p.suffix.lower() != '.docx':
        raise ValueError(f"输入文件必须是 .docx 格式，当前: {p.suffix}")
    return p


# ──────────────────────────────────────────────
# 日志输出
# ──────────────────────────────────────────────

def setup_logger(name='docx-spec-formatter', level=logging.INFO):
    """配置统一日志格式。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)-7s %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


log = setup_logger()


# ──────────────────────────────────────────────
# 时间戳
# ──────────────────────────────────────────────

def now_str(fmt='%Y-%m-%d %H:%M:%S'):
    """当前时间字符串。"""
    return datetime.now().strftime(fmt)


def timestamp():
    """文件名安全的时间戳。"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


# ──────────────────────────────────────────────
# 版本信息
# ──────────────────────────────────────────────

VERSION = '0.2.4'

def print_banner():
    """打印工具横幅。"""
    return (
        f"╔══════════════════════════════════════════╗\n"
        f"║   doc-审阅修订 v{VERSION}                    ║\n"
        f"║   docx 文档审阅与修订工具                 ║\n"
        f"╚══════════════════════════════════════════╝"
    )

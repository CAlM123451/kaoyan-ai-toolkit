"""资料解析：支持 txt / pdf / docx 三种格式的文本提取。"""
import os


def parse_file(path: str) -> str:
    """按扩展名解析文件为纯文本。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    lower = path.lower()
    if lower.endswith(".txt"):
        return _parse_txt(path)
    if lower.endswith(".pdf"):
        return _parse_pdf(path)
    if lower.endswith(".docx"):
        return _parse_docx(path)
    raise ValueError(f"不支持的文件格式: {path}（支持 txt/pdf/docx）")


def _parse_txt(path: str) -> str:
    # utf-8-sig 优先：能正确处理带 BOM 的 UTF-8 文件
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法识别文件编码: {path}")


def _parse_pdf(path: str) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("解析 PDF 需要安装 pdfplumber: pip install pdfplumber")
    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    result = "\n".join(parts)
    if not result.strip():
        raise ValueError(f"PDF 文件无可提取文本（可能是扫描件）: {path}")
    return result


def _parse_docx(path: str) -> str:
    try:
        import docx
    except ImportError:
        raise RuntimeError("解析 docx 需要安装 python-docx: pip install python-docx")
    doc = docx.Document(path)
    parts = [p.text for p in doc.paragraphs if p.text]
    if not parts:
        # 尝试从表格中提取
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
    if not parts:
        raise ValueError(f"docx 文件无可提取文本: {path}")
    return "\n".join(parts)

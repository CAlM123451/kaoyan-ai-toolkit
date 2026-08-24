"""资料解析：支持 txt / pdf / docx 三种格式的文本提取。"""


def parse_file(path: str) -> str:
    """按扩展名解析文件为纯文本。"""
    lower = path.lower()
    if lower.endswith(".txt"):
        return _parse_txt(path)
    if lower.endswith(".pdf"):
        return _parse_pdf(path)
    if lower.endswith(".docx"):
        return _parse_docx(path)
    raise ValueError(f"不支持的文件格式: {path}（支持 txt/pdf/docx）")


def _parse_txt(path: str) -> str:
    for enc in ("utf-8", "gbk", "utf-8-sig"):
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
    return "\n".join(parts)


def _parse_docx(path: str) -> str:
    try:
        import docx
    except ImportError:
        raise RuntimeError("解析 docx 需要安装 python-docx: pip install python-docx")
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text)

"""测试时生成虚构 PDF，不把任何真实论文或 PDF 二进制放入仓库。"""
import json
from pathlib import Path
import zlib


def write_pdf(path, rotate=0, crop=False, caption=True, chinese=True, pages=2, dual_column=False):
    """仅用标准库写文字、矢量曲线和小型 RGB 位图；便于从安装副本验证。"""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [5 0 R] >>",
               b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /FontDescriptor << /Type /FontDescriptor /FontName /STSong-Light /Flags 6 /FontBBox [-25 -254 1000 880] /ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >> /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> >>"]
    bitmap = zlib.compress(bytes([0, 125, 180, 220, 125, 0, 220, 125, 0, 0, 125, 180]))
    objects.append(b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length " + str(len(bitmap)).encode() + b" >>\nstream\n" + bitmap + b"\nendstream")
    page_ids = []
    for index in range(pages):
        text = "图 2 虚构结果" if index == 1 and chinese else "Fig. %d Synthetic comparison" % (index + 1)
        caption_code = (b"BT /FC 12 Tf 45 260 Td <" + text.encode("utf-16-be").hex().encode() + b"> Tj ET\n" if text.startswith("图")
                        else b"BT /F1 12 Tf 45 260 Td (" + text.encode("ascii") + b") Tj ET\n") if caption else b""
        stream = (b"q 0.1 0.45 0.65 RG 2 w 45 300 300 140 re S 55 310 m 120 390 l 180 330 l 260 420 l 330 360 l S Q\n"
                  b"q 30 0 0 30 300 400 cm /Im1 Do Q\nBT /F1 10 Tf 45 470 Td (Synthetic figure fixture - no research evidence) Tj ET\n" + caption_code)
        stream += (b"BT /F1 9 Tf 24 350 Td (Y) Tj ET\n"
                   b"BT /F1 9 Tf 165 286 Td (Time axis) Tj ET\n"
                   b"BT /F1 9 Tf 280 445 Td (Legend) Tj ET\n")
        if dual_column:
            stream = (b"q 0.1 0.45 0.65 RG 2 w 25 300 145 140 re S 230 300 145 140 re S Q\n"
                      b"BT /F1 10 Tf 25 270 Td (Fig. 1 Left panel) Tj ET\n"
                      b"BT /F1 10 Tf 230 270 Td (Fig. 2 Right panel) Tj ET\n")
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        cropbox = b" /CropBox [20 30 380 480]" if crop else b""
        objects.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 500] /Rotate %d /Resources << /Font << /F1 3 0 R /FC 4 0 R >> /XObject << /Im1 6 0 R >> >> /Contents %d 0 R" % (rotate, content_id)).encode() + cropbox + b" >>")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream")
    objects[1] = b"<< /Type /Pages /Count " + str(pages).encode() + b" /Kids [" + b" ".join(("%d 0 R" % item).encode() for item in page_ids) + b"] >>"
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, item in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(("%d 0 obj\n" % number).encode() + item + b"\nendobj\n")
    xref = len(data)
    data.extend(("xref\n0 %d\n0000000000 65535 f \n" % len(offsets)).encode())
    for offset in offsets[1:]:
        data.extend(("%010d 00000 n \n" % offset).encode())
    data.extend(("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(offsets), xref)).encode())
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def make_demo(base):
    """返回 scope.json 路径；文件名故意含中文、空格、&、#、% 以检查链接。"""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    source = write_pdf(base / "虚构 source & # %.pdf")
    (base / "虚构 note & # %.md").write_text("# 虚构笔记\n仅为功能测试，不是真实科研记录。\n", encoding="utf-8")
    scope = base / "scope-input.json"
    scope.write_text(json.dumps({"schema_version": 1, "papers": [{"ledger_id": "DEMO-001", "title": "虚构文献：离线图库演示", "authors": ["示例作者"], "year": 2026, "tags": ["虚构", "测试"], "section": "方法", "pdf_path": source.name, "note_path": "虚构 note & # %.md"}]}, ensure_ascii=False, indent=2), encoding="utf-8")
    return scope

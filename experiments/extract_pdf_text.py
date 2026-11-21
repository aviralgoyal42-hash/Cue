"""Extract text from a simple PDF using only the standard library (no installs).
It inflates each content stream and applies the ToUnicode maps of the fonts.
Usage: python -I experiments/extract_pdf_text.py input.pdf output.txt
"""
import re
import sys
import zlib


def inflate(raw):
    try:
        return zlib.decompress(raw)
    except zlib.error:
        try:
            return zlib.decompressobj().decompress(raw)
        except zlib.error:
            return None


def objects(data):
    """Map object number -> (dictionary bytes, inflated stream or None)."""
    out = {}
    for m in re.finditer(rb"(\d+) 0 obj(.*?)endobj", data, re.S):
        body = m.group(2)
        s = re.search(rb"stream\r?\n", body)
        if s:
            raw = body[s.end():body.rfind(b"endstream")].rstrip(b"\r\n")
            out[int(m.group(1))] = (body[:s.start()], inflate(raw) if b"FlateDecode" in body[:s.start()] else raw)
        else:
            out[int(m.group(1))] = (body, None)
    return out


def cmap(stream):
    table = {}
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", stream, re.S):
        for a, b in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            table[int(a, 16)] = bytes.fromhex(b.decode()).decode("utf-16-be", "replace")
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", stream, re.S):
        for a, b, c in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            for i, code in enumerate(range(int(a, 16), int(b, 16) + 1)):
                table[code] = chr(int(c, 16) + i)
    return table


def main():
    data = open(sys.argv[1], "rb").read()
    objs = objects(data)
    fonts = {}      # font object number -> cmap
    for num, (d, _) in objs.items():
        t = re.search(rb"/ToUnicode (\d+) 0 R", d)
        if t and int(t.group(1)) in objs and objs[int(t.group(1))][1]:
            fonts[num] = cmap(objs[int(t.group(1))][1])
    names = {}      # /F1 -> font object number (taken from any resource dictionary)
    for d, _ in objs.values():
        for name, num in re.findall(rb"/(\w+) (\d+) 0 R", d):
            if int(num) in fonts:
                names[name] = int(num)
    lines = []
    for num, (d, s) in sorted(objs.items()):
        if not s or b"BT" not in s or b"ET" not in s:
            continue
        lines.append(f"\n===== stream {num} =====")
        current = {}
        y_last = None
        row = ""
        for tok in re.finditer(rb"/(\w+) [\d.]+ Tf|([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) Tm"
                               rb"|([-\d.]+) ([-\d.]+) T[dD]|\[(.*?)\]\s*TJ|<([0-9A-Fa-f]+)>\s*Tj|\((.*?)\)\s*Tj", s, re.S):
            if tok.group(1):
                current = fonts.get(names.get(tok.group(1)), {})
            elif tok.group(2) or tok.group(8):
                y = tok.group(7) or tok.group(9)
                if y_last is not None and y != y_last and row.strip():
                    lines.append(row)
                    row = ""
                elif row:
                    row += " "
                y_last = y
            else:
                parts = re.findall(rb"<([0-9A-Fa-f]+)>|\((.*?)\)", tok.group(10)) if tok.group(10) is not None else \
                    [(tok.group(11) or b"", tok.group(12) or b"")]
                for hexa, lit in parts:
                    if hexa:
                        w = 4 if len(hexa) % 4 == 0 and current and max(current, default=0) > 255 else 2
                        row += "".join(current.get(int(hexa[i:i + w], 16), "?") for i in range(0, len(hexa), w))
                    elif lit:
                        row += "".join(current.get(c, chr(c)) for c in lit)
        if row.strip():
            lines.append(row)
    open(sys.argv[2], "w", encoding="utf8").write("\n".join(lines))
    print(len(objs), "objects;", len(fonts), "fonts with maps;", len(lines), "text lines")


if __name__ == "__main__":
    main()

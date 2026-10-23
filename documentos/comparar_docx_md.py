# -*- coding: utf-8 -*-
"""Compara el texto de un .docx con el .md del que salió (solo lectura).

Sirve para dos cosas: comprobar que el conversor no ha perdido nada, y ver qué se ha cambiado a mano
en Word para llevarlo de vuelta al .md. Saca las imágenes del docx, los bloques que solo están en uno
de los dos y, en los bloques cambiados, la diferencia palabra a palabra: [-quitado-] {+añadido+}.

    python comparar_docx_md.py documento.docx documento.md

Sale con código 1 si hay diferencias, para poder usarlo en un script.
"""
import difflib
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def norm(t):
    t = re.sub(r"\*\*|`|\*", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"<(https?:[^>]+)>", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def bloques_docx(ruta):
    """Un texto por párrafo; las celdas de una fila de tabla se unen con ' | '."""
    z = zipfile.ZipFile(ruta)
    xml = z.read("word/document.xml")
    print("imágenes en el docx:", len([n for n in z.namelist() if n.startswith("word/media/")]))
    print("dibujos en el cuerpo:", xml.count(b"<a:blip "))
    salida = []
    for el in ET.fromstring(xml).find(W + "body"):
        if el.tag == W + "p":
            t = "".join(x.text or "" for x in el.iter(W + "t"))
            if t.strip():
                salida.append(norm(t))
        elif el.tag == W + "tbl":
            for fila in el.iter(W + "tr"):
                celdas = ["".join(x.text or "" for x in c.iter(W + "t")) for c in fila.iter(W + "tc")]
                salida.append(norm(" | ".join(celdas)))
    return salida


def bloques_md(ruta):
    """Párrafos unidos, elementos de lista, filas de tabla, pies de figura y líneas de código."""
    salida, par = [], []

    def cerrar():
        if par:
            salida.append(norm(" ".join(par)))
            par.clear()

    codigo = False
    for l in open(ruta, encoding="utf-8").read().splitlines():
        if l.startswith("```"):
            cerrar()
            codigo = not codigo
            continue
        if codigo:
            if l.strip():
                salida.append(norm(l))
            continue
        if not l.strip():
            cerrar()
            continue
        m = re.match(r"^!\[([^\]]*)\]", l)
        if m:
            cerrar()
            salida.append(norm(m.group(1)))
            continue
        if l.startswith("|"):
            cerrar()
            if not re.match(r"^\|[\s|:-]+\|$", l):
                salida.append(norm(" | ".join(c.strip() for c in l.strip()[1:-1].split("|"))))
            continue
        m = re.match(r"^\s*(?:- |\d+\. )(.+)", l)
        if m:
            cerrar()
            salida.append(norm(m.group(1)))
            continue
        if re.match(r"^#+ ", l):
            cerrar()
            salida.append(norm(l.lstrip("# ")))
            continue
        if not par and salida and re.match(r"^\s+\S", l):   # continuación de un elemento de lista
            salida[-1] = norm(salida[-1] + " " + l)
            continue
        par.append(l.strip())
    cerrar()
    return salida


def palabras(x, y):
    out = []
    for t in difflib.ndiff(x.split(), y.split()):
        if t[0] == " ":
            out.append(t[2:])
        elif t[0] == "-":
            out.append("[-" + t[2:] + "-]")
        elif t[0] == "+":
            out.append("{+" + t[2:] + "+}")
    idx = [k for k, w in enumerate(out) if w.startswith(("[-", "{+"))]
    keep = set(j for k in idx for j in range(k - 6, k + 7))
    frase, prev = [], -2
    for k, w in enumerate(out):
        if k in keep:
            if k != prev + 1:
                frase.append("...")
            frase.append(w)
            prev = k
    return " ".join(frase)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    docx, md = bloques_docx(sys.argv[1]), bloques_md(sys.argv[2])
    print(f"bloques md: {len(md)} · bloques docx: {len(docx)}")
    diferencias = 0
    sm = difflib.SequenceMatcher(None, md, docx, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        diferencias += 1
        print(f"\n=== {op} md[{a1}:{a2}] docx[{b1}:{b2}]")
        if op == "replace" and a2 - a1 == b2 - b1:
            for x, y in zip(md[a1:a2], docx[b1:b2]):
                print("  ", palabras(x, y))
            continue
        for t in md[a1:a2]:
            print("  MD  :", t[:220])
        for t in docx[b1:b2]:
            print("  DOCX:", t[:220])
    print("\nsin diferencias" if not diferencias else f"\n{diferencias} diferencias")
    sys.exit(1 if diferencias else 0)


if __name__ == "__main__":
    main()

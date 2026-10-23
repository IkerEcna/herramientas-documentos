# -*- coding: utf-8 -*-
"""Revisa la maquetación de un PDF antes de entregarlo.

Cuenta páginas y marcadores, dice en qué página empiezan los anexos y avisa, página a página, de:
  - un título al final de la página (su texto queda en la siguiente),
  - un hueco grande al final (una figura que no cabía y saltó),
  - una imagen sin su pie debajo en la misma página (el pie debe empezar por "Captura" o "Figura").
Genera además hojas de miniaturas (8 páginas por hoja) para mirarlas de un vistazo.

    python revisar_pdf.py documento.pdf carpeta_miniaturas [--anexos "Anexo A"] [--pies Captura,Figura]

Los marcadores salen de los títulos: en Word, "Guardar como PDF" con "Crear marcadores usando
títulos".
"""
import argparse
import os

import pymupdf

PIE_DE_PAGINA = 60   # pt que se descartan abajo: el pie con el número de página


def lineas(p):
    """Líneas de texto con su posición vertical y su tamaño de letra, sin el pie de página."""
    out = []
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t:
                out.append((l["bbox"][1], l["bbox"][3], max(s["size"] for s in l["spans"]), t))
    return [x for x in out if x[0] < p.rect.height - PIE_DE_PAGINA]


def revisar(doc, inicio_anexos, pies, hueco_max=200, titulo_min=12):
    for i, p in enumerate(doc, 1):
        ls, imgs, avisos = lineas(p), p.get_image_info(), []
        if ls:
            t = ls[-1]
            if t[2] >= titulo_min:
                avisos.append(f"TÍTULO al final de la página: {t[3][:60]}")
            hueco = p.rect.height - PIE_DE_PAGINA - max([x[1] for x in ls] + [im["bbox"][3] for im in imgs])
            if hueco > hueco_max and i != (inicio_anexos - 1 if inicio_anexos else -1):
                avisos.append(f"hueco de {hueco:.0f} pt al final")
        for im in imgs:
            debajo = [x for x in ls if x[0] >= im["bbox"][3] - 2]
            if not debajo or not debajo[0][3].startswith(pies):
                avisos.append("imagen sin su pie debajo en la misma página")
        print(f"p{i:02d} · {len(imgs)} img · " + (" | ".join(avisos) if avisos else "ok"))


def miniaturas(doc, carpeta, por_hoja=8, columnas=4):
    os.makedirs(carpeta, exist_ok=True)
    w, alto = 300, int(300 * 1.414)
    filas = -(-por_hoja // columnas)
    for h in range(0, doc.page_count, por_hoja):
        hoja = pymupdf.open()
        pg = hoja.new_page(width=w * columnas, height=alto * filas)
        for k, n in enumerate(range(h, min(h + por_hoja, doc.page_count))):
            r = pymupdf.Rect((k % columnas) * w, (k // columnas) * alto,
                             (k % columnas + 1) * w, (k // columnas + 1) * alto)
            pg.show_pdf_page(r, doc, n)
            pg.draw_rect(r, color=(0.6, 0.6, 0.6), width=0.5)
            pg.insert_text((r.x0 + 4, r.y0 + 12), str(n + 1), fontsize=10, color=(1, 0, 0))
        pg.get_pixmap(dpi=110).save(os.path.join(carpeta, f"hoja_{h // por_hoja + 1}.png"))
    print("hojas de miniaturas en", carpeta)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("miniaturas", help="carpeta donde dejar las hojas de miniaturas")
    ap.add_argument("--anexos", default="Anexo A", help="marcador con el que empiezan los anexos")
    ap.add_argument("--pies", default="Captura,Figura", help="cómo empiezan los pies de imagen, separados por comas")
    args = ap.parse_args()

    doc = pymupdf.open(args.pdf)
    print("páginas:", doc.page_count)
    toc = doc.get_toc()
    print("marcadores:", len(toc), "· nivel 1:", [t[1][:28] for t in toc if t[0] == 1])
    anexos = next((t[2] for t in toc if t[1].startswith(args.anexos)), None)
    if anexos:
        print(f"{args.anexos} empieza en la página {anexos} · cuerpo: {anexos - 1} páginas")
    revisar(doc, anexos, tuple(p.strip() for p in args.pies.split(",")))
    miniaturas(doc, args.miniaturas)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Convierte una transcripción en un texto legible sin cambiar ni una palabra.

Una transcripción de Whisper es una línea por segmento: difícil de leer. Un modelo de lenguaje puede
proponer dónde cortar en párrafos y qué título poner a cada bloque, pero no se le deja reescribir el
texto: solo devuelve un .legible.json con los cortes, y este script monta el .legible.md con las
líneas originales.

Formato del .legible.json, junto al .txt con el mismo nombre:
    [{"s": 1, "e": 14, "t": "Título del bloque"}, {"s": 15, "e": 30, "t": "..."}]
s y e son números de línea del .txt, contados desde 1 e inclusivos. t es opcional. Un hueco entre
bloques sale como párrafo sin título, para no perder texto.

    python legibles.py CARPETA [CARPETA ...]

Comprueba al final que el .legible.md tiene las mismas palabras, en el mismo orden, que el .txt, y
avisa si no.
"""
import glob
import json
import os
import re
import sys


def parrafo(lineas, a, b):
    """Une las líneas [a, b) (desde 0) en un párrafo, sin tocar el texto."""
    return " ".join(l.strip() for l in lineas[a:b] if l.strip())


def palabras(s):
    return re.findall(r"\w+", s.lower(), re.UNICODE)


def montar(lineas, bloques):
    """Devuelve (texto del .legible.md, si conserva todas las palabras del original)."""
    n = len(lineas)
    validos = []
    for g in bloques:
        if isinstance(g, dict) and "s" in g and "e" in g:
            try:
                validos.append({"s": int(g["s"]), "e": int(g["e"]), "t": str(g.get("t", ""))})
            except (TypeError, ValueError):
                pass
    validos.sort(key=lambda g: g["s"])
    partes, cur = [], 1   # cur: primera línea (desde 1) todavía sin cubrir
    for g in validos:
        s, e = max(1, g["s"]), min(n, g["e"])
        if e < cur:
            continue   # bloque solapado con lo ya cubierto
        s = max(s, cur)
        if s > cur:
            hueco = parrafo(lineas, cur - 1, s - 1)
            if hueco:
                partes.append(hueco)
        titulo = g["t"].strip().lstrip("#").strip()
        if titulo:
            partes.append("### " + titulo)
        texto = parrafo(lineas, s - 1, e)
        if texto:
            partes.append(texto)
        cur = e + 1
    if cur <= n:
        cola = parrafo(lineas, cur - 1, n)
        if cola:
            partes.append(cola)
    cuerpo = "\n\n".join(partes).strip() + "\n"
    igual = palabras(" ".join(lineas)) == palabras(" ".join(p for p in partes if not p.startswith("### ")))
    return cuerpo, igual


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    hechos = fallos = distintos = 0
    for carpeta in sys.argv[1:]:
        for js in glob.glob(os.path.join(carpeta, "**", "*.legible.json"), recursive=True):
            base = js[:-len(".legible.json")]
            if not os.path.exists(base + ".txt"):
                continue
            lineas = open(base + ".txt", encoding="utf-8").read().splitlines()
            try:
                bloques = json.load(open(js, encoding="utf-8"))
                assert isinstance(bloques, list)
            except (ValueError, AssertionError):
                fallos += 1
                print("[JSON no válido]", os.path.basename(js))
                continue
            cuerpo, igual = montar(lineas, bloques)
            with open(base + ".legible.md", "w", encoding="utf-8") as f:
                f.write(cuerpo)
            hechos += 1
            if not igual:
                distintos += 1
                print("[AVISO: no conserva todas las palabras]", os.path.basename(base + ".txt"))
    print(f"\nlegibles creados: {hechos} · JSON no válidos: {fallos} · avisos: {distintos}")


if __name__ == "__main__":
    main()

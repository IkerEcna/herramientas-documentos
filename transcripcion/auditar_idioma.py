# -*- coding: utf-8 -*-
"""Busca transcripciones que han salido en un idioma que no toca.

Whisper con detección automática a veces se equivoca de idioma en los primeros segundos y transcribe
la grabación entera en él: un vídeo en inglés acabó en galés. Este script cuenta palabras muy
frecuentes de cada idioma en el principio de cada .txt y marca los que no están en el esperado.

    python auditar_idioma.py CARPETA [--esperado es] [--ingles-si-contiene inglés,ingles] [--solo TEXTO]

Con --ingles-si-contiene, un fichero cuyo nombre lleve alguno de esos textos se espera en inglés.
Es una heurística: detecta errores gruesos, no matices. Lo marcado se vuelve a transcribir con el
idioma fijo (transcribir.py --idioma ... --rehacer).
"""
import argparse
import glob
import os
import re
import sys

FRECUENTES = {
    "es": r"que|de|la|el|los|las|un|una|para|con|como|es|en|y|nos|se",
    "en": r"the|and|of|to|a|in|is|that|it|we|you|for|this|are",
    "cy": r"ydych|yn|ymgyrch|ddechrau|bod|yr|wedi|gyfer|mae|chi|ac|roedd|hwn|gan",   # galés
    "pt": r"não|uma|os|as|com|para|isso|você|muito|também|são|está",
    "it": r"che|il|di|non|una|per|sono|questo|anche|della|gli|perché",
}
PATRONES = {k: re.compile(rf"\b({v})\b", re.I) for k, v in FRECUENTES.items()}


def idioma_dominante(texto, caracteres=4000):
    muestra = re.sub(r"\s+", " ", texto)[:caracteres]
    cuentas = {k: len(p.findall(muestra)) for k, p in PATRONES.items()}
    return max(cuentas, key=cuentas.get), cuentas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--esperado", default="es", choices=sorted(FRECUENTES))
    ap.add_argument("--ingles-si-contiene", default="", help="textos del nombre, separados por comas")
    ap.add_argument("--solo", default="", help="solo los .txt cuyo nombre case con esta regex")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    marcas = [m.strip().lower() for m in args.ingles_si_contiene.split(",") if m.strip()]
    ficheros = sorted(f for f in glob.glob(os.path.join(args.carpeta, "**", "*.txt"), recursive=True)
                      if not args.solo or re.search(args.solo, os.path.basename(f)))
    sospechosos = []
    for f in ficheros:
        b = os.path.basename(f)
        esperado = "en" if any(m in b.lower() for m in marcas) else args.esperado
        dominante, cuentas = idioma_dominante(open(f, encoding="utf-8").read())
        mal = dominante != esperado
        if mal:
            sospechosos.append(f)
        detalle = "/".join(f"{k}{v}" for k, v in cuentas.items())
        print(f"[{esperado}] ~{dominante} ({detalle}) {b[:60]}" + ("  <-- REVISAR" if mal else ""))
    print(f"\n{len(ficheros)} transcripciones · {len(sospechosos)} sospechosas")
    for f in sospechosos:
        print("  " + os.path.relpath(f, args.carpeta))
    sys.exit(1 if sospechosos else 0)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Transcribe audio y vídeo en local con faster-whisper: deja junto a cada fichero un .txt (una línea
por segmento) y un .srt con los tiempos.

    python transcribir.py RUTA [RUTA ...] [--modelo medium] [--idioma es] [--hilos 10]
                          [--prompt TEXTO | --prompt-fichero RUTA] [--solo TEXTO | --solo re:REGEX]
                          [--excluir TEXTO] [--rehacer]

Cada RUTA puede ser un fichero o una carpeta (se busca dentro, con subcarpetas). Por defecto se salta
lo que ya tiene su .txt, así que se puede cortar y relanzar. Corre en CPU con int8.

El prompt da contexto y vocabulario al modelo (nombres propios, siglas del tema). Solo se usa si el
idioma es fijo: con --idioma auto podría sesgar la detección.
"""
import argparse
import glob
import os
import re
import sys
import time

EXTENSIONES = (".mp4", ".mkv", ".webm", ".mov", ".mp3", ".m4a", ".wav", ".ogg", ".flac")


def fmt_ts(t):
    h, m, s = int(t // 3600), int((t % 3600) // 60), t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def recoger(rutas, solo="", excluir=""):
    """Ficheros de audio o vídeo de las rutas, ordenados, filtrados por nombre."""
    encontrados = []
    for p in rutas:
        if os.path.isdir(p):
            encontrados += [f for f in glob.glob(os.path.join(p, "**", "*"), recursive=True)
                            if f.lower().endswith(EXTENSIONES)]
        else:
            encontrados.append(p)
    salida = []
    for f in sorted(set(encontrados)):
        b = os.path.basename(f)
        if excluir and excluir.lower() in b.lower():
            continue
        if solo:
            if solo.startswith("re:"):
                if not re.search(solo[3:], b):
                    continue
            elif solo.lower() not in b.lower():
                continue
        salida.append(f)
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rutas", nargs="+")
    ap.add_argument("--modelo", default="medium", help="tiny, base, small, medium, large-v3...")
    ap.add_argument("--idioma", default="es", help="código del idioma, o auto para detectarlo")
    ap.add_argument("--hilos", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--prompt-fichero")
    ap.add_argument("--solo", default="", help="solo los nombres que contengan esto (o re:REGEX)")
    ap.add_argument("--excluir", default="", help="salta los nombres que contengan esto")
    ap.add_argument("--rehacer", action="store_true", help="transcribe también lo que ya tiene su .txt")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    prompt = args.prompt
    if args.prompt_fichero:
        prompt = open(args.prompt_fichero, encoding="utf-8").read().strip()
    if args.idioma == "auto":
        prompt = ""   # un prompt en un idioma sesga la detección

    ficheros = recoger(args.rutas, args.solo, args.excluir)
    pendientes = [f for f in ficheros if args.rehacer or not os.path.exists(os.path.splitext(f)[0] + ".txt")]
    print(f"[inicio] modelo={args.modelo} hilos={args.hilos} | {len(ficheros)} ficheros, {len(pendientes)} pendientes",
          flush=True)
    if not pendientes:
        return

    from faster_whisper import WhisperModel   # aquí, para que --help no tenga que cargarlo
    t0 = time.time()
    modelo = WhisperModel(args.modelo, device="cpu", compute_type="int8", cpu_threads=args.hilos)
    print(f"[inicio] modelo cargado en {time.time() - t0:.0f}s", flush=True)
    hechos = errores = 0
    for ruta in pendientes:
        base, t = os.path.splitext(ruta)[0], time.time()
        try:
            segmentos, info = modelo.transcribe(ruta, language=None if args.idioma == "auto" else args.idioma,
                                                vad_filter=True, beam_size=5, initial_prompt=prompt or None)
            lineas, srt = [], []
            for i, s in enumerate(segmentos, 1):
                lineas.append(s.text.strip())
                srt.append(f"{i}\n{fmt_ts(s.start)} --> {fmt_ts(s.end)}\n{s.text.strip()}\n")
            with open(base + ".txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lineas) + "\n")
            with open(base + ".srt", "w", encoding="utf-8") as f:
                f.write("\n".join(srt))
            hechos += 1
            dur = time.time() - t
            print(f"[{hechos}/{len(pendientes)}] {os.path.basename(ruta)} | audio {info.duration:.0f}s "
                  f"({info.language}) | {dur:.0f}s | x{info.duration / dur:.2f} tiempo real", flush=True)
        except Exception as e:   # un fichero roto no para la tanda
            errores += 1
            print(f"[ERROR] {os.path.basename(ruta)} :: {e}", flush=True)
    print(f"[fin] {hechos} transcritos, {errores} errores, en {(time.time() - t0) / 60:.1f} min", flush=True)
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()

"""
build_v2.py — Painel DDA Arapiraca v2.1 (arquitetura desacoplada).

Este script NÃO monta HTML. Ele apenas:
  1. Copia v2/casos_anonimizados.json → raiz/casos_anonimizados.json
  2. Garante que favicon.png existe (gera 32×32 a partir de Logo_PMA.png se necessário)
  3. Imprime resumo dos arquivos publicáveis (tamanho, modificação)

Antes de rodar, certifique-se que:
  - python anonimizador.py já foi executado nesta sessão (v2/casos_anonimizados.json atualizado)
  - dashboard_v2_app.js, dashboard_v2_styles.css, index.html, documentacao.html
    estão presentes na raiz (gerenciados por edição direta no editor / git)

USO:
    python v2/build_v2.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent          # v2/
ROOT = HERE.parent                              # raiz do projeto

SRC_JSON = HERE / "casos_anonimizados.json"
DST_JSON = ROOT / "casos_anonimizados.json"

SRC_CSV = HERE / "casos_anonimizados.csv"
DST_CSV = ROOT / "casos_anonimizados.csv"

LOGO = ROOT / "Logo_PMA.png"
ICONE = ROOT / "Icone_PMA.png"   # fonte preferida do favicon
FAVICON = ROOT / "favicon.png"

PUBLIC_FILES = [
    "index.html",
    "documentacao.html",
    "dashboard_v2_app.js",
    "dashboard_v2_styles.css",
    "casos_anonimizados.json",
    "casos_anonimizados.csv",
    "arapiraca_bairros.json",
    "Logo_PMA.png",
    "Icone_PMA.png",
    "favicon.png",
]


def copy_data():
    if not SRC_JSON.exists():
        print(f"ERRO: {SRC_JSON} não existe. Rode primeiro: python v2/anonimizador.py")
        sys.exit(1)
    print(f"[COPY] {SRC_JSON.name} → raiz")
    shutil.copy2(SRC_JSON, DST_JSON)
    print(f"        ok ({DST_JSON.stat().st_size // 1024} KB)")

    if SRC_CSV.exists():
        print(f"[COPY] {SRC_CSV.name} → raiz (auditoria pública)")
        shutil.copy2(SRC_CSV, DST_CSV)
        print(f"        ok ({DST_CSV.stat().st_size // 1024} KB)")
    else:
        print(f"[CSV]  AVISO: {SRC_CSV.name} não encontrado — auditoria pública não publicada.")


def ensure_favicon():
    """
    Gera favicon.png a partir de Icone_PMA.png (preferido) ou Logo_PMA.png
    como fallback. Sobrescreve sempre — assim, mudanças no ícone fonte
    propagam pro favicon na próxima execução do build.
    """
    src = ICONE if ICONE.exists() else (LOGO if LOGO.exists() else None)
    if src is None:
        print("[FAVICON] AVISO: nem Icone_PMA.png nem Logo_PMA.png existem; favicon não gerado.")
        return
    try:
        from PIL import Image
    except ImportError:
        # Fallback: copia o ícone direto (browsers redimensionam)
        print(f"[FAVICON] Pillow não instalado — copiando {src.name} como favicon.png")
        shutil.copy2(src, FAVICON)
        return
    img = Image.open(src).convert("RGBA")
    # 64×64 cobre 16/32/48 com qualidade — browsers escalam para baixo
    img.thumbnail((64, 64), Image.LANCZOS)
    img.save(FAVICON, "PNG", optimize=True)
    print(f"[FAVICON] gerado a partir de {src.name} ({FAVICON.stat().st_size} bytes)")


def report_public_files():
    print()
    print("=" * 60)
    print("ARQUIVOS PÚBLICOS NA RAIZ:")
    print("=" * 60)
    for name in PUBLIC_FILES:
        p = ROOT / name
        if p.exists():
            size = p.stat().st_size
            unit = "KB" if size < 1024 * 1024 else "MB"
            value = size / 1024 if unit == "KB" else size / (1024 * 1024)
            mt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m %H:%M")
            print(f"  {name:35s}  {value:8.1f} {unit}   {mt}")
        else:
            print(f"  {name:35s}  AUSENTE")
    print("=" * 60)


def main():
    print("=" * 60)
    print("BUILD v2.1 — Painel DDA Arapiraca")
    print("=" * 60)
    copy_data()
    ensure_favicon()
    report_public_files()
    print()
    print("Build concluído. Abra index.html via servidor estático para testar:")
    print("    python -m http.server 8000")
    print("    → http://localhost:8000/")
    print()


if __name__ == "__main__":
    main()

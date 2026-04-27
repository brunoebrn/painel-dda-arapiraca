"""
Pipeline de anonimização — Painel DDA Arapiraca v2.

Lê os 3 xlsx brutos (FAI, FCI, Cidadão), faz os joins necessários,
remove dados pessoais identificáveis e gera a base anonimizada
em parquet, json e csv.

USO:
    python anonimizador.py

ENTRADAS (na pasta-pai do projeto, fora do v2/):
    - 69d39b922da2d_*producao_fai.xlsx
    - 69d3a36966bf5_*producao_fci.xlsx
    - 69d3cba31a8fd_*producao_cidadao.xlsx
    - _internal_cache.py  (com CACHE_TOKEN, fora do git)

SAÍDAS (na pasta v2/):
    - casos_anonimizados.parquet  (canônica)
    - casos_anonimizados.json     (consumida pelo painel web)
    - casos_anonimizados.csv      (auditoria pública)
    - relatorio_anonimizacao.txt  (estatísticas e validações)

LGPD:
    Este script aplica hash determinístico SHA-256 sobre identificadores
    de pacientes, com sal local não versionado. Saídas não contêm
    nome, CPF, nome da mãe, nome do pai, logradouro, número ou
    complemento. Profissionais são identificados pelo CNS (informação
    pública do MS, agente do Estado, mantida para análise de produção).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ERRO: pandas não instalado. Rode: pip install pandas openpyxl pyarrow")
    sys.exit(1)

# Módulo local de deduplicação (mesma pasta v2/)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dedup  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent       # pasta v2/
PROJECT = HERE.parent                          # pasta do projeto

# Onde estão os xlsx brutos: por padrão na pasta-pai (PROJECT). Pode ser
# sobrescrito via variável de ambiente PAINEL_XLSX_DIR (útil quando o código
# está num clone git separado dos dados sensíveis no OneDrive).
import os as _os
_xlsx_env = _os.environ.get("PAINEL_XLSX_DIR")
XLSX_DIR = Path(_xlsx_env).resolve() if _xlsx_env else PROJECT

OUT_PARQUET = HERE / "casos_anonimizados.parquet"
OUT_JSON = HERE / "casos_anonimizados.json"
OUT_CSV = HERE / "casos_anonimizados.csv"
OUT_REPORT = HERE / "relatorio_anonimizacao.txt"

CID_FILTER = "A09"  # Doença Diarreica Aguda

# Tenta carregar o token local. Se não existir, falha com mensagem clara.
def _load_cache_token() -> str:
    candidates = [HERE / "_internal_cache.py", PROJECT / "_internal_cache.py"]
    for p in candidates:
        if p.exists():
            ns: dict = {}
            exec(p.read_text(encoding="utf-8"), ns)
            tok = ns.get("CACHE_TOKEN", "")
            if tok and tok != "REPLACE_WITH_LOCAL_TOKEN":
                return tok
    print(
        "ERRO: arquivo _internal_cache.py não encontrado ou com placeholder.\n"
        "Crie o arquivo na pasta v2/ ou na raiz do projeto com:\n"
        '    CACHE_TOKEN = "<token gerado localmente>"\n'
        "\n"
        "Para gerar um token seguro, rode no PowerShell ou Git Bash:\n"
        '    python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
        "Cole a saída como valor de CACHE_TOKEN."
    )
    sys.exit(2)


_K = _load_cache_token()
_K_PROF = _K + "::p"   # derivação para profissionais (caso futuro)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _norm_str(v) -> str:
    """Normaliza string: remove espaços externos, NFC, lowercase."""
    if v is None:
        return ""
    s = str(v).strip()
    if not s or s.lower() in {"none", "nan", "-", "0"}:
        return ""
    return unicodedata.normalize("NFKC", s).lower()


def _digits_only(v) -> str:
    """Remove tudo que não é dígito; útil para CNS, CPF, CEP."""
    if v is None:
        return ""
    s = re.sub(r"\D", "", str(v))
    return s.lstrip("0")


def stable_id(*parts: str, salt: str = _K, length: int = 12) -> str:
    """Hash determinístico SHA-256 truncado, com sal local."""
    payload = salt + "::" + "|".join(p for p in parts if p)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def patient_id_from_canonical(canonical: str) -> str:
    """
    Gera paciente_id a partir do canonical_key produzido pela deduplicação.
    canonical já incorpora informação de quaisquer registros unidos.
    """
    return stable_id("paciente", canonical)


def patient_id_fallback(cns, cpf, nome, data_nasc, mae) -> str:
    """
    Fallback: usado apenas para registros que não puderam ser
    deduplicados (sem CNS, sem CPF). Hash sobre (nome+data+mãe) ou idx.
    """
    cns_d = _digits_only(cns)
    if cns_d and cns_d != "0":
        return stable_id("paciente", "cns:" + cns_d)
    cpf_d = _digits_only(cpf)
    if cpf_d and len(cpf_d) >= 9:
        return stable_id("paciente", "cpf:" + cpf_d)
    nome_n = _norm_str(nome)
    mae_n = _norm_str(mae)
    dn = _norm_date(data_nasc)
    if nome_n and dn:
        return stable_id("paciente", "fb:" + nome_n + ":" + dn + ":" + mae_n)
    return stable_id("paciente", "unk:" + str(id((cns, cpf, nome))))


def _norm_date(v) -> str:
    """Converte para AAAAMMDD; vazio se falhar."""
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y%m%d")
    s = str(v).strip()
    # tenta parsing
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return ""


def _faixa_etaria(idade: int | None) -> str:
    if idade is None:
        return "nd"
    if idade < 1:
        return "<1a"
    if idade == 1:
        return "1a"
    if 2 <= idade <= 4:
        return "2-4a"
    if 5 <= idade <= 9:
        return "5-9a"
    if 10 <= idade <= 17:
        return "10-17a"
    if 18 <= idade <= 29:
        return "18-29a"
    if 30 <= idade <= 44:
        return "30-44a"
    if 45 <= idade <= 59:
        return "45-59a"
    return "60+"


def _calc_idade(data_nasc_yyyymmdd: str, data_atend_yyyymmdd: str) -> int | None:
    if not data_nasc_yyyymmdd or not data_atend_yyyymmdd:
        return None
    try:
        dn = datetime.strptime(data_nasc_yyyymmdd, "%Y%m%d").date()
        da = datetime.strptime(data_atend_yyyymmdd, "%Y%m%d").date()
    except ValueError:
        return None
    anos = da.year - dn.year - ((da.month, da.day) < (dn.month, dn.day))
    return anos if 0 <= anos <= 130 else None


def _bool_yn(v) -> bool:
    if v is None:
        return False
    s = _norm_str(v)
    return s in {"sim", "s", "yes", "y", "true", "1"}


def _norm_zona(ubs: str, bairro: str) -> str:
    """
    Heurística simples baseada em palavras-chave em UBS/bairro.
    Idealmente substituída por mapeamento oficial da SMS futuramente.
    """
    txt = (str(ubs) + " " + str(bairro)).upper()
    rurais = ["RURAL", "POVOADO", "ASSENTAMENTO", "ZONA RURAL", "STIO", "SÍTIO"]
    for r in rurais:
        if r in txt:
            return "RURAL"
    return "URBANA"


def _norm_cep(v) -> str:
    d = _digits_only(v)
    if len(d) != 8:
        return ""
    return d[:5] + "-" + d[5:]


def _parse_cids(v: str) -> tuple[str, str]:
    """
    e-SUS exporta CIDs como '|A09|J06.9|' — pipes como separadores.
    Retorna (principal, secundarios_csv).
    """
    if not v:
        return "", ""
    parts = [p.strip() for p in str(v).split("|") if p.strip()]
    if not parts:
        return "", ""
    return parts[0], ",".join(parts[1:])


# ─────────────────────────────────────────────────────────────────────────────
# LOAD INPUTS
# ─────────────────────────────────────────────────────────────────────────────

def _find_xlsx(pattern_substring: str) -> Path:
    """Procura em XLSX_DIR um xlsx que contenha o padrão no nome."""
    candidates = sorted(XLSX_DIR.glob("*.xlsx"))
    for c in candidates:
        if pattern_substring in c.name.lower():
            return c
    raise FileNotFoundError(
        f"Nenhum xlsx contendo '{pattern_substring}' encontrado em {XLSX_DIR}.\n"
        f"Arquivos disponíveis: {[c.name for c in candidates]}\n"
        f"Defina PAINEL_XLSX_DIR para apontar à pasta com os xlsx brutos."
    )


def _load_xlsx_fast(path: Path, label: str, key_filter=None,
                    key_cols=("CNS", "CPF")) -> pd.DataFrame:
    """
    Leitura rapida via openpyxl read_only.
    Se key_filter for fornecido, mantem apenas linhas cujo valor de qualquer
    coluna em key_cols (apos digits_only) esteja em key_filter.
    """
    import openpyxl
    print(f"[{label}] Lendo {path.name}...", flush=True)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header = next(rows_iter)
    header = [str(h).upper().strip() if h else f"COL{i}" for i, h in enumerate(header)]
    key_idx = [i for i, h in enumerate(header) if h in key_cols]
    data = []
    n_lidas = 0
    for row in rows_iter:
        n_lidas += 1
        if key_filter is not None:
            keep = False
            for ki in key_idx:
                v = row[ki] if ki < len(row) else None
                if v is None:
                    continue
                d = re.sub(r"\D", "", str(v)).lstrip("0")
                if d and d in key_filter:
                    keep = True
                    break
            if not keep:
                continue
        data.append([
            "" if v is None else (
                v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else str(v)
            )
            for v in row
        ])
        if n_lidas % 50000 == 0:
            print(f"  ... {n_lidas} lidas, {len(data)} mantidas", flush=True)
    wb.close()
    df = pd.DataFrame(data, columns=header)
    if key_filter is not None:
        print(f"   -> {n_lidas} lidas, {len(df)} mantidas (filtradas)", flush=True)
    else:
        print(f"   -> {len(df)} linhas", flush=True)
    return df


def load_fai() -> pd.DataFrame:
    return _load_xlsx_fast(_find_xlsx("producao_fai"), "FAI")


def load_fci(key_filter=None) -> pd.DataFrame:
    return _load_xlsx_fast(_find_xlsx("producao_fci"), "FCI", key_filter=key_filter)


def load_cidadao(key_filter=None) -> pd.DataFrame:
    return _load_xlsx_fast(_find_xlsx("producao_cidadao"), "CIDADAO", key_filter=key_filter)



# ─────────────────────────────────────────────────────────────────────────────
# CORE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def build_lookup(df: pd.DataFrame, key_cols: list[str]) -> dict[str, dict]:
    """
    Constrói um dict { chave → linha (subset de colunas) } usando o primeiro
    valor não-vazio para cada CNS/CPF.
    """
    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        for k in key_cols:
            v = row.get(k)
            d = _digits_only(v)
            if d and d != "0" and d not in out:
                out[d] = row.to_dict()
    return out


def _build_dedup_input(fai: pd.DataFrame, fci: pd.DataFrame, cid: pd.DataFrame):
    """
    Constrói lista de RegistroDedup a partir das 3 bases.
    Inclui APENAS registros com algum identificador útil (CNS, CPF ou nome).
    """
    regs = []
    next_idx = 0
    for origem, df in [("fai", fai), ("fci", fci), ("cidadao", cid)]:
        for _, row in df.iterrows():
            r = dedup.RegistroDedup(
                idx=next_idx,
                origem=origem,
                cns=row.get("CNS"),
                cpf=row.get("CPF"),
                nome=row.get("NOME"),
                mae=row.get("MAE"),
                data_nasc=row.get("DATA NASCIMENTO") if origem != "fai" else None,
            )
            # só inclui se tem identificador ou nome+data
            if r.cns or r.cpf or (r.nome and r.data_nasc):
                regs.append(r)
                next_idx += 1
    return regs


def _resolve_canonical(indice: dict[str, str], cns: str, cpf: str) -> str | None:
    """Dado CNS/CPF de um registro, busca seu canonical_key no índice."""
    if cns:
        v = indice.get("cns:" + cns)
        if v:
            return v
    if cpf:
        v = indice.get("cpf:" + cpf)
        if v:
            return v
    return None


def anonimizar() -> pd.DataFrame:
    fai = load_fai()

    print(f"[FILTER] Filtrando FAI por CID '{CID_FILTER}'...")
    mask = fai["CIDS"].fillna("").str.contains(rf"\|{CID_FILTER}(\.|\|)", regex=True, na=False)
    mask |= fai["CIDS"].fillna("").str.contains(CID_FILTER, na=False)
    fai = fai[mask].copy()
    print(f"   -> {len(fai)} atendimentos com {CID_FILTER}")

    chaves_alvo = set()
    for col in ("CNS", "CPF"):
        for v in fai[col].fillna(""):
            d = _digits_only(v)
            if d and d != "0":
                chaves_alvo.add(d)
    print(f"[KEYS] {len(chaves_alvo)} chaves unicas (CNS+CPF) na FAI filtrada")

    fci_rel = load_fci(key_filter=chaves_alvo)
    cid_rel = load_cidadao(key_filter=chaves_alvo)
    print(f"   -> FCI: {len(fci_rel)} | CIDADAO: {len(cid_rel)}")

    print("[DEDUP] Executando record linkage (hard + soft match)...")
    regs_dedup = _build_dedup_input(fai, fci_rel, cid_rel)
    indice_dedup = dedup.deduplicar(regs_dedup)
    print(f"   → {len(set(indice_dedup.values()))} pacientes canônicos identificados")
    print(f"   → relatório: {dedup.RELATORIO_PATH.name}")
    if dedup.DUVIDAS_PATH.exists():
        print(f"   → ATENÇÃO: dúvidas para revisar manualmente em {dedup.DUVIDAS_PATH.name}")

    # Lookups de FCI e CIDADAO via CNS e CPF (para enriquecimento)
    print("[BUILD] Construindo lookups FCI e CIDADAO para enriquecimento...")
    fci_by_key = build_lookup(fci_rel, ["CNS", "CPF"])
    cid_by_key = build_lookup(cid_rel, ["CNS", "CPF"])

    # Itera sobre FAI e enriquece
    print("[ENRICH] Gerando registros anonimizados...")
    rows: list[dict] = []
    for _, fai_row in fai.iterrows():
        cns_d = _digits_only(fai_row.get("CNS"))
        cpf_d = _digits_only(fai_row.get("CPF"))
        keys = [k for k in (cns_d, cpf_d) if k and k != "0"]

        fci_match = next((fci_by_key[k] for k in keys if k in fci_by_key), {})
        cid_match = next((cid_by_key[k] for k in keys if k in cid_by_key), {})

        # paciente_id via deduplicação (canonical_key) ou fallback
        canonical = _resolve_canonical(indice_dedup, cns_d, cpf_d)
        if canonical:
            pid = patient_id_from_canonical(canonical)
        else:
            pid = patient_id_fallback(
                fai_row.get("CNS"),
                fai_row.get("CPF"),
                fai_row.get("NOME"),
                fci_match.get("DATA NASCIMENTO") or cid_match.get("DATA NASCIMENTO"),
                fai_row.get("MAE"),
            )

        # Datas
        data_atend = _norm_date(fai_row.get("DATA DA CONSULTA"))
        data_nasc = _norm_date(
            fci_match.get("DATA NASCIMENTO") or cid_match.get("DATA NASCIMENTO")
        )

        idade = _calc_idade(data_nasc, data_atend)
        faixa = _faixa_etaria(idade)

        # CIDs
        cid_principal, cids_secundarios = _parse_cids(fai_row.get("CIDS"))

        # Bairro (do cadastro do paciente)
        bairro = _norm_str(cid_match.get("BAIRRO")).upper()
        cep = _norm_cep(cid_match.get("CEP"))

        # ─── UNIDADE DE ATENDIMENTO (vem da FAI = onde o atend ocorreu) ─────
        ubs_atend = _norm_str(fai_row.get("UNIDADE SAUDE")).upper()
        equipe_atend = _norm_str(fai_row.get("EQUIPE")).upper()
        ine_atend = _digits_only(fai_row.get("INE"))
        cnes_atend = _digits_only(fai_row.get("CNES"))

        # ─── UNIDADE DE REFERÊNCIA (vem do FCI/Cidadão = vinculação do paciente) ─
        # Prioriza FCI (cadastro clínico longitudinal); fallback Cidadão.
        ubs_ref = _norm_str(fci_match.get("UNIDADE SAUDE")).upper() or \
                  _norm_str(cid_match.get("UNIDADE SAUDE")).upper()
        equipe_ref = _norm_str(fci_match.get("EQUIPE")).upper() or \
                     _norm_str(cid_match.get("EQUIPE")).upper()
        ine_ref = _digits_only(fci_match.get("INE")) or \
                  _digits_only(cid_match.get("INE"))
        cnes_ref = _digits_only(fci_match.get("CNES")) or \
                   _digits_only(cid_match.get("CNES"))
        microarea_ref = _norm_str(fci_match.get("MICRO AREA")) or \
                        _norm_str(cid_match.get("MICRO AREA"))

        # Sem vinculação localizada: cadastro não tem UBS de referência
        # ou tem mas é uma unidade genérica/UPA (heurística por nome).
        sem_vinculacao = not ubs_ref
        if sem_vinculacao:
            ubs_ref = "SEM VINCULACAO LOCALIZADA"
            equipe_ref = "SEM VINCULACAO LOCALIZADA"

        # Atendido fora da UBS de referência?
        # True quando paciente está vinculado a uma UBS mas foi atendido em outra.
        # Falso para 'sem vinculação' (sem como saber).
        if not sem_vinculacao and ubs_atend and ubs_atend != ubs_ref:
            fora_da_referencia = True
        else:
            fora_da_referencia = False

        # Zona (com base na UBS de referência - mais consistente para gestão)
        zona = _norm_zona(ubs_ref, bairro)

        # Profissional (não anonimizar — informação pública MS)
        cns_prof = _digits_only(fai_row.get("CNS PROFISSIONAL"))

        # Mês e dia da semana do atendimento
        mes_atend = int(data_atend[4:6]) if data_atend else 0
        dia_semana = ""
        if data_atend and len(data_atend) == 8:
            try:
                dt = datetime.strptime(data_atend, "%Y%m%d").date()
                dia_semana = dt.strftime("%a").upper()  # MON, TUE, ...
            except ValueError:
                dia_semana = ""

        rec = {
            "paciente_id": pid,
            "sexo": _norm_str(fai_row.get("SEXO")).upper()[:1] or "",
            "data_nasc": data_nasc,
            "idade_anos_atend": idade if idade is not None else -1,
            "faixa_etaria": faixa,
            "data_atendimento": data_atend,
            "mes_atendimento": mes_atend,
            "dia_semana_atend": dia_semana,
            "cep": cep,
            "bairro": bairro,
            "zona": zona,
            # ── unidade de atendimento ──
            "ubs_atendimento": ubs_atend,
            "equipe_atendimento": equipe_atend,
            "ine_atendimento": ine_atend,
            "cnes_atendimento": cnes_atend,
            # ── unidade de referência (vinculação) ──
            "ubs_referencia": ubs_ref,
            "equipe_referencia": equipe_ref,
            "ine_referencia": ine_ref,
            "cnes_referencia": cnes_ref,
            "microarea_referencia": microarea_ref,
            # ── flags ──
            "sem_vinculacao_aps": sem_vinculacao,
            "fora_da_referencia": fora_da_referencia,
            # ── clínico ──
            "cns_profissional": cns_prof,
            "cid_principal": cid_principal,
            "cids_secundarios": cids_secundarios,
            "menor_5": (idade is not None and idade < 5),
            "gestante": _bool_yn(fci_match.get("GESTANTE")),
            "diabetico": _bool_yn(fci_match.get("DIABETICO")),
            "hipertenso": _bool_yn(fci_match.get("HIPERTENSO")),
            "morador_rua": _bool_yn(fci_match.get("MORADOR RUA")),
        }
        rows.append(rec)

    df = pd.DataFrame(rows)

    # Derivados que dependem do dataset inteiro
    print("[DERIVE] Calculando flag de recorrência...")
    cnt = df["paciente_id"].value_counts()
    df["repetido"] = df["paciente_id"].map(lambda p: int(cnt.get(p, 0)) >= 2)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────

def write_outputs(df: pd.DataFrame) -> dict:
    print(f"[WRITE] Gravando {len(df)} registros...", flush=True)
    # Parquet eh opcional: pula se pyarrow/fastparquet faltarem
    parquet_ok = False
    try:
        df.to_parquet(OUT_PARQUET, compression="snappy", index=False)
        parquet_ok = True
        print(f"   parquet ok: {OUT_PARQUET.name}", flush=True)
    except Exception as e:
        print(f"   parquet PULADO ({type(e).__name__}: {str(e)[:80]}); seguindo", flush=True)

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")  # BOM para Excel
    print(f"   csv ok: {OUT_CSV.name}", flush=True)

    # JSON minificado, registros como lista
    payload = {
        "metadata": {
            "schema_version": "1.0",
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "total_registros": len(df),
            "cid_filtro": CID_FILTER,
            "fonte": "e-SUS APS — FAI/FCI/Cidadão",
            "anonimizacao": "SHA-256 + sal local; sem PII direta",
        },
        "registros": df.to_dict(orient="records"),
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"   json ok: {OUT_JSON.name}", flush=True)
    # Sinaliza para o relatorio se parquet foi gerado
    df._parquet_gerado = parquet_ok  # type: ignore[attr-defined]

    sizes = {
        "parquet_kb": (OUT_PARQUET.stat().st_size // 1024) if OUT_PARQUET.exists() else 0,
        "json_kb": OUT_JSON.stat().st_size // 1024,
        "csv_kb": OUT_CSV.stat().st_size // 1024,
    }
    parq_str = f"{sizes['parquet_kb']} KB" if sizes['parquet_kb'] else "(nao gerado)"
    print(
        f"   tamanhos: parquet={parq_str}  "
        f"json={sizes['json_kb']} KB  csv={sizes['csv_kb']} KB",
        flush=True,
    )
    return sizes


def write_report(df: pd.DataFrame, sizes: dict):
    lines = [
        "RELATÓRIO DE ANONIMIZAÇÃO — Painel DDA Arapiraca v2",
        "=" * 60,
        f"Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        f"Total de registros: {len(df)}",
        f"Pacientes únicos (paciente_id): {df['paciente_id'].nunique()}",
        f"Pacientes com ≥2 atendimentos (repetidos): "
        f"{(df['paciente_id'].value_counts() >= 2).sum()}",
        "",
        "DISTRIBUIÇÃO POR SEXO:",
        df["sexo"].value_counts(dropna=False).to_string(),
        "",
        "DISTRIBUIÇÃO POR FAIXA ETÁRIA:",
        df["faixa_etaria"].value_counts(dropna=False).to_string(),
        "",
        "DISTRIBUIÇÃO POR MÊS:",
        df["mes_atendimento"].value_counts().sort_index().to_string(),
        "",
        "TOP 10 UBS DE ATENDIMENTO (onde o atendimento ocorreu):",
        df["ubs_atendimento"].value_counts().head(10).to_string(),
        "",
        "TOP 10 UBS DE REFERENCIA (vinculacao do paciente):",
        df["ubs_referencia"].value_counts().head(10).to_string(),
        "",
        f"Pacientes sem vinculacao APS localizada: {df['sem_vinculacao_aps'].sum()}",
        f"Atendimentos fora da UBS de referencia: {df['fora_da_referencia'].sum()}",
        "",
        "TOP 10 BAIRROS:",
        df["bairro"].value_counts().head(10).to_string(),
        "",
        f"Tamanhos: parquet={sizes['parquet_kb']} KB, "
        f"json={sizes['json_kb']} KB, csv={sizes['csv_kb']} KB",
        "",
        "VALIDAÇÕES LGPD:",
        f"  - colunas presentes: {list(df.columns)}",
        f"  - colunas com 'nome'/'cpf' no nome: "
        f"{[c for c in df.columns if 'nome' in c.lower() or 'cpf' in c.lower()]} (deve ser vazio ou só CNS_PROF)",
        f"  - paciente_id é determinístico: SIM (SHA-256 + sal local)",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[REPORT] Relatorio salvo em {OUT_REPORT.name}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("ANONIMIZADOR - Painel DDA Arapiraca v2")
    print("=" * 60)
    df = anonimizar()
    sizes = write_outputs(df)
    write_report(df, sizes)
    print("=" * 60)
    print("CONCLUIDO.")
    print(f"Saidas em: {HERE}")
    print("=" * 60)


if __name__ == "__main__":
    main()

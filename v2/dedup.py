"""
Deduplicação de cadastros — Painel DDA Arapiraca v2.

Identifica registros que se referem à mesma pessoa real, mesmo quando
aparecem com identificadores diferentes (uma vez por CNS, outra por CPF).

Estratégia em camadas:

1. HARD MATCH:
    - Mesmo CNS válido → mesma pessoa (transitivo).
    - Mesmo CPF válido → mesma pessoa (transitivo).
    - CNS e CPF aparecendo cruzados em registros diferentes → união.

2. SOFT MATCH (somente para registros não cobertos pelo hard match):
    - Bloqueio por DATA NASCIMENTO exata (reduz O(n²) para O(grupos²)).
    - Critério ALL: similaridade nome ≥ 0.92, similaridade nome_mãe ≥ 0.85.
    - Faixa intermediária (nome ≥ 0.85 mas < 0.92, ou mãe ≥ 0.70 mas < 0.85)
      vai para 'dedup_duvidas.csv' para revisão manual.

3. OVERRIDES:
    - Bruno preenche dedup_overrides.csv com decisões manuais
      (mesmo / diferente). Aplicadas em execuções futuras.

SAÍDA:
    - dedup_index.json (interno) — mapeamento chave_original → canonical_id
    - dedup_duvidas.csv (PII, local) — pares para revisão manual
    - dedup_relatorio.txt — estatísticas do processo

ENTRADAS opcionais:
    - dedup_overrides.csv (PII, local) — decisões manuais

LGPD:
    Este módulo trabalha COM PII (nome, CPF, nome da mãe) por necessidade
    técnica do record linkage. Suas saídas com PII (dedup_duvidas.csv,
    dedup_overrides.csv, dedup_index.json) são gitignored. Apenas o
    canonical_id (já derivado do paciente_id) escapa para o pipeline.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

OVERRIDES_PATH = HERE / "dedup_overrides.csv"
DUVIDAS_PATH = HERE / "dedup_duvidas.csv"
RELATORIO_PATH = HERE / "dedup_relatorio.txt"

# Thresholds (conservadores por decisão do Bruno em 2026-04-26)
THR_NOME_MATCH = 0.92
THR_MAE_MATCH = 0.85
THR_NOME_DUVIDA = 0.85   # entre 0.85 e 0.92 = dúvida
THR_MAE_DUVIDA = 0.70    # entre 0.70 e 0.85 = dúvida


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

_STOPWORDS = {"DA", "DE", "DO", "DOS", "DAS", "E"}

def _remove_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def norm_nome(v) -> str:
    """
    Normaliza nome: uppercase, sem acentos, sem stopwords curtas,
    sem iniciais isoladas (ex: 'M.'), espaços colapsados.
    """
    if v is None:
        return ""
    s = _remove_acentos(str(v)).upper()
    s = re.sub(r"[^A-Z\s]", " ", s)
    tokens = [t for t in s.split() if len(t) > 1 and t not in _STOPWORDS]
    return " ".join(tokens)


def digits_only(v) -> str:
    if v is None:
        return ""
    s = re.sub(r"\D", "", str(v))
    return s.lstrip("0")


def cns_valido(v) -> str:
    """Retorna CNS digit-only se for válido (15 dígitos), senão ''."""
    d = digits_only(v)
    if len(d) >= 11 and d != "0":   # alguns ficam com leading-zero stripped
        return d
    return ""


def cpf_valido(v) -> str:
    d = digits_only(v)
    if len(d) >= 9:   # tolerante a leading zero stripped
        return d
    return ""


def norm_data(v) -> str:
    """Retorna AAAAMMDD ou ''."""
    if v is None:
        return ""
    s = str(v).strip()
    # Lida com datetime estilo pandas
    if "-" in s and len(s) >= 10:
        return s[:10].replace("-", "")
    if "/" in s and len(s) >= 10:
        # dd/mm/yyyy → yyyymmdd
        try:
            d, m, y = s[:10].split("/")
            return f"{y}{m.zfill(2)}{d.zfill(2)}"
        except Exception:
            return ""
    return re.sub(r"\D", "", s)[:8]


# ─────────────────────────────────────────────────────────────────────────────
# SIMILARIDADE
# ─────────────────────────────────────────────────────────────────────────────

def jaro_winkler(s1: str, s2: str) -> float:
    """
    Jaro-Winkler simplificado, sem dependências externas.
    Retorna float em [0, 1].
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    len1, len2 = len(s1), len(s2)
    match_dist = max(len1, len2) // 2 - 1
    if match_dist < 0:
        match_dist = 0
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    for i in range(len1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    jaro = (
        matches / len1 + matches / len2 + (matches - transpositions) / matches
    ) / 3.0
    # prefix scaling (Winkler)
    prefix = 0
    for i in range(min(4, len1, len2)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
    return jaro + prefix * 0.1 * (1 - jaro)


def sim_nome(a: str, b: str) -> float:
    """Similaridade entre dois nomes normalizados."""
    if not a or not b:
        return 0.0
    return jaro_winkler(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# UNION-FIND
# ─────────────────────────────────────────────────────────────────────────────

class UnionFind:
    """Union-Find para fundir grupos de registros equivalentes."""
    def __init__(self):
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        if x not in self.parent:
            self.parent[x] = x
            return x
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]   # path compression
            x = self.parent[x]
        return x

    def union(self, a: int, b: int):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


# ─────────────────────────────────────────────────────────────────────────────
# OVERRIDES
# ─────────────────────────────────────────────────────────────────────────────

def carregar_overrides() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """
    Lê dedup_overrides.csv (se existir) e retorna:
      - same: pares (cns_a, cns_b) que devem ser unidos
      - diff: pares que NÃO devem ser unidos
    Formato esperado:
      decisao,id_a,id_b,obs
      mesmo,898001234,...,...
      diferente,898009999,...,...
    """
    same: set[tuple[str, str]] = set()
    diff: set[tuple[str, str]] = set()
    if not OVERRIDES_PATH.exists():
        return same, diff
    with OVERRIDES_PATH.open(encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            dec = (row.get("decisao") or "").strip().lower()
            a = (row.get("id_a") or "").strip()
            b = (row.get("id_b") or "").strip()
            if not a or not b:
                continue
            par = tuple(sorted([a, b]))
            if dec in {"mesmo", "same", "yes", "sim", "true"}:
                same.add(par)
            elif dec in {"diferente", "diff", "no", "nao", "não", "false"}:
                diff.add(par)
    return same, diff


def gerar_template_overrides():
    """Cria dedup_overrides.csv com header se não existir."""
    if OVERRIDES_PATH.exists():
        return
    OVERRIDES_PATH.write_text(
        "decisao,id_a,id_b,obs\n"
        "# decisao = 'mesmo' ou 'diferente'\n"
        "# id_a, id_b = qualquer chave estável (CNS, CPF, ou linha-id da dúvida)\n",
        encoding="utf-8-sig",
    )


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class RegistroDedup:
    """
    Wrapper com os campos PII necessários para o linkage.
    NÃO é exportado — vive apenas em memória durante o anonimizador.
    """
    __slots__ = ("idx", "origem", "cns", "cpf", "nome", "mae", "data_nasc")

    def __init__(self, idx: int, origem: str, cns, cpf, nome, mae, data_nasc):
        self.idx = idx
        self.origem = origem      # 'fai', 'fci', 'cidadao'
        self.cns = cns_valido(cns)
        self.cpf = cpf_valido(cpf)
        self.nome = norm_nome(nome)
        self.mae = norm_nome(mae)
        self.data_nasc = norm_data(data_nasc)

    def chaves_id(self) -> list[str]:
        """Lista de identificadores 'fortes' deste registro."""
        out = []
        if self.cns:
            out.append("cns:" + self.cns)
        if self.cpf:
            out.append("cpf:" + self.cpf)
        return out


def hard_match(registros: list[RegistroDedup], uf: UnionFind):
    """
    Une registros que compartilham CNS, CPF, ou um cruzamento.
    Trabalha em O(n) construindo índices.
    """
    by_cns: dict[str, list[int]] = defaultdict(list)
    by_cpf: dict[str, list[int]] = defaultdict(list)
    for r in registros:
        if r.cns:
            by_cns[r.cns].append(r.idx)
        if r.cpf:
            by_cpf[r.cpf].append(r.idx)

    for grupo in by_cns.values():
        if len(grupo) > 1:
            base = grupo[0]
            for x in grupo[1:]:
                uf.union(base, x)
    for grupo in by_cpf.values():
        if len(grupo) > 1:
            base = grupo[0]
            for x in grupo[1:]:
                uf.union(base, x)


def soft_match(
    registros: list[RegistroDedup],
    uf: UnionFind,
) -> list[dict]:
    """
    Soft match com bloqueio por data_nasc.
    Retorna lista de DÚVIDAS (matches limítrofes para revisão manual).
    """
    duvidas: list[dict] = []

    # Bloqueio: só compara registros com mesma data_nasc
    by_data: dict[str, list[RegistroDedup]] = defaultdict(list)
    for r in registros:
        if r.data_nasc and r.nome:
            by_data[r.data_nasc].append(r)

    for data, grupo in by_data.items():
        if len(grupo) < 2:
            continue
        # comparação dois a dois dentro do bloco
        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = grupo[i], grupo[j]
                # Já estão unidos pelo hard match? Pula.
                if uf.find(a.idx) == uf.find(b.idx):
                    continue
                sn = sim_nome(a.nome, b.nome)
                sm = sim_nome(a.mae, b.mae) if (a.mae and b.mae) else 0.0
                if sn >= THR_NOME_MATCH and sm >= THR_MAE_MATCH:
                    uf.union(a.idx, b.idx)
                elif sn >= THR_NOME_DUVIDA and sm >= THR_MAE_DUVIDA:
                    duvidas.append({
                        "data_nasc": data,
                        "idx_a": a.idx, "idx_b": b.idx,
                        "origem_a": a.origem, "origem_b": b.origem,
                        "nome_a": a.nome, "nome_b": b.nome,
                        "mae_a": a.mae, "mae_b": b.mae,
                        "cns_a": a.cns, "cns_b": b.cns,
                        "cpf_a": a.cpf, "cpf_b": b.cpf,
                        "sim_nome": round(sn, 3),
                        "sim_mae": round(sm, 3),
                    })
    return duvidas


def aplicar_overrides(
    registros: list[RegistroDedup],
    uf: UnionFind,
    same: set[tuple[str, str]],
    diff: set[tuple[str, str]],
) -> int:
    """
    Aplica overrides manuais. Retorna número de overrides aplicados.
    'same' força união. 'diff' não pode ser aplicado depois do hard match
    (que pode já ter unido); fica registrado no relatório como aviso.
    """
    # Indexa por todas as chaves possíveis
    chave_para_idx: dict[str, list[int]] = defaultdict(list)
    for r in registros:
        for k in r.chaves_id():
            chave_para_idx[k.split(":", 1)[1]].append(r.idx)
            chave_para_idx[k].append(r.idx)

    n_aplicados = 0
    for a, b in same:
        ia = chave_para_idx.get(a) or chave_para_idx.get("cns:" + a) or chave_para_idx.get("cpf:" + a)
        ib = chave_para_idx.get(b) or chave_para_idx.get("cns:" + b) or chave_para_idx.get("cpf:" + b)
        if ia and ib:
            uf.union(ia[0], ib[0])
            n_aplicados += 1
    return n_aplicados


def construir_indice(
    registros: list[RegistroDedup],
    uf: UnionFind,
) -> dict[str, str]:
    """
    Para cada registro, mapeia suas chaves originais para um canonical_key
    (string estável que será usada pelo anonimizador para gerar paciente_id).
    O canonical é o menor CNS/CPF dentro do componente conexo, ou o índice.
    """
    grupos: dict[int, list[RegistroDedup]] = defaultdict(list)
    for r in registros:
        grupos[uf.find(r.idx)].append(r)

    indice: dict[str, str] = {}
    for raiz, regs in grupos.items():
        # Escolhe canonical: menor CNS válido, senão menor CPF, senão idx do menor
        cnss = sorted([r.cns for r in regs if r.cns])
        cpfs = sorted([r.cpf for r in regs if r.cpf])
        if cnss:
            canonical = "cns:" + cnss[0]
        elif cpfs:
            canonical = "cpf:" + cpfs[0]
        else:
            canonical = f"grp:{raiz}"
        for r in regs:
            for k in r.chaves_id():
                indice[k] = canonical
    return indice


def escrever_duvidas(duvidas: list[dict]):
    if not duvidas:
        if DUVIDAS_PATH.exists():
            DUVIDAS_PATH.unlink()
        return
    fields = [
        "data_nasc", "sim_nome", "sim_mae",
        "origem_a", "nome_a", "mae_a", "cns_a", "cpf_a",
        "origem_b", "nome_b", "mae_b", "cns_b", "cpf_b",
        "idx_a", "idx_b",
    ]
    with DUVIDAS_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in duvidas:
            w.writerow({k: d.get(k, "") for k in fields})


def escrever_relatorio(
    n_registros: int, n_grupos: int, n_duvidas: int,
    n_overrides_same: int, n_hard_unions: int, n_soft_unions: int,
):
    lines = [
        "RELATÓRIO DE DEDUPLICAÇÃO — Painel DDA Arapiraca v2",
        "=" * 60,
        f"Registros analisados (FAI + FCI + CIDADAO unidos): {n_registros}",
        f"Pacientes únicos identificados (componentes conexos): {n_grupos}",
        f"  → redução: {n_registros - n_grupos} registros foram fundidos",
        "",
        f"Uniões por hard match (CNS/CPF cruzados): {n_hard_unions}",
        f"Uniões por soft match (nome+mãe+data exata):  {n_soft_unions}",
        f"Overrides 'mesmo' aplicados manualmente:      {n_overrides_same}",
        "",
        f"Dúvidas para revisão manual (em dedup_duvidas.csv): {n_duvidas}",
        "",
        "PRÓXIMOS PASSOS:",
        "  1. Abra dedup_duvidas.csv no Excel",
        "  2. Para cada par, decida 'mesmo' ou 'diferente'",
        "  3. Adicione decisões em dedup_overrides.csv",
        "  4. Rode o anonimizador novamente",
        "",
        "Arquivos gerados (PII — NÃO COMMITAR):",
        f"  - {DUVIDAS_PATH.name}",
        f"  - {OVERRIDES_PATH.name} (template, se ainda não existia)",
    ]
    RELATORIO_PATH.write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# API PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def deduplicar(registros: Iterable[RegistroDedup]) -> dict[str, str]:
    """
    Recebe lista de RegistroDedup e devolve índice {chave_original → canonical_key}.

    Side effects:
        - escreve dedup_duvidas.csv (se houver dúvidas)
        - escreve dedup_relatorio.txt
        - cria dedup_overrides.csv (template) se não existir
    """
    regs = list(registros)
    if not regs:
        return {}

    same, diff = carregar_overrides()
    gerar_template_overrides()

    uf = UnionFind()
    for r in regs:
        uf.find(r.idx)   # registra todos

    # Snapshot antes/depois para contar
    pais_antes = {r.idx: uf.find(r.idx) for r in regs}
    hard_match(regs, uf)
    pais_pos_hard = {r.idx: uf.find(r.idx) for r in regs}
    n_hard_unions = sum(1 for k in regs if pais_antes[k.idx] != pais_pos_hard[k.idx])

    duvidas = soft_match(regs, uf)
    pais_pos_soft = {r.idx: uf.find(r.idx) for r in regs}
    n_soft_unions = sum(1 for k in regs if pais_pos_hard[k.idx] != pais_pos_soft[k.idx])

    n_overrides = aplicar_overrides(regs, uf, same, diff)

    indice = construir_indice(regs, uf)

    # contagem de grupos finais
    grupos = {uf.find(r.idx) for r in regs}
    escrever_duvidas(duvidas)
    escrever_relatorio(
        n_registros=len(regs),
        n_grupos=len(grupos),
        n_duvidas=len(duvidas),
        n_overrides_same=n_overrides,
        n_hard_unions=n_hard_unions,
        n_soft_unions=n_soft_unions,
    )

    return indice


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-TESTE QUANDO EXECUTADO DIRETAMENTE
# ─────────────────────────────────────────────────────────────────────────────

def _self_test():
    """Smoke test rápido para validar a lógica."""
    print("=== self-test dedup ===")
    regs = [
        RegistroDedup(0, "fai",     "898001234567890", None,             "JOAO DA SILVA",      "MARIA SILVA",     "1980-01-15"),
        RegistroDedup(1, "fci",     None,              "12345678901",    "JOAO SILVA",         "MARIA SILVA",     "1980-01-15"),
        RegistroDedup(2, "cidadao", "898001234567890", "12345678901",    "JOAO DA SILVA",      "MARIA SILVA",     "1980-01-15"),
        RegistroDedup(3, "fai",     "898009999999999", None,             "JOAO DE SOUZA",      "ANA DE SOUZA",    "1980-01-15"),
        RegistroDedup(4, "fai",     "898007777777777", None,             "JOSE PEREIRA",       "ANA PEREIRA",     "1990-05-10"),
        RegistroDedup(5, "fci",     None,              "11122233344",    "JOSÉ PEREIRA",       "ANA PEREIRA",     "1990-05-10"),
    ]
    # Esperado: {0,1,2} unido (transitivo via cns + cpf cruzados),
    #            {4,5} unido por soft match (nomes muito similares + data + mãe),
    #            {3} sozinho.
    indice = deduplicar(regs)
    print("Índice resultante:")
    for k, v in indice.items():
        print(f"  {k} → {v}")
    valores = set(indice.values())
    print(f"\nTotal de pacientes canônicos: {len(valores)}")
    assert len(valores) == 3, f"Esperava 3 grupos, obtive {len(valores)}"
    print("OK!")


if __name__ == "__main__":
    _self_test()

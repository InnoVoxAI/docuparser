#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discovery_spike.py — Spike de descoberta (READ-ONLY) da API Condomínios (Superlógica).

Fase B do estudo DocuParse × Superlógica. Objetivo: converter os [HIP] do §7 da Fase A
em fato e TESTAR a regra de associação documento↔condomínio ANTES de firmá-la.

⚠️  Este script é DESCARTÁVEL e 100% READ-ONLY: só emite GET (guarda rígida no cliente).
    O que persiste é o relatório de achados, não o script.

Uso rápido:
    export SL_APP_TOKEN=...   SL_ACCESS_TOKEN=...
    python discovery_spike.py --self-test               # checagem offline (não bate na API)
    python discovery_spike.py                            # fases 0..3 (descoberta)
    python discovery_spike.py --sample amostra.json      # inclui a fase 4 (regra de associação)

Ver README-discovery-spike.md para pré-requisitos, formato da amostra e saídas.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Optional

# ------------------------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------------------------
BASE_URL_DEFAULT = "https://api.superlogica.net/v2"

# Controllers candidatos (Fase A §3) — TODOS [HIP]; o spike confirma quais existem.
CANDIDATE_CONTROLLERS = [
    "condominios", "unidades", "condominos", "contatosunidade",
    "fornecedores", "despesas", "cobrancas", "planodecontas", "notafiscal",
]

# Params candidatos para filtro server-side por CNPJ (Fase B task 2.1).
CANDIDATE_CNPJ_FILTER_PARAMS = ["CNPJ", "cnpj", "pesquisa", "busca", "ST_CGC_CON", "ST_CNPJ_CON"]

# Params candidatos de paginação/itens (Fase B task 2.2; nomes da v1 [IND]).
CANDIDATE_PERPAGE_PARAMS = ["itensPorPagina", "limit", "porPagina"]

# Nomes de campo podem ser sobrescritos se a heurística errar (escape hatch).
FIELD_CNPJ_OVERRIDE = os.getenv("SL_FIELD_CNPJ")   # ex.: ST_CGC_CON
FIELD_ID_OVERRIDE = os.getenv("SL_FIELD_ID")       # ex.: id_condominio_cond

logger = logging.getLogger("spike")


# ------------------------------------------------------------------------------------
# Utilidades PURAS (testáveis offline via --self-test; não dependem de httpx)
# ------------------------------------------------------------------------------------
def only_digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s if s is not None else ""))


def normalize_cnpj(s: Any) -> Optional[str]:
    d = only_digits(s)
    return d if len(d) == 14 else None


def is_valid_cnpj(s: Any) -> bool:
    """Valida os dois dígitos verificadores do CNPJ (numérico)."""
    d = only_digits(s)
    if len(d) != 14 or d == d[0] * 14:
        return False

    def _dv(nums: str, weights: list[int]) -> str:
        total = sum(int(n) * w for n, w in zip(nums, weights))
        r = total % 11
        return "0" if r < 2 else str(11 - r)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    d1 = _dv(d[:12], w1)
    d2 = _dv(d[:12] + d1, w2)
    return d[12:] == d1 + d2


def mask_cnpj(s: Any) -> str:
    d = only_digits(s)
    if len(d) != 14:
        return "***"
    return f"{d[:2]}.***.***/****-{d[12:]}"


def mask_cpf(s: Any) -> str:
    d = only_digits(s)
    if len(d) != 11:
        return "***"
    return f"{d[:3]}.***.***-{d[9:]}"


def looks_like_cnpj(v: Any) -> bool:
    return bool(re.fullmatch(r"\D*\d{14}\D*", str(v if v is not None else "")))


def looks_like_cpf(v: Any) -> bool:
    return bool(re.fullmatch(r"\D*\d{11}\D*", str(v if v is not None else "")))


def mask_pii_in_record(record: dict) -> dict:
    out = {}
    for k, v in record.items():
        if looks_like_cnpj(v):
            out[k] = mask_cnpj(v)
        elif looks_like_cpf(v):
            out[k] = mask_cpf(v)
        else:
            out[k] = v
    return out


def find_fields_by_value(record: dict, predicate: Callable[[Any], bool]) -> list[str]:
    """Retorna os NOMES de campo cujo VALOR satisfaz o predicado.
    Base da task 1.3: descobrir EM QUAL coluna a API guarda o CNPJ — não o valor."""
    return [k for k, v in record.items() if predicate(v)]


def guess_cnpj_field(records: list[dict]) -> Optional[str]:
    """Descobre o NOME do campo de CNPJ do condomínio na resposta da API."""
    if FIELD_CNPJ_OVERRIDE:
        return FIELD_CNPJ_OVERRIDE
    c: Counter = Counter()
    for r in records:
        for k in find_fields_by_value(r, looks_like_cnpj):
            c[k] += 1
    return c.most_common(1)[0][0] if c else None


def guess_id_field(records: list[dict]) -> Optional[str]:
    """Heurística: chave que começa com 'id' e cujo valor é numérico."""
    if FIELD_ID_OVERRIDE:
        return FIELD_ID_OVERRIDE
    c: Counter = Counter()
    for r in records:
        for k, v in r.items():
            if re.match(r"(?i)^id[_a-z]*$", str(k)) and only_digits(v):
                c[k] += 1
    return c.most_common(1)[0][0] if c else None


def extract_records(body: Any) -> list[dict]:
    """Normaliza a resposta em lista de registros, seja qual for o envelope."""
    if isinstance(body, list):
        return [r for r in body if isinstance(r, dict)]
    if isinstance(body, dict):
        for key in ("data", "records", "result", "results", "items"):
            v = body.get(key)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        if body and all(str(k).isdigit() for k in body.keys()):
            return [v for v in body.values() if isinstance(v, dict)]
        return [body] if body else []
    return []


def detect_pagination(body: Any) -> dict:
    hints = {}
    if isinstance(body, dict):
        for k in body.keys():
            if re.search(r"(?i)(pagina|page|total|itens|count|registros)", str(k)):
                hints[str(k)] = body[k]
    return hints


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


# ------------------------------------------------------------------------------------
# Cliente HTTP READ-ONLY (guarda rígida: só GET)
# ------------------------------------------------------------------------------------
class ReadOnlyClient:
    """Envelope sobre httpx que só expõe GET. Qualquer outro método levanta erro."""

    def __init__(self, headers: dict, timeout: float = 30.0):
        import httpx  # import tardio: --self-test não precisa da lib
        self._client = httpx.Client(headers=headers, timeout=timeout, follow_redirects=True)
        self.call_log: list[dict] = []

    def get(self, url: str, params: Optional[dict] = None):
        return self._request("GET", url, params=params)

    def _request(self, method: str, url: str, params=None):
        if method.upper() != "GET":
            raise RuntimeError(f"Spike é READ-ONLY: método {method} bloqueado.")
        started = time.perf_counter()
        try:
            return self._client.request("GET", url, params=params)
        finally:
            self.call_log.append(
                {"url": url, "ms": round((time.perf_counter() - started) * 1000, 1)}
            )
            logger.info("GET %s %s", url, params or "")

    def close(self):
        self._client.close()


def safe_json(resp) -> Any:
    try:
        return resp.json()
    except Exception:
        return None


@dataclass
class Config:
    base_url: str
    app_token: str
    access_token: str
    timeout: float = 30.0
    out_dir: Path = Path("achados_out")
    max_pages: int = 5


def build_headers(app_token: str, access_token: str) -> dict:
    return {"Content-Type": "application/json", "app_token": app_token, "access_token": access_token}


def make_client(cfg: Config, bad_auth: bool = False) -> ReadOnlyClient:
    at = cfg.app_token if not bad_auth else "INVALID_TOKEN"
    ac = cfg.access_token if not bad_auth else "INVALID_TOKEN"
    return ReadOnlyClient(build_headers(at, ac), timeout=cfg.timeout)


# ------------------------------------------------------------------------------------
# Sonda primitiva e busca de registros
# ------------------------------------------------------------------------------------
def probe(client: ReadOnlyClient, base_url: str, controller: str, params: Optional[dict] = None) -> dict:
    url = f"{base_url}/condor/{controller}"
    finding: dict = {
        "controller": controller, "url": url, "params": params or {},
        "http_status": None, "body_status": None, "exists": None,
        "num_records": 0, "fields": [], "sample": None,
        "pagination_hint": {}, "error": None,
    }
    try:
        resp = client.get(url, params=params)
        finding["http_status"] = resp.status_code
        body = safe_json(resp)
        if isinstance(body, dict):
            finding["body_status"] = body.get("status")
        records = extract_records(body)
        finding["num_records"] = len(records)
        finding["pagination_hint"] = detect_pagination(body)
        if records:
            finding["fields"] = sorted(records[0].keys())
            finding["sample"] = mask_pii_in_record(records[0])
        finding["exists"] = bool(resp.status_code == 200 and (records or body is not None))
    except Exception as e:  # noqa: BLE001
        finding["error"] = repr(e)
    return finding


def fetch_records(client: ReadOnlyClient, cfg: Config, controller: str,
                  want: int = 25, extra_params: Optional[dict] = None) -> list[dict]:
    """Busca registros REAIS (não mascarados) para heurística/índice. Nunca são gravados crus."""
    params = {"itensPorPagina": want}
    if extra_params:
        params.update(extra_params)
    body = None
    try:
        resp = client.get(f"{cfg.base_url}/condor/{controller}", params=params)
        body = safe_json(resp)
    except Exception as e:  # noqa: BLE001
        logger.warning("falha ao buscar %s: %r", controller, e)
    return extract_records(body)


# ------------------------------------------------------------------------------------
# Fase 0 — autenticação & modelo de erro  (§7.4)
# ------------------------------------------------------------------------------------
def phase0_auth_errors(client: ReadOnlyClient, cfg: Config) -> dict:
    logger.info("== Fase 0: auth & modelo de erro ==")
    out: dict = {}
    valid = probe(client, cfg.base_url, "condominios", params={"itensPorPagina": 1})
    out["chamada_valida"] = {
        "http_status": valid["http_status"], "body_status": valid["body_status"],
        "autenticou": valid["http_status"] not in (401, 403) and valid["error"] is None,
    }
    bad = make_client(cfg, bad_auth=True)
    try:
        binv = probe(bad, cfg.base_url, "condominios", params={"itensPorPagina": 1})
    finally:
        bad.close()
    out["token_invalido"] = {
        "http_status": binv["http_status"], "body_status": binv["body_status"],
        "erro_via": ("http_status" if (binv["http_status"] or 0) >= 400
                     else "envelope_no_corpo" if binv["body_status"] else "indeterminado"),
    }
    nx = probe(client, cfg.base_url, "__endpoint_inexistente__")
    out["path_inexistente"] = {"http_status": nx["http_status"], "body_status": nx["body_status"]}
    out["nota"] = ("Tokens vão no header a cada requisição -> stateless por natureza. "
                   "Expiração NÃO é verificável numa execução única (precisa observação ao longo do tempo).")
    return out


# ------------------------------------------------------------------------------------
# Fase 1 — endpoints & campos  (§7.1, §7.2-campo, §7.8)
# ------------------------------------------------------------------------------------
def phase1_endpoints(client: ReadOnlyClient, cfg: Config, controllers: Optional[list] = None) -> dict:
    logger.info("== Fase 1: descoberta de endpoints & campos ==")
    endpoints: dict = {}
    condominio_records: list[dict] = []
    for ctrl in (controllers or CANDIDATE_CONTROLLERS):
        endpoints[ctrl] = probe(client, cfg.base_url, ctrl, params={"itensPorPagina": 5})
        if ctrl == "condominios":
            condominio_records = fetch_records(client, cfg, ctrl, want=25)
    return {
        "endpoints": endpoints,
        "campo_cnpj_condominio": guess_cnpj_field(condominio_records),   # NOME do campo (task 1.3)
        "campo_id_condominio": guess_id_field(condominio_records),
        "nota_campos": "Nomes descobertos por heurística; conferir via inspeção do tráfego do ERP.",
    }


# ------------------------------------------------------------------------------------
# Fase 2 — filtro, paginação, lote, data  (§7.2-filtro, §7.5, §7.6, §7.7)
# ------------------------------------------------------------------------------------
def _detect_date_formats(records: list[dict]) -> dict:
    pat_iso = re.compile(r"^\d{4}-\d{2}-\d{2}")
    pat_br = re.compile(r"^\d{2}/\d{2}/\d{4}")
    found = {"iso_yyyy_mm_dd": 0, "com_barra_dd_ou_mm": 0, "exemplos": []}
    for r in records:
        for v in r.values():
            s = str(v if v is not None else "")
            if pat_iso.match(s):
                found["iso_yyyy_mm_dd"] += 1
            elif pat_br.match(s):
                found["com_barra_dd_ou_mm"] += 1
            else:
                continue
            if len(found["exemplos"]) < 5:
                found["exemplos"].append(s[:10])
    found["nota"] = ("Formato com barra NÃO distingue DD/MM de MM/DD só na leitura; "
                     "confirmar com teste ativo se houver filtro de data.")
    return found


def _probe_rate_limit(client: ReadOnlyClient, cfg: Config, n: int = 8) -> dict:
    logger.info("sonda de rate limit (burst pequeno, n=%d)", n)
    statuses: list = []
    headers_seen: dict = {}
    for _ in range(n):
        try:
            resp = client.get(f"{cfg.base_url}/condor/condominios", params={"itensPorPagina": 1})
            statuses.append(resp.status_code)
            for h in resp.headers:
                if re.search(r"(?i)rate|limit|remaining|retry", h):
                    headers_seen[h] = resp.headers[h]
            if resp.status_code == 429:
                break
        except Exception as e:  # noqa: BLE001
            statuses.append(f"ERR:{e!r}")
    return {
        "status_codes": statuses, "headers_rate": headers_seen,
        "hit_429": 429 in [s for s in statuses if isinstance(s, int)],
        "nota": "Burst deliberadamente pequeno. Limite real não é público; throttle conservador na integração.",
    }


def phase2_mechanics(client: ReadOnlyClient, cfg: Config, cnpj_field: Optional[str]) -> dict:
    logger.info("== Fase 2: filtro, paginação, lote, data ==")
    out: dict = {"filtro_cnpj": {}, "paginacao": {}, "data": {}, "rate_limit": {}, "lote": {}}

    base_records = fetch_records(client, cfg, "condominios", want=50)
    baseline_n = len(base_records)
    out["paginacao"]["baseline_num_registros"] = baseline_n

    # 2.1 filtro server-side por CNPJ (usa um CNPJ real dos próprios registros)
    known_cnpj = None
    if cnpj_field:
        for r in base_records:
            c = normalize_cnpj(r.get(cnpj_field))
            if c:
                known_cnpj = c
                break
    if known_cnpj:
        for p in CANDIDATE_CNPJ_FILTER_PARAMS:
            recs = fetch_records(client, cfg, "condominios", want=50, extra_params={p: known_cnpj})
            out["filtro_cnpj"][p] = {"num": len(recs), "estreitou": 0 < len(recs) < baseline_n}
        achou = any(v.get("estreitou") for v in out["filtro_cnpj"].values() if isinstance(v, dict))
        out["filtro_cnpj"]["conclusao"] = (
            "Existe filtro server-side por CNPJ" if achou
            else "SEM filtro server-side -> sincronização local da carteira é OBRIGATÓRIA"
        )
    else:
        out["filtro_cnpj"]["conclusao"] = "Não testado (sem CNPJ conhecido / campo não identificado)"

    # 2.2 paginação
    for pp in CANDIDATE_PERPAGE_PARAMS:
        one = fetch_records(client, cfg, "condominios", want=1, extra_params={pp: 1})
        out["paginacao"][f"{pp}=1"] = {"num": len(one), "respeitou_limite": len(one) == 1}

    # 2.4 data (leitura)
    out["data"]["formatos_observados"] = _detect_date_formats(base_records)

    # 2.5 rate limit (burst pequeno)
    out["rate_limit"] = _probe_rate_limit(client, cfg, n=8)

    # 2.3 lote (padrão v1 era POST -> deferido para modo de escrita)
    out["lote"] = {"nota": "Padrão 'params[]' da v1 era POST; confirmação de lote fica p/ modo de escrita (deferido)."}
    return out


# ------------------------------------------------------------------------------------
# Fase 3 — anexos (read-only)  (§7.3)
# ------------------------------------------------------------------------------------
def _value_shape(v: Any) -> str:
    s = str(v if v is not None else "")
    if re.match(r"(?i)^https?://", s):
        return "url"
    if len(s) > 200 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", s):
        return "provavelmente_base64"
    if s and only_digits(s) == s:
        return "id_numerico"
    return f"outro(len={len(s)})"


def phase3_attachments(client: ReadOnlyClient, cfg: Config) -> dict:
    logger.info("== Fase 3: sonda de anexos (read-only) ==")
    recs = fetch_records(client, cfg, "despesas", want=50)
    key_pat = re.compile(r"(?i)(anexo|arquivo|documento|boleto|nota|pdf|url|link)")
    suspects: dict = {}
    for r in recs:
        for k, v in r.items():
            if key_pat.search(str(k)):
                suspects.setdefault(str(k), _value_shape(v))
    out = {
        "num_despesas_amostradas": len(recs),
        "campos_suspeitos_anexo": suspects,
        "conclusao": ("Há campo(s) candidato(s) a anexo na LEITURA; confirmar formato (URL/base64/id)."
                      if suspects else
                      "Nenhum campo óbvio de anexo nas despesas amostradas (ou nenhuma com anexo). Ver ERP."),
        "nota_escrita": ("Confirmar se a despesa ACEITA anexo (e em que formato) só se resolve escrevendo "
                         "-> passo autorizado à parte."),
    }
    return out


# ------------------------------------------------------------------------------------
# Fase 4 — ⭐ validação da regra de associação  (§7 ⭐ / §5)
# ------------------------------------------------------------------------------------
def _build_condominio_index(client: ReadOnlyClient, cfg: Config,
                            cnpj_field: str, id_field: Optional[str]) -> dict:
    index: dict = {}
    page = 1
    per = 200
    for _ in range(cfg.max_pages):
        recs = fetch_records(client, cfg, "condominios", want=per, extra_params={"pagina": page})
        if not recs:
            break
        for r in recs:
            cnpj = normalize_cnpj(r.get(cnpj_field))
            if not cnpj:
                continue
            index[cnpj] = {"id": (r.get(id_field) if id_field else None)}  # 'raw' fica fora do disco
        if len(recs) < per:
            break
        page += 1
    return index


def _association_metrics(c: dict) -> dict:
    total = c["total"] or 1
    com_gabarito = c["correto"] + c["errado"]
    return {
        "cobertura_match_%": round(100 * c["casou"] / total, 1),
        "precisao_%": (round(100 * c["correto"] / com_gabarito, 1) if com_gabarito else None),
        "sem_cnpj_%": round(100 * c["sem_cnpj"] / total, 1),
        "cnpj_invalido_%": round(100 * c["cnpj_invalido"] / total, 1),
        "sem_match_%": round(100 * c["sem_match"] / total, 1),
        "errado_%": round(100 * c["errado"] / total, 1),
    }


def _go_no_go_text(m: dict) -> str:
    prec = m.get("precisao_%")
    if prec is None:
        return ("SEM GABARITO suficiente: a amostra não trouxe 'condominio_esperado_id'. "
                "Dá p/ medir COBERTURA, mas não PRECISÃO. Rotule a amostra para decidir go/no-go.")
    return (
        f"Precisão do match (correto entre os que casaram): {prec}%. "
        f"Cobertura (casaram por CNPJ): {m['cobertura_match_%']}%. "
        f"Associações ERRADAS (condomínio errado): {m['errado_%']}% — este é o número de risco financeiro/jurídico. "
        "O LIMIAR de auto-confirmação × revisão humana é decisão humana (H5). "
        "Se 'errado_%' > 0, trate como bloqueador até entender caso a caso."
    )


def phase4_association(client: ReadOnlyClient, cfg: Config,
                       cnpj_field: Optional[str], id_field: Optional[str], sample_path: Path) -> dict:
    logger.info("== Fase 4 ⭐: validação da regra de associação ==")
    if not cnpj_field:
        return {"erro": "Campo de CNPJ do condomínio não identificado (Fase 1). "
                        "Defina SL_FIELD_CNPJ e rode de novo."}
    index = _build_condominio_index(client, cfg, cnpj_field, id_field)
    sample = json.loads(Path(sample_path).read_text(encoding="utf-8"))

    rows: list[dict] = []
    c = {"total": 0, "sem_cnpj": 0, "cnpj_invalido": 0, "casou": 0,
         "correto": 0, "errado": 0, "sem_match": 0}
    for doc in sample:
        c["total"] += 1
        raw = doc.get("cnpj_papel_condominio")
        cnpj = normalize_cnpj(raw)
        esperado = str(doc.get("condominio_esperado_id") or "").strip()
        row = {"doc_id": doc.get("doc_id"), "tipo": doc.get("tipo"),
               "cnpj_extraido": mask_cnpj(raw), "condominio_casado_id": None,
               "condominio_esperado_id": esperado, "resultado": None}
        if not cnpj:
            c["sem_cnpj"] += 1
            row["resultado"] = "sem_cnpj"
        elif not is_valid_cnpj(cnpj):
            c["cnpj_invalido"] += 1
            row["resultado"] = "cnpj_invalido"
        else:
            hit = index.get(cnpj)
            if not hit:
                c["sem_match"] += 1
                row["resultado"] = "sem_match_no_cadastro"
            else:
                c["casou"] += 1
                row["condominio_casado_id"] = hit["id"]
                if hit["id"] is None:
                    row["resultado"] = "casou_mas_id_field_desconhecido"
                elif esperado and str(hit["id"]) == esperado:
                    c["correto"] += 1
                    row["resultado"] = "correto"
                elif esperado:
                    c["errado"] += 1
                    row["resultado"] = "ERRADO"
                else:
                    row["resultado"] = "casou_sem_gabarito"
        rows.append(row)

    metrics = _association_metrics(c)
    return {"index_size": len(index), "counters": c, "metrics": metrics,
            "rows": rows, "go_no_go": _go_no_go_text(metrics)}


# ------------------------------------------------------------------------------------
# Fase 5 — relatórios
# ------------------------------------------------------------------------------------
def _dig(d: Any, *keys) -> Any:
    for k in keys:
        d = d.get(k) if isinstance(d, dict) else None
    return d


def write_reports(findings: dict, cfg: Config) -> None:
    (cfg.out_dir / "achados.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_achados_csv(findings, cfg)
    _write_associacao_csv(findings, cfg)
    (cfg.out_dir / "RELATORIO-ACHADOS.md").write_text(_build_report_md(findings), encoding="utf-8")


def _write_achados_csv(findings: dict, cfg: Config) -> None:
    eps = _dig(findings, "fase1_endpoints", "endpoints") or {}
    with (cfg.out_dir / "achados.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["controller", "http_status", "exists", "num_records", "num_fields", "error"])
        for ctrl, f in eps.items():
            w.writerow([ctrl, f.get("http_status"), f.get("exists"),
                        f.get("num_records"), len(f.get("fields") or []), f.get("error")])


def _write_associacao_csv(findings: dict, cfg: Config) -> None:
    rows = _dig(findings, "fase4_associacao", "rows")
    if not rows:
        return
    cols = ["doc_id", "tipo", "cnpj_extraido", "condominio_casado_id",
            "condominio_esperado_id", "resultado"]
    with (cfg.out_dir / "associacao.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _build_report_md(f: dict) -> str:
    L: list[str] = []
    L.append("# RELATÓRIO DE ACHADOS — spike de descoberta (Fase B)\n")
    L.append(f"_Gerado em {f.get('gerado_em', '?')} · base_url `{f.get('base_url', '?')}` · modo: {f.get('modo', '?')}_\n")
    L.append("> Reescreve os `[HIP]` do **§7 da Fase A** em fato. Cada seção mapeia um item daquele §7.\n")

    f0 = f.get("fase0_auth_erro")
    if f0:
        L.append("## §7.4 — Autenticação e modelo de erro")
        L.append(f"- Chamada válida: HTTP `{_dig(f0, 'chamada_valida', 'http_status')}`, "
                 f"autenticou: `{_dig(f0, 'chamada_valida', 'autenticou')}`.")
        L.append(f"- Token inválido: HTTP `{_dig(f0, 'token_invalido', 'http_status')}`, "
                 f"erro via `{_dig(f0, 'token_invalido', 'erro_via')}`.")
        L.append(f"- Path inexistente: HTTP `{_dig(f0, 'path_inexistente', 'http_status')}`.")
        L.append(f"- {f0.get('nota', '')}\n")

    f1 = f.get("fase1_endpoints")
    if f1:
        L.append("## §7.1 / §7.8 — Endpoints e campos")
        L.append("| controller | existe | HTTP | nº campos |")
        L.append("|---|---|---|---|")
        for ctrl, ff in (f1.get("endpoints") or {}).items():
            L.append(f"| `{ctrl}` | {ff.get('exists')} | {ff.get('http_status')} | {len(ff.get('fields') or [])} |")
        L.append(f"\n**Campo de CNPJ do condomínio (nome):** `{f1.get('campo_cnpj_condominio')}` · "
                 f"**Campo de id:** `{f1.get('campo_id_condominio')}`  \n_{f1.get('nota_campos', '')}_\n")

    f2 = f.get("fase2_mecanica")
    if f2:
        L.append("## §7.2 / §7.5 / §7.6 / §7.7 — Filtro, paginação, lote, data")
        L.append(f"- **Filtro por CNPJ:** {_dig(f2, 'filtro_cnpj', 'conclusao')}")
        L.append(f"- **Paginação (baseline):** {_dig(f2, 'paginacao', 'baseline_num_registros')} registros.")
        L.append(f"- **Data (formatos observados):** {_dig(f2, 'data', 'formatos_observados')}")
        L.append(f"- **Rate limit:** hit 429 = {_dig(f2, 'rate_limit', 'hit_429')}; "
                 f"{_dig(f2, 'rate_limit', 'nota')}")
        L.append(f"- **Lote:** {_dig(f2, 'lote', 'nota')}\n")

    f3 = f.get("fase3_anexos")
    if f3:
        L.append("## §7.3 — Anexos")
        L.append(f"- {f3.get('conclusao', '(não rodado)')}")
        if f3.get("campos_suspeitos_anexo"):
            L.append(f"- Campos candidatos: `{f3['campos_suspeitos_anexo']}`")
        L.append(f"- {f3.get('nota_escrita', '')}\n")

    L.append("## ⭐ Regra de associação (§5 / §7 ⭐)")
    f4 = f.get("fase4_associacao")
    if not f4:
        L.append("- _Não rodada (rode com `--sample amostra.json`)._\n")
    elif f4.get("erro"):
        L.append(f"- ⚠️ {f4['erro']}\n")
    else:
        L.append(f"- Índice de condomínios: {f4.get('index_size')} entradas.")
        L.append(f"- Métricas: `{f4.get('metrics')}`")
        L.append(f"- **Go/No-Go:** {f4.get('go_no_go')}\n")

    L.append("---\n_Próximo: usar estes achados para atualizar `[HIP]→[DOC]` na Fase A "
             "e alimentar o `Specify` da Fase C._")
    return "\n".join(L)


# ------------------------------------------------------------------------------------
# Self-test offline (funções puras) — não bate na API
# ------------------------------------------------------------------------------------
def run_self_test() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        print(("PASS" if cond else "FAIL"), "-", name)
        ok = ok and cond

    check("cnpj válido (11.222.333/0001-81)", is_valid_cnpj("11.222.333/0001-81"))
    check("cnpj inválido (DV errado)", not is_valid_cnpj("11.222.333/0001-80"))
    check("cnpj repetido é inválido", not is_valid_cnpj("00000000000000"))
    check("normalize_cnpj", normalize_cnpj("11.222.333/0001-81") == "11222333000181")
    check("mask esconde o meio", mask_cnpj("11222333000181") == "11.***.***/****-81")

    rec = {"ST_NOME_CON": "Cond X", "ST_CGC_CON": "11222333000181",
           "ID_COND": "42", "CPF": "12345678901"}
    check("acha o NOME do campo de CNPJ", guess_cnpj_field([rec]) == "ST_CGC_CON")
    check("mascara PII no registro", mask_pii_in_record(rec)["ST_CGC_CON"].startswith("11."))
    check("mascara CPF no registro", mask_pii_in_record(rec)["CPF"].startswith("123."))
    check("extract_records lista", extract_records([rec]) == [rec])
    check("extract_records envelope data", extract_records({"data": [rec]}) == [rec])
    check("extract_records numerado", extract_records({"0": rec}) == [rec])

    c = {"total": 10, "sem_cnpj": 1, "cnpj_invalido": 0, "casou": 8,
         "correto": 7, "errado": 1, "sem_match": 1}
    m = _association_metrics(c)
    check("precisão = 7/8 = 87.5%", m["precisao_%"] == 87.5)
    check("cobertura = 8/10 = 80.0%", m["cobertura_match_%"] == 80.0)

    print("\nRESULTADO:", "TODOS PASSARAM ✅" if ok else "HOUVE FALHAS ❌")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Spike de descoberta READ-ONLY da API Condomínios (Superlógica).")
    p.add_argument("--phases", default="0,1,2,3",
                   help="fases a rodar, ex.: '0,1,2,3' ou '0,1'. A fase 4 requer --sample.")
    p.add_argument("--sample", type=Path, help="JSON com amostra rotulada (habilita a Fase 4).")
    p.add_argument("--out", type=Path, default=Path("achados_out"), help="diretório de saída.")
    p.add_argument("--base-url", default=os.getenv("SL_BASE_URL", BASE_URL_DEFAULT))
    p.add_argument("--timeout", type=float, default=float(os.getenv("SL_TIMEOUT", "30")))
    p.add_argument("--max-pages", type=int, default=int(os.getenv("SL_MAX_PAGES", "5")))
    p.add_argument("--test-mode", action="store_true",
                   help="modo de teste: avalia SOMENTE o endpoint 'condominios' (smoke check). Pula a Fase 3.")
    p.add_argument("--self-test", action="store_true",
                   help="roda checagens offline das funções puras e sai (não bate na API).")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s")

    if args.self_test:
        return run_self_test()

    app_token = os.getenv("SL_APP_TOKEN")
    access_token = os.getenv("SL_ACCESS_TOKEN")
    if not app_token or not access_token:
        print("ERRO: defina SL_APP_TOKEN e SL_ACCESS_TOKEN no ambiente. Ver README.", file=sys.stderr)
        return 2

    cfg = Config(base_url=args.base_url.rstrip("/"), app_token=app_token, access_token=access_token,
                 timeout=args.timeout, out_dir=args.out, max_pages=args.max_pages)
    cfg.out_dir.mkdir(parents=True, exist_ok=True)

    phases = {x.strip() for x in args.phases.split(",") if x.strip()}
    test_mode = args.test_mode
    controllers = ["condominios"] if test_mode else CANDIDATE_CONTROLLERS
    client = make_client(cfg)
    findings: dict = {
        "base_url": cfg.base_url,
        "gerado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modo": "teste (somente condominios)" if test_mode else "completo",
    }
    if test_mode:
        logger.info("MODO DE TESTE: avaliando somente 'condominios' (Fase 3 pulada).")
    cnpj_field = id_field = None
    try:
        if "0" in phases:
            findings["fase0_auth_erro"] = phase0_auth_errors(client, cfg)
        if "1" in phases:
            f1 = phase1_endpoints(client, cfg, controllers)
            findings["fase1_endpoints"] = f1
            cnpj_field = f1.get("campo_cnpj_condominio")
            id_field = f1.get("campo_id_condominio")
        if "2" in phases:
            findings["fase2_mecanica"] = phase2_mechanics(client, cfg, cnpj_field)
        if "3" in phases and not test_mode:
            findings["fase3_anexos"] = phase3_attachments(client, cfg)
        if args.sample:
            findings["fase4_associacao"] = phase4_association(client, cfg, cnpj_field, id_field, args.sample)
    finally:
        client.close()

    write_reports(findings, cfg)
    print(f"OK — achados gravados em: {cfg.out_dir}/")
    print(f"     Leia primeiro: {cfg.out_dir / 'RELATORIO-ACHADOS.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

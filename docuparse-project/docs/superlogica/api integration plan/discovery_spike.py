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

# Parâmetros OBRIGATÓRIOS por controller. Sem eles a API responde 403 com
# "Id do condomínio não informado" e o controller pareceria inexistente.
# 'todos' é o coringa aceito por condominios para devolver a carteira inteira.
CONTROLLER_REQUIRED_PARAMS: dict[str, dict] = {
    "condominios": {"id": "todos"},
}

# Quando um controller reclama de parâmetro faltando, estes candidatos são
# testados em ordem até um responder 200. O que funcionar entra no achado.
# `{cond_id}` é substituído pelo id de condomínio já descoberto, quando houver.
CANDIDATE_REQUIRED_PARAMS: list[dict] = [
    {"id": "todos"},
    {"idCondominio": "todos"},
    {"idCondominio": "{cond_id}"},
    {"id": "{cond_id}"},
    {"ID_CONDOMINIO_COND": "{cond_id}"},
]

# Sinais, na mensagem de erro, de que faltou parâmetro (≠ endpoint inexistente).
_MISSING_PARAM_HINTS = ("não informado", "nao informado", "obrigat", "informe ", "não informada")

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


# Campos cujo NOME indica credencial. O cadastro de condomínio da v2 traz
# st_apptoken_usu / st_accesstoken_usu / st_senha_usu: gravá-los na amostra
# colocaria credenciais em disco (fere RI-002 e RI-004).
SECRET_FIELD_RE = re.compile(r"(?i)(token|senha|password|passwd|secret|chave|api[_-]?key|md5)")


def looks_like_secret_field(name: Any) -> bool:
    return bool(SECRET_FIELD_RE.search(str(name)))


def mask_pii_in_record(record: dict) -> dict:
    out = {}
    for k, v in record.items():
        # Nome de campo tem precedência sobre valor: um campo de token com valor
        # curto não seria pego por nenhuma heurística de formato.
        if looks_like_secret_field(k):
            out[k] = "" if not str(v or "").strip() else "***REDACTED***"
        elif looks_like_cnpj(v):
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


def guess_id_field(records: list[dict], entidade: str = "condominio") -> Optional[str]:
    """Descobre o NOME do campo identificador da própria entidade.

    Contar ocorrências não basta: um registro de condomínio traz uma dúzia de
    campos `id_*` numéricos (plano de contas, tipo de cobrança, CNAE…), todos
    empatados. Escolher o errado corromperia o índice da Fase 4 em silêncio —
    o CNPJ casaria, mas o id comparado com o gabarito seria de outra entidade.
    Por isso a escolha é por PONTUAÇÃO, priorizando o campo que nomeia a
    própria entidade (convenção `id_<entidade>_<sufixo>` da API).
    """
    if FIELD_ID_OVERRIDE:
        return FIELD_ID_OVERRIDE
    ent = str(entidade or "").lower().rstrip("s")
    candidatos: dict[str, int] = {}
    valores: dict[str, set] = {}
    for r in records:
        for k, v in r.items():
            nome = str(k).lower()
            if not re.match(r"(?i)^id[_a-z]*$", nome) or not only_digits(v):
                continue
            score = 1
            if ent and re.match(rf"^id_{re.escape(ent)}", nome):
                score = 100        # id_condominio_* -> é o id da própria entidade
            elif ent and ent in nome:
                score = 10         # cita a entidade em outra posição
            candidatos[k] = max(candidatos.get(k, 0), score)
            valores.setdefault(k, set()).add(str(v))
    if not candidatos:
        return None
    # Desempate: id de verdade é único por registro; um FK repete entre registros.
    def chave(k: str):
        return (candidatos[k], len(valores[k]))
    return max(candidatos, key=chave)


def _unwrap_single_key(records: list[dict]) -> list[dict]:
    """Desembrulha envelopes do tipo [{'condominio': [{...}]}] em [{...}].

    A v2 aninha a entidade sob uma chave com o nome dela. Sem desembrulhar, o
    achado reportaria 1 registro com um único "campo" chamado `condominio`, e a
    heurística de nome de CNPJ (e o índice da Fase 4) não achariam nada.
    """
    out: list[dict] = []
    mudou = False
    for r in records:
        if isinstance(r, dict) and len(r) == 1:
            v = next(iter(r.values()))
            if isinstance(v, dict) and v:
                out.append(v)
                mudou = True
                continue
            if isinstance(v, list) and v and all(isinstance(i, dict) for i in v):
                out.extend(v)
                mudou = True
                continue
        out.append(r)
    # Envelopes podem ser aninhados em mais de um nível; repete até estabilizar.
    return _unwrap_single_key(out) if mudou else out


def extract_records(body: Any) -> list[dict]:
    """Normaliza a resposta em lista de registros, seja qual for o envelope."""
    records: list[dict]
    if isinstance(body, list):
        records = [r for r in body if isinstance(r, dict)]
    elif isinstance(body, dict):
        for key in ("data", "records", "result", "results", "items"):
            v = body.get(key)
            if isinstance(v, list):
                records = [r for r in v if isinstance(r, dict)]
                break
        else:
            if body and all(str(k).isdigit() for k in body.keys()):
                records = [v for v in body.values() if isinstance(v, dict)]
            else:
                records = [body] if body else []
    else:
        return []
    return _unwrap_single_key(records)


# Chaves que a API usa para devolver erro DENTRO do corpo. 'status' é o padrão da v1
# (>=100 = erro); 'msg' é o que o backend v2 usa junto de um HTTP 5xx.
BODY_ERROR_KEYS = ("msg", "mensagem", "erro", "error", "message")


def detect_body_error(body: Any, http_status: Optional[int] = None) -> Optional[dict]:
    """Detecta erro sinalizado no corpo da resposta, não pelo status HTTP.

    Devolve {'campo': <nome>, 'valor': <conteúdo>} ou None. Existe porque o erro
    pode chegar por três caminhos: status HTTP, envelope no corpo, ou os dois —
    e um envelope de erro NÃO pode ser confundido com um registro de dados.
    """
    if not isinstance(body, dict):
        return None
    # Padrão v1: campo 'status' numérico onde >=100 significa erro.
    st = body.get("status")
    if st is not None:
        try:
            if int(st) >= 100:
                return {"campo": "status", "valor": st}
        except (TypeError, ValueError):
            pass
    # Padrão v2 observado: corpo só com uma chave de mensagem, sob HTTP 4xx/5xx.
    for k in BODY_ERROR_KEYS:
        if k in body and isinstance(body[k], str) and body[k].strip():
            # Só é erro se o corpo não parece um registro de dados: ou o HTTP já
            # falhou, ou a mensagem é a única coisa que veio.
            if (http_status or 0) >= 400 or len(body) == 1:
                return {"campo": k, "valor": body[k]}
    return None


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
def looks_like_missing_param(body_error: Optional[dict]) -> bool:
    """A mensagem indica parâmetro obrigatório faltando (≠ endpoint inexistente)?"""
    if not body_error:
        return False
    txt = str(body_error.get("valor", "")).lower()
    return any(h in txt for h in _MISSING_PARAM_HINTS)


def merge_required_params(controller: str, params: Optional[dict]) -> dict:
    """Junta os params pedidos aos obrigatórios conhecidos daquele controller."""
    out = dict(CONTROLLER_REQUIRED_PARAMS.get(controller) or {})
    out.update(params or {})
    return out


def probe(client: ReadOnlyClient, base_url: str, controller: str, params: Optional[dict] = None) -> dict:
    url = f"{base_url}/condor/{controller}"
    params = merge_required_params(controller, params)
    finding: dict = {
        "controller": controller, "url": url, "params": params or {},
        "http_status": None, "body_status": None, "body_error": None, "exists": None,
        "requer_param": False, "num_records": 0, "fields": [], "sample": None,
        "pagination_hint": {}, "error": None,
    }
    try:
        resp = client.get(url, params=params)
        finding["http_status"] = resp.status_code
        body = safe_json(resp)
        if isinstance(body, dict):
            finding["body_status"] = body.get("status")
        finding["body_error"] = detect_body_error(body, resp.status_code)
        finding["pagination_hint"] = detect_pagination(body)
        if finding["body_error"]:
            # Envelope de erro não é dado: não vira registro nem campo descoberto,
            # senão 'msg' entraria no relatório como se fosse coluna da entidade.
            finding["requer_param"] = looks_like_missing_param(finding["body_error"])
            # Reclamar de parâmetro faltando PROVA que o controller existe —
            # marcar como inexistente aqui seria um falso negativo do §7.1.
            finding["exists"] = True if finding["requer_param"] else False
        else:
            records = extract_records(body)
            finding["num_records"] = len(records)
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
    params = merge_required_params(controller, {"itensPorPagina": want})
    if extra_params:
        params.update(extra_params)
    body = None
    try:
        resp = client.get(f"{cfg.base_url}/condor/{controller}", params=params)
        body = safe_json(resp)
        err = detect_body_error(body, resp.status_code)
        if err:
            # Sem isto, o envelope de erro viraria "registro" e envenenaria a
            # heurística de nome de campo e o índice da Fase 4.
            logger.warning("%s respondeu erro no corpo (%s); descartando", controller, err["campo"])
            return []
    except Exception as e:  # noqa: BLE001
        logger.warning("falha ao buscar %s: %r", controller, e)
    return extract_records(body)


# ------------------------------------------------------------------------------------
# Fase 0 — autenticação & modelo de erro  (§7.4)
# ------------------------------------------------------------------------------------
def _erro_via(finding: dict) -> str:
    """Por onde o erro chega: status HTTP, envelope no corpo, os dois, ou nenhum."""
    via_http = (finding["http_status"] or 0) >= 400
    via_body = bool(finding["body_error"]) or bool(finding["body_status"])
    if via_http and via_body:
        return "http_status+envelope_no_corpo"
    if via_http:
        return "http_status"
    if via_body:
        return "envelope_no_corpo"
    return "indeterminado"


# Termos que, numa mensagem de erro do corpo, indicam recusa de credencial —
# e não uma falha genérica do servidor.
_AUTH_DENIED_HINTS = ("permiss", "token", "autoriz", "unauthor", "forbidden", "credencial", "licen")


def phase0_auth_errors(client: ReadOnlyClient, cfg: Config) -> dict:
    logger.info("== Fase 0: auth & modelo de erro ==")
    out: dict = {}
    valid = probe(client, cfg.base_url, "condominios", params={"itensPorPagina": 1})
    # 'autenticou' é tri-estado de propósito: um HTTP 500 com "permissão negada"
    # no corpo não é autenticação bem-sucedida, mas também não é o 401 clássico.
    autenticou: Optional[bool]
    motivo = None
    body_err_txt = str((valid["body_error"] or {}).get("valor", "")).lower()
    if valid["error"] is not None:
        autenticou, motivo = None, "requisição não completou (erro de transporte)"
    elif any(h in body_err_txt for h in _AUTH_DENIED_HINTS):
        autenticou, motivo = False, "credencial recusada por mensagem no corpo, apesar do status HTTP"
    elif looks_like_missing_param(valid["body_error"]):
        # 403 por parâmetro faltando NÃO é recusa de credencial: para o endpoint
        # reclamar do parâmetro, a credencial já passou pelo gateway.
        autenticou, motivo = True, "endpoint respondeu reclamando de parâmetro — credencial passou"
    elif valid["http_status"] == 401:
        autenticou, motivo = False, "credencial rejeitada pelo status HTTP"
    elif valid["http_status"] == 200 and not valid["body_error"]:
        autenticou, motivo = True, "chamada válida retornou dados"
    else:
        autenticou, motivo = None, "resposta não permite concluir (nem dados, nem recusa explícita)"
    out["chamada_valida"] = {
        "http_status": valid["http_status"], "body_status": valid["body_status"],
        "body_error": valid["body_error"], "autenticou": autenticou, "motivo": motivo,
        "erro_via": _erro_via(valid),
    }
    bad = make_client(cfg, bad_auth=True)
    try:
        binv = probe(bad, cfg.base_url, "condominios", params={"itensPorPagina": 1})
    finally:
        bad.close()
    out["token_invalido"] = {
        "http_status": binv["http_status"], "body_status": binv["body_status"],
        "body_error": binv["body_error"], "erro_via": _erro_via(binv),
    }
    nx = probe(client, cfg.base_url, "__endpoint_inexistente__")
    out["path_inexistente"] = {
        "http_status": nx["http_status"], "body_status": nx["body_status"],
        "body_error": nx["body_error"], "erro_via": _erro_via(nx),
    }
    out["nota"] = ("Tokens vão no header a cada requisição -> stateless por natureza. "
                   "Expiração NÃO é verificável numa execução única (precisa observação ao longo do tempo).")
    return out


# ------------------------------------------------------------------------------------
# Fase 1 — endpoints & campos  (§7.1, §7.2-campo, §7.8)
# ------------------------------------------------------------------------------------
def _discover_required_params(client: ReadOnlyClient, cfg: Config, controller: str,
                              cond_id: Optional[str]) -> Optional[dict]:
    """Testa candidatos de parâmetro obrigatório até um responder com dados.

    Roda só quando o controller reclamou de parâmetro faltando — logo, existe.
    Devolve o conjunto de params que funcionou, ou None.
    """
    for cand in CANDIDATE_REQUIRED_PARAMS:
        if any("{cond_id}" in str(v) for v in cand.values()) and not cond_id:
            continue  # candidato depende de um id que ainda não temos
        p = {k: str(v).replace("{cond_id}", str(cond_id or "")) for k, v in cand.items()}
        f = probe(client, cfg.base_url, controller, params={**p, "itensPorPagina": 5})
        if f["http_status"] == 200 and not f["body_error"] and f["num_records"]:
            logger.info("  %s: parâmetro obrigatório descoberto -> %s", controller, p)
            return p
    return None


def phase1_endpoints(client: ReadOnlyClient, cfg: Config, controllers: Optional[list] = None) -> dict:
    logger.info("== Fase 1: descoberta de endpoints & campos ==")
    endpoints: dict = {}
    condominio_records: list[dict] = []
    params_descobertos: dict = {}
    cond_id: Optional[str] = None
    for ctrl in (controllers or CANDIDATE_CONTROLLERS):
        endpoints[ctrl] = probe(client, cfg.base_url, ctrl, params={"itensPorPagina": 5})
        if endpoints[ctrl].get("requer_param"):
            achado = _discover_required_params(client, cfg, ctrl, cond_id)
            if achado:
                params_descobertos[ctrl] = achado
                CONTROLLER_REQUIRED_PARAMS.setdefault(ctrl, {}).update(achado)
                endpoints[ctrl] = probe(client, cfg.base_url, ctrl, params={"itensPorPagina": 5})
        if ctrl == "condominios":
            condominio_records = fetch_records(client, cfg, ctrl, want=25)
            # Guarda um id real: outros controllers costumam exigi-lo.
            id_field = FIELD_ID_OVERRIDE or guess_id_field(condominio_records)
            if condominio_records and id_field:
                cond_id = str(condominio_records[0].get(id_field) or "") or None
    return {
        "endpoints": endpoints,
        "campo_cnpj_condominio": guess_cnpj_field(condominio_records),   # NOME do campo (task 1.3)
        "campo_id_condominio": guess_id_field(condominio_records),
        "params_obrigatorios_descobertos": params_descobertos,
        "condominio_id_usado_nas_sondas": cond_id,
        "nota_campos": ("Nomes descobertos por heurística; conferir via inspeção do tráfego do "
                        "ERP. `campo_cnpj_condominio` é a CHAVE DE BUSCA (recebe o CNPJ vindo do "
                        "documento); `campo_id_condominio` é a RESPOSTA (identificador do "
                        "condomínio no ERP, comparado com o gabarito da amostra)."),
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
            resp = client.get(f"{cfg.base_url}/condor/condominios",
                              params=merge_required_params("condominios", {"itensPorPagina": 1}))
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
        if achou:
            out["filtro_cnpj"]["conclusao"] = "Existe filtro server-side por CNPJ"
        elif baseline_n < 2:
            # Com 1 condomínio na carteira, filtrar não tem como "estreitar" nada:
            # com ou sem filtro o resultado é o mesmo. Concluir "sem filtro" aqui
            # seria falsa confiança numa das decisões mais caras da Fase C.
            out["filtro_cnpj"]["conclusao"] = (
                f"NÃO CONCLUSIVO — carteira com {baseline_n} condomínio(s) visível(is): "
                "um filtro não teria como estreitar o resultado. Repetir com carteira de 2+."
            )
        else:
            out["filtro_cnpj"]["conclusao"] = (
                "SEM filtro server-side -> sincronização local da carteira é OBRIGATÓRIA")
    else:
        out["filtro_cnpj"]["conclusao"] = "Não testado (sem CNPJ conhecido / campo não identificado)"

    # 2.2 paginação
    for pp in CANDIDATE_PERPAGE_PARAMS:
        one = fetch_records(client, cfg, "condominios", want=1, extra_params={pp: 1})
        out["paginacao"][f"{pp}=1"] = {"num": len(one), "respeitou_limite": len(one) == 1}
    if baseline_n < 2:
        out["paginacao"]["nota"] = (
            f"Baseline de {baseline_n} registro(s): 'respeitou_limite' é trivialmente "
            "verdadeiro e NÃO prova que o parâmetro de paginação funciona.")

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
        w.writerow(["controller", "http_status", "exists", "num_records", "num_fields",
                    "body_error", "error"])
        for ctrl, f in eps.items():
            be = (f.get("body_error") or {}).get("valor")
            w.writerow([ctrl, f.get("http_status"), f.get("exists"),
                        f.get("num_records"), len(f.get("fields") or []), be, f.get("error")])


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
                 f"autenticou: `{_dig(f0, 'chamada_valida', 'autenticou')}` "
                 f"({_dig(f0, 'chamada_valida', 'motivo')}); "
                 f"erro via `{_dig(f0, 'chamada_valida', 'erro_via')}`.")
        for rotulo, chave in (("Chamada válida", "chamada_valida"),
                              ("Token inválido", "token_invalido"),
                              ("Path inexistente", "path_inexistente")):
            be = _dig(f0, chave, "body_error")
            if be:
                L.append(f"  - {rotulo} — erro no corpo (`{be.get('campo')}`): `{be.get('valor')}`")
        L.append(f"- Token inválido: HTTP `{_dig(f0, 'token_invalido', 'http_status')}`, "
                 f"erro via `{_dig(f0, 'token_invalido', 'erro_via')}`.")
        L.append(f"- Path inexistente: HTTP `{_dig(f0, 'path_inexistente', 'http_status')}`, "
                 f"erro via `{_dig(f0, 'path_inexistente', 'erro_via')}`.")
        L.append(f"- {f0.get('nota', '')}\n")

    f1 = f.get("fase1_endpoints")
    if f1:
        L.append("## §7.1 / §7.8 — Endpoints e campos")
        L.append("| controller | existe | HTTP | nº campos | erro no corpo |")
        L.append("|---|---|---|---|---|")
        for ctrl, ff in (f1.get("endpoints") or {}).items():
            be = (ff.get("body_error") or {}).get("valor") or ""
            L.append(f"| `{ctrl}` | {ff.get('exists')} | {ff.get('http_status')} | "
                     f"{len(ff.get('fields') or [])} | {be} |")
        cnpj_f = f1.get("campo_cnpj_condominio")
        id_f = f1.get("campo_id_condominio")
        L.append("\n### Os dois campos que sustentam a associação\n")
        L.append("São pontas opostas da mesma operação — não confundir:\n")
        L.append("| | Campo | Papel | Origem do valor |")
        L.append("|---|---|---|---|")
        L.append(f"| 🔑 **Chave de busca** | `{cnpj_f}` | Onde o cadastro guarda o **CNPJ** do "
                 "condomínio. É por ele que se **procura** | O valor vem de fora: é o CNPJ "
                 "extraído do documento pelo DocuParse |")
        L.append(f"| 🎯 **Resposta** | `{id_f}` | **Identificador** do condomínio dentro do ERP. "
                 "É o que se **obtém** do match | O valor vem do próprio ERP |")
        L.append("\nA Fase 4 monta o índice `{%s normalizado → %s}`: entra com o CNPJ do "
                 "documento, sai com o identificador do condomínio.\n" % (cnpj_f, id_f))
        L.append(f"O `condominio_esperado_id` da amostra rotulada é um **`{id_f}`**, nunca um "
                 "CNPJ — e o gabarito NÃO pode ser montado casando CNPJ, sob pena de gerar a "
                 "resposta com a mesma chave que está sendo testada.\n")
        L.append(f"_{f1.get('nota_campos', '')}_\n")

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

    # Modelo de erro: envelope no corpo não pode passar por registro de dados.
    err_v2 = {"msg": "Permissão ao access_token negada. Detalhe: abc licenca123"}
    check("detecta erro no corpo via 'msg' (HTTP 5xx)",
          (detect_body_error(err_v2, 500) or {}).get("campo") == "msg")
    check("detecta erro no corpo via 'status' >=100 (padrão v1)",
          (detect_body_error({"status": 101, "msg": "x"}, 200) or {}).get("campo") == "status")
    check("registro legítimo não vira erro", detect_body_error(rec, 200) is None)

    # Envelope aninhado da v2: [{'condominio': [{...}]}] tem que virar [{...}].
    check("desembrulha envelope aninhado da entidade",
          extract_records([{"condominio": [rec]}]) == [rec])
    check("desembrulha envelope de nível duplo",
          extract_records([{"a": {"b": rec}}]) == [rec])
    check("parâmetro obrigatório é distinguido de endpoint inexistente",
          looks_like_missing_param({"campo": "msg", "valor": "Id do condomínio não informado."})
          and not looks_like_missing_param({"campo": "msg", "valor": "Não encontrado."}))
    check("params obrigatórios do controller entram na requisição",
          merge_required_params("condominios", {"itensPorPagina": 5}) ==
          {"id": "todos", "itensPorPagina": 5})

    # Campos de credencial não podem ser gravados na amostra (RI-002 / RI-004).
    seg = {"st_apptoken_usu": "abc123", "st_senha_usu": "s3nh4",
           "st_accesstoken_usu": "", "st_nome_cond": "COND X"}
    msk = mask_pii_in_record(seg)
    check("mascara campo de token pelo NOME", msk["st_apptoken_usu"] == "***REDACTED***")
    check("mascara campo de senha pelo NOME", msk["st_senha_usu"] == "***REDACTED***")
    check("campo de credencial vazio continua vazio", msk["st_accesstoken_usu"] == "")
    check("campo comum não é redigido", msk["st_nome_cond"] == "COND X")

    # O id da entidade tem que ganhar dos vários FKs numéricos do registro.
    cond = {"id_planoconta_plc": "8", "id_tipocobranca_tco": "1",
            "id_condominio_cond": "7", "id_cnae_cnae": "1157", "st_nome_cond": "X"}
    check("escolhe o id da própria entidade, não um FK",
          guess_id_field([cond], "condominios") == "id_condominio_cond")
    check("id continua achável sem pista de entidade",
          guess_id_field([{"id_x_y": "3"}], "") == "id_x_y")

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

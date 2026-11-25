"""O escritor só faz a escrita permitida, nunca reenvia sozinho e nunca vaza segredo."""

from __future__ import annotations

import logging

import pytest
import requests

from erp_export.errors import ExportError
from erp_export.writer import ALLOWED_WRITES, SuperlogicaWriter, WriteNotAllowed

from .helpers import FakeResponse, FakeSession

APP_TOKEN = "app-token-secreto"
ACCESS_TOKEN = "access-token-secreto"
BODY = {"campo": "valor-do-corpo-secreto"}


def writer(session: FakeSession) -> SuperlogicaWriter:
    return SuperlogicaWriter(
        APP_TOKEN, ACCESS_TOKEN, "https://sandbox.erp.test/v2/condor", session=session
    )


def test_only_one_write_is_allowed():
    assert ALLOWED_WRITES == frozenset({("POST", "despesas")})


@pytest.mark.parametrize(
    "path", ["fornecedores", "condominios/get", "despesas/cancelar", ""]
)
def test_any_other_path_is_refused_before_touching_the_network(path):
    session = FakeSession()
    with pytest.raises(WriteNotAllowed):
        writer(session).post(path, BODY)
    assert session.calls == []


def test_successful_post_returns_the_expense_id():
    session = FakeSession({("POST", "despesas"): [{"id_despesa_des": "9001"}]})
    result = writer(session).post("despesas", BODY)
    assert result.external_id == "9001"
    assert session.methods() == ["POST"]
    assert session.calls[0]["json"] == BODY


def test_id_is_found_inside_a_data_envelope():
    session = FakeSession({("POST", "despesas"): {"data": [{"id_despesa_des": 55}]}})
    assert writer(session).post("despesas", BODY).external_id == "55"


def test_success_without_a_readable_id_is_retryable_and_flagged_unknown():
    session = FakeSession({("POST", "despesas"): FakeResponse(200, {"ok": True})})
    with pytest.raises(ExportError) as raised:
        writer(session).post("despesas", BODY)
    assert raised.value.code == "unexpected_response"
    assert raised.value.outcome_unknown is True
    assert raised.value.retryable is True


@pytest.mark.parametrize("status", [401, 403])
def test_auth_rejection_is_not_retryable(status):
    session = FakeSession({("POST", "despesas"): FakeResponse(status, {})})
    with pytest.raises(ExportError) as raised:
        writer(session).post("despesas", BODY)
    assert raised.value.code == "auth_rejected"
    assert raised.value.retryable is False


@pytest.mark.parametrize("status", [400, 404, 422])
def test_validation_rejection_is_not_retryable_and_the_outcome_is_known(status):
    session = FakeSession({("POST", "despesas"): FakeResponse(status, {"x": 1})})
    with pytest.raises(ExportError) as raised:
        writer(session).post("despesas", BODY)
    assert raised.value.code == "erp_rejected"
    assert raised.value.retryable is False
    assert raised.value.outcome_unknown is False


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_server_trouble_is_retryable_with_unknown_outcome(status):
    session = FakeSession({("POST", "despesas"): FakeResponse(status, {})})
    with pytest.raises(ExportError) as raised:
        writer(session).post("despesas", BODY)
    assert raised.value.retryable is True
    assert raised.value.outcome_unknown is True


def test_network_failure_is_retryable_with_unknown_outcome():
    session = FakeSession(
        {("POST", "despesas"): requests.ConnectTimeout("tempo esgotado")}
    )
    with pytest.raises(ExportError) as raised:
        writer(session).post("despesas", BODY)
    assert raised.value.code == "network_error"
    assert raised.value.retryable is True
    assert raised.value.outcome_unknown is True


def test_a_failed_post_is_never_repeated_by_the_writer():
    session = FakeSession({("POST", "despesas"): FakeResponse(503, {})})
    with pytest.raises(ExportError):
        writer(session).post("despesas", BODY)
    assert len(session.posts()) == 1


def test_default_session_has_no_retrying_adapter():
    # Sem sessão injetada, o POST também não pode ser reenviado pela biblioteca.
    real = SuperlogicaWriter("a", "b", "https://sandbox.erp.test/v2/condor")
    adapter = real._session.get_adapter("https://sandbox.erp.test")
    assert adapter.max_retries.total == 0


def test_neither_logs_nor_errors_expose_tokens_or_body(caplog):
    caplog.set_level(logging.DEBUG)
    cases = [
        FakeResponse(200, [{"id_despesa_des": "1"}]),
        FakeResponse(422, {"detalhe": BODY["campo"]}),
        FakeResponse(503, {"detalhe": BODY["campo"]}),
        FakeResponse(401, {}),
        requests.ConnectionError(f"falha com {ACCESS_TOKEN} e {BODY['campo']}"),
    ]
    messages = []
    for case in cases:
        session = FakeSession({("POST", "despesas"): case})
        try:
            writer(session).post("despesas", BODY)
        except ExportError as error:
            messages.append(str(error))
    everything = "\n".join([caplog.text, *messages])
    for secret in (APP_TOKEN, ACCESS_TOKEN, BODY["campo"]):
        assert secret not in everything


def test_tokens_travel_only_in_headers_never_in_the_url_or_body():
    session = FakeSession({("POST", "despesas"): [{"id_despesa_des": "1"}]})
    writer(session).post("despesas", BODY)
    assert session.headers["app_token"] == APP_TOKEN
    assert session.headers["access_token"] == ACCESS_TOKEN
    call = session.calls[0]
    assert APP_TOKEN not in call["url"] and ACCESS_TOKEN not in call["url"]
    assert APP_TOKEN not in str(call["json"])


def test_the_conftest_blocks_any_real_http_call():
    real = requests.Session()
    with pytest.raises(AssertionError, match="bloqueada"):
        real.get("https://api.superlogica.net/v2/condor/despesas")

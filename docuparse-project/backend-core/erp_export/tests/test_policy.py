"""A política decide se pode haver envio ao ERP. Todo padrão deve ser o mais seguro."""

from __future__ import annotations

from documents.models import IntegrationSettings

from erp_export.policy import (
    DEFAULT_PRODUCTION_URL,
    LIVE_WRITES_ENV,
    SANDBOX_HOSTS_ENV,
    confirmation_required,
    evaluate_policy,
)

Mode = IntegrationSettings.SuperlogicaMode
SANDBOX_URL = "https://sandbox.erp.test/v2/condor"
LIVE_ENV = {LIVE_WRITES_ENV: "1"}


def cfg(mode, **kw) -> IntegrationSettings:
    return IntegrationSettings(superlogica_mode=mode, **kw)


def test_new_settings_default_to_the_safest_values():
    config = IntegrationSettings()
    assert config.superlogica_mode == Mode.DISABLED
    assert config.superlogica_dry_run is True
    assert config.superlogica_live_enabled is False


def test_disabled_and_mock_never_send():
    for mode in (Mode.DISABLED, Mode.MOCK):
        policy = evaluate_policy(cfg(mode, superlogica_dry_run=False), environ={})
        assert policy.send_allowed is False
        assert policy.blocked_reason == ""


def test_dry_run_never_sends_even_when_everything_else_allows_it():
    policy = evaluate_policy(
        cfg(Mode.SANDBOX, superlogica_base_url=SANDBOX_URL, superlogica_dry_run=True),
        environ={SANDBOX_HOSTS_ENV: "sandbox.erp.test"},
    )
    assert policy.dry_run is True
    assert policy.send_allowed is False


def test_sandbox_sends_only_to_an_allowlisted_host():
    config = cfg(
        Mode.SANDBOX, superlogica_base_url=SANDBOX_URL, superlogica_dry_run=False
    )
    allowed = evaluate_policy(config, environ={SANDBOX_HOSTS_ENV: "sandbox.erp.test"})
    assert allowed.send_allowed is True
    assert allowed.blocked_reason == ""

    # Lista vazia (padrão): nenhum host é autorizado.
    refused = evaluate_policy(config, environ={})
    assert refused.send_allowed is False
    assert SANDBOX_HOSTS_ENV in refused.blocked_reason

    other = evaluate_policy(config, environ={SANDBOX_HOSTS_ENV: "outro.host"})
    assert other.send_allowed is False


def test_sandbox_never_points_to_production_even_if_allowlisted():
    config = cfg(
        Mode.SANDBOX,
        superlogica_base_url=DEFAULT_PRODUCTION_URL,
        superlogica_dry_run=False,
    )
    policy = evaluate_policy(config, environ={SANDBOX_HOSTS_ENV: "api.superlogica.net"})
    assert policy.send_allowed is False
    assert "produção" in policy.blocked_reason


def test_sandbox_without_url_is_blocked():
    policy = evaluate_policy(cfg(Mode.SANDBOX, superlogica_dry_run=False), environ={})
    assert policy.send_allowed is False
    assert "URL" in policy.blocked_reason


def test_live_needs_all_four_conditions():
    base = dict(superlogica_dry_run=False, superlogica_live_enabled=True)
    ok = evaluate_policy(
        cfg(Mode.LIVE, **base), environ=LIVE_ENV, contract_verified=True
    )
    assert ok.send_allowed is True
    assert ok.base_url == DEFAULT_PRODUCTION_URL

    cases = {
        "tenant não habilitado": (
            cfg(Mode.LIVE, superlogica_dry_run=False, superlogica_live_enabled=False),
            LIVE_ENV,
            True,
        ),
        "servidor desligado": (cfg(Mode.LIVE, **base), {}, True),
        "contrato não verificado": (cfg(Mode.LIVE, **base), LIVE_ENV, False),
        "host que não é produção": (
            cfg(Mode.LIVE, superlogica_base_url="https://outro.host/v2", **base),
            LIVE_ENV,
            True,
        ),
    }
    for name, (config, environ, verified) in cases.items():
        policy = evaluate_policy(config, environ=environ, contract_verified=verified)
        assert policy.send_allowed is False, name
        assert policy.blocked_reason, name


def test_live_is_blocked_by_default_because_the_contract_is_unverified():
    # Sem sobrescrever `contract_verified`, vale a constante do código (False).
    config = cfg(Mode.LIVE, superlogica_dry_run=False, superlogica_live_enabled=True)
    policy = evaluate_policy(config, environ=LIVE_ENV)
    assert policy.send_allowed is False
    assert "contrato" in policy.blocked_reason


def test_confirmation_is_required_only_when_something_can_be_sent():
    assert confirmation_required(cfg(Mode.SANDBOX)) is True
    assert confirmation_required(cfg(Mode.LIVE)) is True
    assert confirmation_required(cfg(Mode.MOCK)) is False
    assert confirmation_required(cfg(Mode.DISABLED)) is False

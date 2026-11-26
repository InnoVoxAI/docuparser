"""Tolerância de relógio na validação do JWT (SIMPLE_JWT["LEEWAY"])."""

from __future__ import annotations

from datetime import timedelta

import pytest
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.utils import aware_utcnow


def _token_issued_in(offset: timedelta) -> str:
    token = AccessToken()
    token.set_iat(at_time=aware_utcnow() + offset)
    return str(token)


def test_token_from_a_clock_a_few_seconds_ahead_is_accepted() -> None:
    # Quem emitiu tinha o relógio adiantado (ou este voltou numa ressincronização).
    AccessToken(_token_issued_in(timedelta(seconds=10)))


def test_token_issued_well_in_the_future_is_still_refused() -> None:
    with pytest.raises(TokenError):
        AccessToken(_token_issued_in(timedelta(minutes=5)))

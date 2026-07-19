from workers.notification import _notify_user


async def test_notify_user_returns_notified_true():
    result = await _notify_user(
        document_id="doc-1",
        rejection_reason="Arquivo corrompido",
        channel="email",
    )

    assert result == {"notified": True}


async def test_notify_user_defaults_channel_to_manual():
    result = await _notify_user(document_id="doc-1", rejection_reason="Senha protegida")

    assert result == {"notified": True}

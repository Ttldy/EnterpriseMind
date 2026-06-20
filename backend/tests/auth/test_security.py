from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_plaintext() -> None:
    encoded = hash_password("Passw0rd!")

    assert encoded != "Passw0rd!"
    assert verify_password(
        "Passw0rd!",
        encoded,
    )
    assert not verify_password(
        "wrong",
        encoded,
    )


def test_access_token_round_trip() -> None:
    token = create_access_token(42)

    assert decode_access_token(token) == 42

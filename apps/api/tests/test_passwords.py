"""Argon2id password hashing tests."""

from app.security import Argon2PasswordHasher


def test_argon2id_hashes_use_unique_salts_and_verify_safely() -> None:
    hasher = Argon2PasswordHasher()
    password = "A-Secure-Test-Password-42!"

    first_hash = hasher.hash(password)
    second_hash = hasher.hash(password)

    assert first_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert second_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert first_hash != second_hash
    assert hasher.verify(first_hash, password)
    assert hasher.verify(second_hash, password)
    assert not hasher.verify(first_hash, "Wrong-Test-Password-42!")
    assert password not in first_hash

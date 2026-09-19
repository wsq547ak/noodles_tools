from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000


def hash_password(password: str, *, iterations: int = DEFAULT_ITERATIONS) -> str:
    if not password:
        raise ValueError("密码不能为空。")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "$".join(
        [
            ALGORITHM,
            str(iterations),
            base64.urlsafe_b64encode(salt).decode().rstrip("="),
            base64.urlsafe_b64encode(digest).decode().rstrip("="),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = encoded.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        iterations = int(raw_iterations)
        salt = _decode_base64(raw_salt)
        expected = _decode_base64(raw_digest)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected)


def configured_password_hash() -> str:
    return os.environ.get("RANDOMSTU_PASSWORD_HASH", "").strip()


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"hash-password", "configure-password"}:
        raise SystemExit(
            "用法: python3 -m services.randomStu.auth "
            "hash-password | configure-password [env文件]"
        )
    password = getpass.getpass("请输入 RandomStu 管理密码: ")
    confirmation = getpass.getpass("请再次输入密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致。")
    encoded = hash_password(password)
    if sys.argv[1] == "hash-password":
        print(encoded)
        return

    env_file = Path(sys.argv[2] if len(sys.argv) > 2 else "services/picZip/.env")
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    output: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("RANDOMSTU_PASSWORD_HASH="):
            output.append(f"RANDOMSTU_PASSWORD_HASH={encoded}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"RANDOMSTU_PASSWORD_HASH={encoded}")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(output) + "\n", encoding="utf-8")
    env_file.chmod(0o600)
    print(f"密码哈希已写入 {env_file}")


if __name__ == "__main__":
    main()

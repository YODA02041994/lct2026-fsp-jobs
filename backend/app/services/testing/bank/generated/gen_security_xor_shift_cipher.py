"""Базовые преобразования (XOR, ROT13, base64, хеш): предсказать вывод, рассуждая о свойствах, а не считая байты руками."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_security_xor_shift_cipher", title="Свойства XOR, ROT13, base64 и хеша",
          competency="Криптография: базовые шифры и кодирование",
          specializations=["security"], technologies=["python", "cryptography"],
          fmt="exact", grade_level="middle", difficulty_shift=0.0)
def _xor_shift_cipher(rng: random.Random) -> Instance:
    kind = rng.randrange(5)

    if kind == 0:
        # XOR инволютивен: data ^ key ^ key == data. Код выводит исходное слово.
        words = ["secret", "vector", "cipher", "nonce", "attack", "shield", "stream"]
        key = rng.choice(["key", "xor", "abc", "salt", "iv"])
        word = rng.choice(words)
        code = (
            "def xor(data: bytes, key: bytes) -> bytes:\n"
            "    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))\n\n"
            f"once = xor(b\"{word}\", b\"{key}\")\n"
            f"twice = xor(once, b\"{key}\")\n"
            "print(twice.decode())"
        )
        expl = ("XOR инволютивен: применённый с тем же ключом дважды, он возвращает исходные байты "
                "(b ^ k ^ k == b), поэтому печатается исходное слово.")
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите строку.",
                        answer=ans, code=code, language="python", explanation=expl)

    if kind == 1:
        # Длина base64 = 4 * ceil(n / 3); считается по длине входа, без самого кодирования.
        words = ["key", "flag", "token", "secret", "payload", "password", "identifier"]
        word = rng.choice(words)
        code = (
            "import base64\n"
            f"data = b\"{word}\"\n"
            "print(len(base64.b64encode(data)))"
        )
        expl = (f"base64 кодирует каждые 3 байта в 4 символа с дополнением до кратности 4: длина "
                f"для {len(word)} байт равна 4*ceil({len(word)}/3).")
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите число.",
                        answer=ans, code=code, language="python", explanation=expl)

    if kind == 2:
        # Длина дайджеста sha256: hexdigest -> 64 символа, digest -> 32 байта.
        words = ["hello", "world", "secret", "crypto", "python", "vector"]
        word = rng.choice(words)
        if rng.random() < 0.5:
            code = (
                "import hashlib\n"
                f"print(len(hashlib.sha256(b\"{word}\").hexdigest()))"
            )
            expl = "sha256 даёт 256 бит = 32 байта; hexdigest() выводит их как 64 шестнадцатеричных символа."
        else:
            code = (
                "import hashlib\n"
                f"print(len(hashlib.sha256(b\"{word}\").digest()))"
            )
            expl = "sha256 даёт 256 бит; digest() возвращает их как 32 байта."
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите число.",
                        answer=ans, code=code, language="python", explanation=expl)

    if kind == 3:
        # ROT13 — сам себе обратный: применённый дважды, возвращает исходный текст.
        words = ["attack", "defend", "binary", "cipher", "secure", "vector"]
        word = rng.choice(words)
        code = (
            "def rot13(s: str) -> str:\n"
            "    out = []\n"
            "    for c in s:\n"
            "        if 'a' <= c <= 'z':\n"
            "            out.append(chr((ord(c) - 97 + 13) % 26 + 97))\n"
            "        else:\n"
            "            out.append(c)\n"
            "    return ''.join(out)\n\n"
            f"print(rot13(rot13(\"{word}\")))"
        )
        expl = ("ROT13 сдвигает букву на 13 из 26 позиций, поэтому применённый дважды он возвращает "
                "исходную букву (13 + 13 = 26 ≡ 0); печатается исходное слово.")
        ans = _run_python(code)
        return Instance(question="Что выведет код? Введите строку.",
                        answer=ans, code=code, language="python", explanation=expl)

    # kind == 4: XOR байта с самим собой даёт 0 — сумма нулевых байтов равна нулю.
    words = ["hello", "world", "secret", "crypto", "python", "vector"]
    word = rng.choice(words)
    code = (
        f"data = b\"{word}\"\n"
        "ct = bytes(b ^ b for b in data)\n"
        "print(sum(ct))"
    )
    expl = "Для каждого байта b выполняется b ^ b == 0, поэтому все байты ct нулевые и их сумма равна 0."
    ans = _run_python(code)
    return Instance(question="Что выведет код? Введите число.",
                    answer=ans, code=code, language="python", explanation=expl)

import re

_TABLE = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_RE = re.compile(r"[\\&%$#_{}~^]")
_FIO = re.compile(r"^\s*((?:[A-ZА-ЯЁ]\.\s*(?:\\,|~)?\s*){1,2})\s*(\S.*)$")


def escape_tex(value) -> str:
    """Экранирует спецсимволы LaTeX; U+2011 заменяет на обычный дефис."""
    s = str(value).replace("\u2011", "-")
    return _RE.sub(lambda m: _TABLE[m.group()], s)


def fio(value) -> str:
    """'И. О. Иванов' / 'И.О.Иванов' / 'И.\\,О.~Иванов' -> 'И.\\,О.~Иванов'."""
    s = str(value).strip()
    m = _FIO.match(s)
    if not m:
        return escape_tex(s)
    initials = re.findall(r"[A-ZА-ЯЁ]\.", m.group(1))
    return r"\,".join(initials) + "~" + escape_tex(m.group(2).strip())

#!/usr/bin/env python3
"""Тянет ICS-фид, выкидывает события по ключевым словам, кладёт результат в docs/."""

import os
import sys
import urllib.request

# события, в SUMMARY которых встретится любое из этих слов, будут выброшены
SKIP = ["французск", "french"]

OUT_DIR = "docs"


def unfold(text):
    """ICS переносит длинные строки, продолжение начинается с пробела или таба."""
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def fold(line):
    """Собираем обратно: не длиннее 75 байт на строку."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    chunks, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > 73:
            chunks.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    chunks.append(cur.decode("utf-8"))
    return "\r\n ".join(chunks)


def main():
    url = os.environ.get("ICS_URL", "").strip()
    name = os.environ.get("OUT_NAME", "schedule").strip()
    if not url:
        sys.exit("ICS_URL не задан")
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]

    req = urllib.request.Request(url, headers={"User-Agent": "ics-filter"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8", "replace")

    lines = unfold(text)
    result, block, in_event = [], [], False
    kept = dropped = 0

    for line in lines:
        if line.startswith("BEGIN:VEVENT"):
            in_event, block = True, [line]
            continue
        if in_event:
            block.append(line)
            if line.startswith("END:VEVENT"):
                summary = ""
                for b in block:
                    if b.upper().startswith("SUMMARY"):
                        summary = b.split(":", 1)[-1]
                        break
                if any(w in summary.lower() for w in SKIP):
                    dropped += 1
                else:
                    kept += 1
                    result.extend(block)
                in_event, block = False, []
            continue
        result.append(line)

    os.makedirs(OUT_DIR, exist_ok=True)
    body = "\r\n".join(fold(l) for l in result if l != "")
    with open(os.path.join(OUT_DIR, name + ".ics"), "w", encoding="utf-8") as f:
        f.write(body + "\r\n")

    print("оставлено событий: %d, выброшено: %d" % (kept, dropped))


if __name__ == "__main__":
    main()

"""Daily profile README refresh.

1. Stamps today's date (Asia/Karachi) after <!--AUTO_UPDATE-->.
2. Shows one quote card, chosen by day of the year, between the QUOTE markers.
3. Checks the view counter and every stats card between the VIEWS and STATS markers. A card whose service is
   down or returns an error image is commented out, and restored once it works.

Standard library only, so the workflow needs no install step.
"""

import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

README = Path(__file__).resolve().parents[2] / "README.md"
PKT = timezone(timedelta(hours=5))

QUOTES = [
    ("A wrong number looks exactly like a right one on the page. Compute it, then trust it.", "Engineering Philosophy"),
    ("Let code compute the facts. Let the model phrase them.", "AI Mindset"),
    ("A test that only checks the happy path proves the feature works. A test that attacks proves the guard does.", "Engineering Philosophy"),
    ("Artificial Intelligence is not about replacing humans, it is about amplifying human potential through data and learning.", "AI Mindset"),
    ("Success is built on curiosity, consistency, and the courage to learn continuously.", "Personal Philosophy"),
    ("Innovation happens when experimentation meets persistence and real-world problem solving.", "Engineering Philosophy"),
    ("A model that reports its uncertainty honestly is worth more than one extra point of accuracy.", "ML Principle"),
    ("If it cannot be deployed, it does not exist. If it cannot be checked, it should not be claimed.", "Engineering Philosophy"),
    ("Most of machine learning happens before a model is ever fitted.", "ML Principle"),
    ("Private by default: the safest field is the one you never fetched.", "Engineering Philosophy"),
    ("Use AI where it earns its place, and a simple rule everywhere else.", "AI Mindset"),
    ("98% accuracy can still be useless. Always ask what the metric is hiding.", "ML Principle"),
    ("Always learning. Always shipping.", "Personal Philosophy"),
    ("Software should narrow the options. People should make the decisions that matter.", "AI Mindset"),
]

ERROR_MARKERS = ("something went wrong", "rate limit", "error", "maximum retries", "not found")


def stamp_date(text: str, now: datetime) -> str:
    return re.sub(r"<!--AUTO_UPDATE-->.*", f"<!--AUTO_UPDATE--> {now:%Y-%m-%d}", text)


def quote_card(now: datetime) -> str:
    quote, author = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
    params = urllib.parse.urlencode(
        {"type": "horizontal", "theme": "radical", "quote": quote, "author": author},
        quote_via=urllib.parse.quote,
    )
    return f'  <img src="https://quotes-github-readme.vercel.app/api?{params}" width="550px"/>'


def set_quote(text: str, now: datetime) -> str:
    return re.sub(
        r"(<!--QUOTE_START-->\n).*?(<!--QUOTE_END-->)",
        lambda m: m.group(1) + quote_card(now) + "\n" + m.group(2),
        text,
        flags=re.S,
    )


def card_is_healthy(url: str) -> bool:
    url = url.replace("&amp;", "&")
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-health-check"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                kind = resp.headers.get("Content-Type", "")
                body = resp.read(200_000).decode("utf-8", "ignore").lower()
                if resp.status == 200 and kind.startswith("image/"):
                    return not any(marker in body for marker in ERROR_MARKERS)
        except Exception:
            pass
    return False


CARD_REGIONS = ("VIEWS", "STATS")


def probe_url(url: str) -> str:
    """The view counter adds one on every fetch, so test a separate probe username instead."""
    if "komarev.com/ghpvc" not in url:
        return url
    return url.replace("username=zain-ul-abideen-5036", "username=zain-ul-abideen-5036-health-probe")


def check_cards(text: str) -> str:
    for region in CARD_REGIONS:
        text = check_region(text, region)
    return text


def check_region(text: str, region: str) -> str:
    start, end = text.find(f"<!--{region}_START-->"), text.find(f"<!--{region}_END-->")
    if start == -1 or end == -1:
        return text
    lines = text[start:end].split("\n")
    for i, line in enumerate(lines):
        hidden = re.match(r"(\s*)<!--HIDDEN (.*) HIDDEN-->\s*$", line)
        img = hidden.group(2) if hidden else line.strip()
        src = re.search(r'<img [^>]*src="([^"]+)"', img)
        if not src or not src.group(1).startswith("http"):
            continue
        indent = hidden.group(1) if hidden else line[: len(line) - len(line.lstrip())]
        healthy = card_is_healthy(probe_url(src.group(1)))
        lines[i] = f"{indent}{img}" if healthy else f"{indent}<!--HIDDEN {img} HIDDEN-->"
        print(f"{'ok    ' if healthy else 'HIDDEN'} {src.group(1)[:90]}")
    return text[:start] + "\n".join(lines) + text[end:]


def main() -> int:
    now = datetime.now(PKT)
    text = README.read_text(encoding="utf-8")
    text = check_cards(set_quote(stamp_date(text, now), now))
    README.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

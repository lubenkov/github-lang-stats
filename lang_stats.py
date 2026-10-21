import datetime
import json
import os
import re
import urllib.request
import urllib.error

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "lubenkov")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"

START = "<!-- LANGS:START -->"
END = "<!-- LANGS:END -->"

MEDALS = ["🥇", "🥈", "🥉"]


def api(path: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "lang-stats-integration",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(
            f"✖ GitHub API error {e.code} for {path}\n"
            "  Без токена лимит API — 60 запросов/час с одного IP.\n"
            "  Локально можно подложить токен:\n"
            "  GITHUB_TOKEN=ghp_xxx python3 lang_stats.py   (Linux/macOS)\n"
            "  $env:GITHUB_TOKEN='ghp_xxx'; python lang_stats.py   (Windows PowerShell)\n"
            "  В GitHub Actions токен подставляется сам — там ошибки не будет."
        ) from e


def bar(frac: float, width: int = 10) -> str:
    filled = max(1, round(frac * width))
    return "█" * filled + "░" * (width - filled)


def render(repos: list) -> str:
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1

    if not langs:
        return "_No language data yet._"

    total = sum(langs.values())
    top = sorted(langs.items(), key=lambda x: (-x[1], x[0]))

    lines = [
        "| Rank | Language | Repos | Share |",
        "|---:|---|---:|---|",
    ]
    for i, (name, count) in enumerate(top):
        rank = MEDALS[i] if i < len(MEDALS) else str(i + 1)
        share = count / total
        lines.append(f"| {rank} | {name} | {count} | {bar(share)} {share:.0%} |")

    lines.append("")
    lines.append(
        f"_Primary languages across {len(own)} public repos · "
        f"updated {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC "
        "via GitHub REST API_"
    )
    return "\n".join(lines)


def main():
    repos = api(f"/users/{USERNAME}/repos?per_page=100&type=owner")

    block = f"{START}\n{render(repos)}\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)

    path = "README.md"
    text = (
        open(path, encoding="utf-8").read()
        if os.path.exists(path)
        else f"# lang-stats\n\n{block}\n"
    )

    if pattern.search(text):
        text = pattern.sub(lambda _: block, text)
    else:
        text = text.rstrip() + f"\n\n{block}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✔ README.md updated for {USERNAME}")


if __name__ == "__main__":
    main()

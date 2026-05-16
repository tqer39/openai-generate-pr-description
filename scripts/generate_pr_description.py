# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "openai",
# ]
# ///
from openai import OpenAI
import os
import subprocess

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API key is not set.")

github_repo = os.getenv("GITHUB_REPOSITORY", "tqer39/generate-pr-description")
default_headers = {
    "HTTP-Referer": f"https://github.com/{github_repo}",
    "X-Title": "generate-pr-description",
}

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    default_headers=default_headers,
)


def create_prompt(commit_logs: str, custom_prompt: str | None = None, locale: str = "en") -> str:
    default_prompt = f"""
    You generate a pull request title and description from commit logs and diffs.

    # Output format (STRICT)

    Your entire response MUST follow this exact shape and nothing else:

    Line 1: The pull request title.
      - Plain text only. No Markdown, no quotes, no labels, no prefix like "Title:".
      - Start with one emoji that fits the change, followed by a single space.
      - One line only. No trailing blank line before the body.

    Line 2 onward: The pull request description body in Markdown.
      - Do NOT repeat or translate any label such as "Pull Request Title",
        "Pull Request Description", "Title", "Body", or "Description".
      - Do NOT output a top-level heading for the description itself.
      - Use the section headings listed below as `##` headings (translated into the
        response language). Omit any section that has nothing meaningful to say.
      - Enclose file names in backticks.
      - You MAY use GitHub Markdown alerts (`> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`,
        `> [!WARNING]`, `> [!CAUTION]`) when appropriate.
      - You MAY use mermaid.js code blocks when a diagram clarifies the change.
      - Do NOT fabricate information; rely only on the commit logs and diffs.

    # Section headings to use in the body (translate into the response language)

    - 📒 Summary of Changes — bullet list, one emoji at the start of each item.
    - ⚒ Technical Details — bullet list, one emoji at the start of each item.
    - ⚠ Points of Caution — bullet list, one emoji at the start of each item.

    # Language

    Write the entire response in the locale: {locale}.

    # Example shape (do NOT copy the wording; only the structure)

    🔧 Refactor authentication helpers

    ## 📒 Summary of Changes

    - ♻️ Consolidate token validation into a single helper.

    ## ⚒ Technical Details

    - 🔐 Replace ad-hoc JWT parsing with `jwt.decode` in `auth/token.py`.

    # Commit logs and diffs

    {commit_logs}
    """
    return custom_prompt or default_prompt


_LABEL_NOISE_PATTERNS = (
    # English labels
    "pull request title",
    "pull request description",
    "title:",
    "description:",
    "body:",
    # Japanese labels
    "プルリクエストタイトル",
    "プルリクエストの説明",
    "プルリクエスト説明",
    "タイトル:",
    "タイトル：",
    "説明:",
    "説明：",
)


def _strip_label_lines(text: str) -> str:
    """Remove leading lines that are just label echoes from the LLM.

    The OpenRouter prompt previously contained literal section labels
    ("Pull Request Title" / "## Pull Request Description") which gpt-4o-mini
    occasionally reproduced (translated when locale=ja) as the first lines
    of its response. The shell side splits the response with `head -n 1`,
    so a leaked label becomes the PR title. This helper drops any such
    leading label lines (and leading blanks) before the response is printed.

    Only the leading run is stripped; identical strings appearing later in
    the body are kept as-is to avoid false positives.
    """
    lines = text.splitlines()
    while lines:
        head = lines[0].strip().strip("#").strip().strip("*").strip().lower()
        if head and any(head == pat or head.startswith(pat) for pat in _LABEL_NOISE_PATTERNS):
            lines.pop(0)
            continue
        if not head:
            lines.pop(0)
            continue
        break
    return "\n".join(lines)


def generate_pr_description(commit_logs: str, locale: str = "en") -> str:
    prompt = create_prompt(commit_logs, locale=locale)

    response = client.chat.completions.create(
        model=os.getenv("MODEL", "openai/gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a highly skilled software engineer."},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=int(os.getenv("MAX_TOKENS", "1000")),
        temperature=float(os.getenv("TEMPERATURE", "0.1")),
        extra_body={"route": "fallback"},
    )

    raw = str(response.choices[0].message.content).strip()
    return _strip_label_lines(raw)


def get_commit_logs_and_diffs() -> str:
    subprocess.run(["git", "fetch", "origin"], check=True)

    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %s", "origin/main..HEAD", "-n", str(os.getenv("COMMIT_LOG_HISTORY_LIMIT"))],
        capture_output=True,
        text=True,
    )
    commit_logs = result.stdout.strip().split("\n")

    if not commit_logs or commit_logs == [""]:
        return ""

    logs_and_diffs = []
    for commit in commit_logs:
        commit_hash = commit.split()[0]
        if commit_hash:
            diff_result = subprocess.run(
                ["git", "diff", commit_hash + "^!", "--"],
                capture_output=True,
                text=True,
            )
            logs_and_diffs.append(f"Commit: {commit}\nDiff:\n{diff_result.stdout}")

    return "\n\n".join(logs_and_diffs)


if __name__ == "__main__":
    commit_logs_and_diffs = get_commit_logs_and_diffs()

    if commit_logs_and_diffs:
        locale = os.getenv("LOCALE", "en")
        pr_description = generate_pr_description(commit_logs_and_diffs, locale=locale)
        print(pr_description)
    else:
        print("No new commits detected.")

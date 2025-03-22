# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "openai",
# ]
# ///
from openai import OpenAI
import os
import subprocess

# OpenAI API キーを設定
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key is not set.")

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("OPENAI_API_KEY")
)


# プロンプトの準備
def create_prompt(commit_logs: str, custom_prompt: str = None) -> str:
    default_prompt = f"""
    ## Instructions

    - Read the following commit logs and file diffs, and create an easy-to-understand pull request title and detailed description.
    -
    - From the second line onward, write in Markdown format.
    - Enclose file names in backticks.
    - Refer to the following:
        - Use GitHub's Markdown syntax (https://github.com/orgs/community/discussions/16925) for NOTE, TIPS, IMPORTANT, WARNING, CAUTION as needed.

    Example:
    ```
    > [!WARNING]
    >
    > - 💣 This includes a breaking change. Please be cautious.
    ```

    - Pull Request Title
        1. Output on the first line. Do not use Markdown.
        2. Add an appropriate emoji at the beginning of the title.
    - Pull Request Description
        1. From the second line onward, provide the pull request description.
        2. Read the commit logs and files, and describe the summary of changes, technical details, and any points of caution.
            1. If there are none, do not output the section.
            2. Do not fabricate information.
        3. If a diagram of the process is needed, use mermaid.js syntax.

    ## Commit Logs and File Diffs

    {commit_logs}

    ## Pull Request Description

    ## 📒 Summary of Changes

    1. Add an appropriate emoji at the beginning of each item.

    ## ⚒ Technical Details

    1. Add an appropriate emoji at the beginning of each item.

    ## ⚠ Points of Caution

    1. Add an appropriate emoji at the beginning of each item.
    """
    return custom_prompt or default_prompt


# OpenAI API でのリクエスト
def generate_pr_description(commit_logs: str) -> str:
    prompt = create_prompt(commit_logs)

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL"),
        messages=[
            {"role": "system", "content": "あなたは優秀なソフトウェアエンジニアです。"},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=1000,
        temperature=0.1,
    )

    return str(response.choices[0].message.content).strip()


# Git コミットログとファイルの差分の取得
def get_commit_logs_and_diffs() -> str:
    # リモートの変更を取得
    subprocess.run(["git", "fetch", "origin"], check=True)

    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %s", "origin/main..HEAD", "-n", str(os.getenv("COMMIT_LOG_HISTORY_LIMIT"))],
        capture_output=True,
        text=True,
    )  # コミットログの数を制限
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


# メインロジック
if __name__ == "__main__":
    commit_logs_and_diffs = get_commit_logs_and_diffs()

    if commit_logs_and_diffs:
        pr_description = generate_pr_description(commit_logs_and_diffs)
        print(pr_description)
    else:
        print("No new commits detected.")

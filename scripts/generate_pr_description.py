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
    ## 指示内容

    - 以下のコミットログとファイルの差分を読んで、理解し易いプルリクエストのタイトルと詳細な説明を作成してください。
    -
    - 2行目以降は Markdown 形式で記述してください。
    - ファイル名はバッククオートで囲んでください。
    -  を参考にしてください。
        - 必要に応じて GitHub の Markdown 記法（https://github.com/orgs/community/discussions/16925）を参考に NOTE, TIPS, IMPORTANT, WARNING, CAUTION を使用してください。

    例:
    ```
    > [!WARNING]
    >
    > - 💣 breaking change が含まれています。注意してください。
    ```

    - プルリクエストのタイトル
        1. 1行目に出力してください。Markdown にしないでください。
        2. タイトルの冒頭には総合的に適した emoji をつけてください。
    - プルリクエストの説明
        1. 2行目以降がプルリクエストの説明です。
        2. コミットログとファイルを読んで、変更点の概要と技術的な詳細や注意点を記述してください。
            1. なければ項目ごと出力しない。
            2. 嘘を書かない。
        3. 処理内容の図解が必要であれば mermaid.js の記法を使用する。

    ## コミットログとファイルの差分

    {commit_logs}

    ## プルリクエストの説明

    ## 📒 変更点の概要

    1. 各項目の先頭に適切な emoji を付ける。

    ## ⚒ 技術的な詳細

    1. 各項目の先頭に適切な emoji を付ける。

    ## ⚠ 注意点

    1. 各項目の先頭に適切な emoji を付ける。
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

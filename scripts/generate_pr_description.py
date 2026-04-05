# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "litellm",
# ]
# ///
import os
import subprocess
import sys

import litellm


def resolve_config() -> tuple[str, str, str]:
    """Resolve configuration with backward compatibility."""
    api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key is not set. Provide 'api-key' input.")

    if os.getenv("OPENAI_API_KEY") and not os.getenv("API_KEY"):
        print("WARNING: 'openai-api-key' is deprecated. Use 'api-key' instead.", file=sys.stderr)

    model = os.getenv("MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    if os.getenv("OPENAI_MODEL") and not os.getenv("MODEL"):
        print("WARNING: 'openai-model' is deprecated. Use 'model' instead.", file=sys.stderr)

    provider = os.getenv("PROVIDER", "openai")

    return api_key, provider, model


# Prepare the prompt
def create_prompt(commit_logs: str, custom_prompt: str | None = None, locale: str = "en") -> str:
    default_prompt = f"""
    ## Instructions

    - Read the following commit logs and file diffs, and create an easy-to-understand pull request title and detailed description.
    -
    - From the second line onward, write in Markdown format.
    - Enclose file names in backticks.
    - Refer to the following:
        - Use GitHub's Markdown syntax (https://github.com/orgs/community/discussions/16925) for NOTE, TIPS, IMPORTANT, WARNING, CAUTION as needed.
    - Respond in the language specified by the locale: {locale}.
    - Ensure that the response is entirely in the specified locale language.

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


def generate_pr_description(commit_logs: str, locale: str = "en") -> str:
    prompt = create_prompt(commit_logs, locale=locale)
    api_key, provider, model = resolve_config()

    # LiteLLM uses provider/model format
    model_string = f"{provider}/{model}" if "/" not in model else model

    max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
    temperature = float(os.getenv("TEMPERATURE", "0.1"))

    response = litellm.completion(
        model=model_string,
        messages=[
            {"role": "system", "content": "You are a highly skilled software engineer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        api_key=api_key,
        api_base=os.getenv("API_BASE_URL") or None,
    )

    return str(response.choices[0].message.content).strip()


# Retrieve Git commit logs and file diffs
def get_commit_logs_and_diffs() -> str:
    # Fetch remote changes
    subprocess.run(["git", "fetch", "origin"], check=True)

    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %s", "origin/main..HEAD", "-n", str(os.getenv("COMMIT_LOG_HISTORY_LIMIT"))],
        capture_output=True,
        text=True,
    )  # Limit the number of commit logs
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


# Main logic
if __name__ == "__main__":
    commit_logs_and_diffs = get_commit_logs_and_diffs()

    if commit_logs_and_diffs:
        locale = os.getenv("LOCALE", "en")  # Default to English if LOCALE is not set
        pr_description = generate_pr_description(commit_logs_and_diffs, locale=locale)
        print(pr_description)
    else:
        print("No new commits detected.")

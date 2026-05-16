"""Tests for generate_pr_description helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    """`scripts/generate_pr_description.py` は API_KEY を import 時に要求するため、
    API_KEY を環境変数にセットしてからロードする。"""
    import os

    os.environ.setdefault("API_KEY", "dummy-for-tests")

    script_path = Path(__file__).parent.parent / "scripts" / "generate_pr_description.py"
    spec = importlib.util.spec_from_file_location("generate_pr_description", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_pr_description"] = module
    spec.loader.exec_module(module)
    return module


MOD = _load_module()


def test_strips_japanese_label_at_start():
    """LLM が日本語ラベルを 1 行目に出した場合、それを剥がして本来のタイトルを 1 行目に持ってくる。"""
    bad = (
        "プルリクエストタイトル  \n"
        "🔒 tts-partner リポジトリを private に変更\n"
        "\n"
        "プルリクエストの説明\n"
        "\n"
        "## 📒 変更の概要\n"
    )
    cleaned = MOD._strip_label_lines(bad)
    assert cleaned.splitlines()[0] == "🔒 tts-partner リポジトリを private に変更"


def test_strips_english_label_at_start():
    """英語ラベル ("Pull Request Title", "Title:" 等) も剥がす。"""
    bad = "Pull Request Title\n🔧 refactor auth helpers\n\n## Summary\n"
    cleaned = MOD._strip_label_lines(bad)
    assert cleaned.splitlines()[0] == "🔧 refactor auth helpers"


def test_strips_title_colon_prefix():
    """`Title:` のようなラベル行も剥がす。"""
    bad = "Title: foo\n🚀 release v1\n\nbody\n"
    cleaned = MOD._strip_label_lines(bad)
    assert cleaned.splitlines()[0] == "🚀 release v1"


def test_keeps_label_in_middle():
    """中間に偶然ラベル風文字列が出ても剥がさない（先頭のみ対象）。"""
    text = "🔒 title\n\nプルリクエストの説明 should stay\n"
    cleaned = MOD._strip_label_lines(text)
    assert "プルリクエストの説明 should stay" in cleaned


def test_no_label_passthrough():
    """ラベルが無い正常出力はそのまま返す（前後の strip のみ）。"""
    text = "🚀 fix bug\n\nbody here"
    cleaned = MOD._strip_label_lines(text)
    assert cleaned.splitlines()[0] == "🚀 fix bug"
    assert "body here" in cleaned


def test_strips_leading_blank_lines():
    """先頭の空行は剥がす。"""
    text = "\n\n🔧 fix\n\nbody"
    cleaned = MOD._strip_label_lines(text)
    assert cleaned.splitlines()[0] == "🔧 fix"

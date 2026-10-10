import json

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="ライフハッ君 ツール", page_icon="🧴", layout="wide")

DEFAULT_MODEL = "gemini-2.5-flash"
MIN_CHARS, MAX_CHARS = 65, 75

ANGLES = ["おまかせ", "意外な使い方", "よくある失敗を防ぐ", "組み合わせ技"]
TONES = [
    "元気いっぱい",
    "ツンデレ",
    "クール・淡々",
    "おっとり",
    "ちょっと偉そう",
    "必死・切実",
]

# ---------------------------------------------------------------- sidebar (BYOK)
with st.sidebar:
    st.header("設定")
    api_key = st.text_input(
        "Gemini APIキー",
        type="password",
        help="このセッション内でのみ使用し、保存・ログ出力は一切しません。",
    )
    model = st.text_input("モデル名", value=DEFAULT_MODEL)
    st.caption(
        "APIキーは Google AI Studio で発行できます。"
        "ブラウザを閉じる/リロードするとキーは消えます。"
    )


# ---------------------------------------------------------------- helpers
def call_json(prompt: str):
    """Gemini を呼んで JSON を返す。"""
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=1.0,
        ),
    )
    return json.loads(resp.text)


def count_chars(text: str) -> int:
    return len("".join(text.split()))


def need_key() -> bool:
    if not api_key:
        st.warning("サイドバーに Gemini APIキーを入力してください。")
        return True
    return False


# ---------------------------------------------------------------- prompts
def build_idea_prompt(theme: str, n: int) -> str:
    return f"""あなたはSNSショート動画の企画担当です。
テーマ「{theme}」について、ライフハック・豆知識を{n}個挙げてください。

条件:
- 医学的・科学的根拠のないもの、俗説は含めない
- 「手洗いをしましょう」のような常識的すぎるものは避け、知らない人が多い情報を選ぶ
- 各項目は次の4つのキーを持つこと

出力はJSON配列のみ。各要素は次の形式:
{{"topic": "【トピック】", "ng": "【NG行為・注意点】", "fix": "【改善策・活用法】", "effect": "【期待される効果】"}}
"""


def build_script_prompt(idea: str, angle: str, tone: str, n: int) -> str:
    angle_line = (
        "切り口はネタに最も合うものを自由に選ぶ"
        if angle == "おまかせ"
        else f"切り口は「{angle}」"
    )
    return f"""あなたは、日用品を擬人化して一人称で話させる10秒ショート動画の脚本家です。
次のネタをもとに、台本を{n}パターン作ってください。

【ネタ】
{idea}

条件:
- {angle_line}
- キャラのトーン: {tone}（標準語）
- 台本は2〜3文、会話調、一人称、{MIN_CHARS}〜{MAX_CHARS}文字（空白・改行を除く）
- 冒頭は視聴者が続きを見たくなる一言にする
- 医学的に誤解を招く表現は避ける
- パターンごとにしゃべるモノを変える

出力はJSON配列のみ。各要素は次のキーを持つ:
{{
  "mono": "しゃべるモノ",
  "gender": "キャラの性別",
  "titles": "タイトル案（3つを / 区切りで）",
  "script": "台本",
  "surprise": "意外性ポイント",
  "emotion": "キャラの感情",
  "voice": "キャラの声（高さ・話し方など）",
  "scene": "シーンの場所・状況"
}}
"""


# ---------------------------------------------------------------- UI
st.title("🧴 ライフハッ君 ネタ探し＆台本ツール")

if "ideas" not in st.session_state:
    st.session_state.ideas = []

tab_idea, tab_script = st.tabs(["① ネタ探し", "② 台本生成"])

# ---- tab 1
with tab_idea:
    col1, col2 = st.columns([3, 1])
    theme = col1.text_input("テーマ", placeholder="例：衛生 / キッチン / 睡眠")
    n_ideas = col2.number_input("個数", min_value=5, max_value=30, value=20, step=5)

    if st.button("ネタを出す", type="primary", key="gen_ideas"):
        if need_key():
            pass
        elif not theme.strip():
            st.warning("テーマを入力してください。")
        else:
            with st.spinner("ネタを考え中…"):
                try:
                    st.session_state.ideas = call_json(
                        build_idea_prompt(theme.strip(), int(n_ideas))
                    )
                except Exception as e:  # noqa: BLE001
                    st.error(f"エラー: {e}")

    for i, it in enumerate(st.session_state.ideas, 1):
        with st.expander(f"{i}. {it.get('topic', '')}"):
            st.markdown(f"**【NG行為・注意点】** {it.get('ng', '')}")
            st.markdown(f"**【改善策・活用法】** {it.get('fix', '')}")
            st.markdown(f"**【期待される効果】** {it.get('effect', '')}")

# ---- tab 2
with tab_script:
    ideas = st.session_state.ideas
    options = ["（手入力する）"] + [
        f"{i}. {it.get('topic', '')}" for i, it in enumerate(ideas, 1)
    ]
    choice = st.selectbox("ネタを選ぶ（①の結果から）", options)

    default_text = ""
    if choice != options[0]:
        it = ideas[options.index(choice) - 1]
        default_text = (
            f"トピック: {it.get('topic', '')}\n"
            f"NG行為・注意点: {it.get('ng', '')}\n"
            f"改善策・活用法: {it.get('fix', '')}\n"
            f"期待される効果: {it.get('effect', '')}"
        )

    idea_text = st.text_area(
        "ネタの内容（編集OK）",
        value=default_text,
        height=160,
        key=f"idea_text_{choice}",
    )

    c1, c2, c3 = st.columns(3)
    angle = c1.selectbox("切り口", ANGLES)
    tone = c2.selectbox("キャラのトーン", TONES)
    n_scripts = c3.slider("パターン数", 1, 5, 3)

    if st.button("台本を作る", type="primary", key="gen_scripts"):
        if need_key():
            pass
        elif not idea_text.strip():
            st.warning("ネタを選ぶか入力してください。")
        else:
            with st.spinner("台本を書き中…"):
                try:
                    st.session_state.scripts = call_json(
                        build_script_prompt(idea_text.strip(), angle, tone, n_scripts)
                    )
                except Exception as e:  # noqa: BLE001
                    st.error(f"エラー: {e}")

    for i, s in enumerate(st.session_state.get("scripts", []), 1):
        n = count_chars(s.get("script", ""))
        ok = MIN_CHARS <= n <= MAX_CHARS
        with st.container(border=True):
            st.subheader(f"パターン {i}：{s.get('mono', '')}")
            st.markdown(f"**【しゃべるモノ】** {s.get('mono', '')}")
            st.markdown(f"**【キャラの性別】** {s.get('gender', '')}")
            st.markdown(f"**【タイトル案】** {s.get('titles', '')}")
            st.markdown("**【台本】**")
            st.code(s.get("script", ""), language=None, wrap_lines=True)
            if ok:
                st.success(f"{n}文字（目標 {MIN_CHARS}〜{MAX_CHARS}）")
            else:
                st.error(f"{n}文字（目標 {MIN_CHARS}〜{MAX_CHARS}）→ 範囲外です")
            st.markdown(f"**【意外性ポイント】** {s.get('surprise', '')}")
            st.markdown(f"**【キャラの感情】** {s.get('emotion', '')}")
            st.markdown(f"**【キャラの声】** {s.get('voice', '')}")
            st.markdown(f"**【シーンの場所・状況】** {s.get('scene', '')}")

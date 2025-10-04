import streamlit as st
import subprocess
import time
import re
import json
import json5
from streamlit_js_eval import streamlit_js_eval
import st_screen_stats
import streamlit.components.v1 as components

st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)
# HTMLのh1タグとCSSのtext-align: center; を使って中央に配置
st.markdown("<h1 style='text-align: center;'>MCBE ProxVC Setup</h1>",
            unsafe_allow_html=True)
# ページの基本設定
st.set_page_config(
    page_title="MCBE ProxyVC Setup",  # ← タブに表示される名前
    page_icon="./apple-touch-icon-180x180.png",        # ← タブのアイコン（絵文字も指定可）
    layout="wide"         # ← ページのレイアウト
)

lang_codes = ["en", "ja"]
langs = ["English (en)", "日本語 (ja)"]


def onScreenSizeChange():
    return


st.markdown("""
<style>
    /* streamlit-js-evalが生成するiframeを直接含むdiv要素をターゲットにする */
    div:has(> iframe.stCustomComponentV1) {
        /* このdivを非表示にし、スペースを確保しないようにする */
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ScreenDataでウィンドウサイズを含む色々な値を取得
screenData = st_screen_stats.ScreenData()
# on_changeに関数を指定すると、ウィンドウサイズが変更されたときにその関数が呼ばれる。指定してもしなくても再実行される
screen_stats_result = screenData.st_screen_data(
    key="screen_stats", on_change=onScreenSizeChange)
if screen_stats_result is not None:
    width = screen_stats_result.get("innerWidth", 1920)
else:
    width= 1920  # 初期値を設定（もしくは return で一時停止）
# 1. ブラウザの言語設定を取得（ or "en" を削除）
browser_lang_code = streamlit_js_eval(
    js_expressions="navigator.language", key="browser_lang")


@st.cache_data  # 結果をキャッシュしてパフォーマンス向上
def load_translations(lang_code):
    """
    指定された言語の翻訳ファイルを読み込む。
    ファイルが見つからない場合は、デフォルトの英語ファイルを読み込む。
    """
    default_lang = 'en'
    lang_to_load = lang_code

    # 1. 指定された言語のファイルを読み込み試行
    try:
        path = f'locales/{lang_to_load}.json'
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:

        # 2. 失敗した場合、デフォルトの言語ファイルを読み込む
        try:
            path = f'locales/{default_lang}.json'
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


# 2. session_state の初期化
if 'browser_lang_applied' not in st.session_state:
    # ブラウザ言語を適用済みかどうかのフラグ
    st.session_state.browser_lang_applied = False

if 'langNum' not in st.session_state:
    # ユーザーの言語選択
    st.session_state.langNum = 0

if browser_lang_code and not st.session_state.get("browser_lang_applied", False):
    main_lang_from_browser = browser_lang_code.split("-")[0]
    if main_lang_from_browser in lang_codes:
        st.session_state.lang = langs[lang_codes.index(
            main_lang_from_browser)]
        st.session_state.langNum = lang_codes.index(main_lang_from_browser)
    st.session_state.browser_lang_applied = True
    st.rerun()


def change_lang():
    st.session_state.langNum = langs.index(st.session_state.lang)


# 4. 現在の選択に基づいて翻訳を読み込む
#    st.session_state.langNum はブラウザ言語かユーザーの選択を反映している
current_lang_code = lang_codes[st.session_state.langNum]
translations = load_translations(current_lang_code)

if 'last_processed_file_id' not in st.session_state:
    st.session_state.last_processed_file_id = None

if 'upload_message' not in st.session_state:
    st.session_state.upload_message = None

# --- 2. スクリプト冒頭で、引き継がれたメッセージがあれば表示 ---
if st.session_state.upload_message:
    # メッセージの種類に応じて success や warning を表示
    if st.session_state.upload_message["type"] == "success":
        st.success(translations.get("upload_success", "Upload succeeded."))
    elif st.session_state.upload_message["type"] == "warning":
        st.warning(translations.get(
            "upload_error", "No common key was found."))

    # 一度表示したらメッセージを消去する（重要）
    st.session_state.upload_message = None

DEF_CONFIG_FILE_PATH = "def-config.json"
CONFIG_FILE_PATH = "config.json"


def load_existing_config():
    """現在のconfig.jsonを読み込む"""
    try:
        with open(DEF_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json5.load(f)
    except FileNotFoundError:
        st.error(f"'{DEF_CONFIG_FILE_PATH}' が見つかりません。")
        return None


def change_setting(uploaded_file):
    if uploaded_file.file_id != st.session_state.last_processed_file_id:
        try:
            uploaded_data = json5.load(uploaded_file)

            # 既存のファイル更新処理
            existing_config_data = load_existing_config()
            if existing_config_data:
                common_keys = set(uploaded_data.keys()) & set(
                    existing_config_data.keys())
                if common_keys:
                    for key in common_keys:
                        value = uploaded_data[key]
                        if key == "distance":
                            value = float(value)
                        if (key in st.session_state) and (type(st.session_state[key]) == type(value)):
                            if key == "lang":
                                options_map = {"en": 0, "ja": 1}
                                new_index = options_map.get(value, 0)
                                st.session_state[key] = langs[new_index]
                                st.session_state.langNum = new_index
                            else:
                                st.session_state[key] = value

                    # ★★★ st.success()の代わりにメッセージをsession_stateに保存 ★★★
                    st.session_state.upload_message = {
                        "type": "success"
                    }
                else:
                    st.session_state.upload_message = {
                        "type": "warning"
                    }

            st.session_state.last_processed_file_id = uploaded_file.file_id
            return True

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.last_processed_file_id = uploaded_file.file_id
            return False
    else:
        return False


st.markdown(
    f"### {translations.get('proximity_setting_title', 'Proximity VC Settings')}")
st.markdown(f"{translations.get('proximity_setting_description', 'In-game settings can be changed.(For more details, run !help in the chat.)')}")

defaults = {
    "app_id": "",
    "secret_key": "",
    "username": "",
    "sub_domain": "",
    "sub_domain2": "",
    "ssh_password": "",
    "port": 19132,  # 固定値
    "web_port": 8000,  # 固定値
    "proximity": True,
    "spectator": True,
    "specListen": True,
    "specDim": False,
    "password": False,
    "distance": 10.0,
    "lang": "English (en)"
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# 2つの列を作成
upload_col, lang_col = st.columns(2)

# 1列目にファイルアップローダーを配置
with upload_col:
    upload_file = st.file_uploader(
        label=translations.get("upload", "Upload Config File"),
        type=["json", "json5"],
        key='file_uploader'
    )
    if upload_file is not None:
        change_setting_result = change_setting(upload_file)
        del upload_file
        if change_setting_result:
            st.rerun()  # UIを更新するために再実行

# 2列目に言語選択ボックスを配置
with lang_col:
    language = st.selectbox(
        label=translations.get("language", "Language:"),
        options=langs,
        on_change=change_lang,
        key="lang"
    )

if width is not None:
    if (width >= 1000):
        prox_col, dis_col, pass_col, spec_col, = st.columns([1.3, 1.5, 2, 2])
    else:
        prox_col, dis_col = st.columns(2)
        pass_col, spec_col = st.columns(2)

    with prox_col:
        st.write("")
        st.write("")
        proximity = st.toggle(
            label=translations.get('prox_col', 'Enable proximity VC'),
            help=translations.get("default_enabled", "Default: Enabled"),
            key='proximity',
        )
    with dis_col:
        distance = st.number_input(
            label=translations.get(
                'dis_col', 'Maximum block distance for voice to reach'),
            min_value=0.0,
            step=0.5,
            help=translations.get("def_dis", "Default: 10"),
            key='distance',
            disabled=not proximity
        )
    with pass_col:
        if (width >= 1000):
            st.write("")
            st.write("")
        password = st.toggle(
            label=translations.get(
                'pass_col', 'Require password for VC connection'),
            help=translations.get("default_disabled", "Default: Disabled"),
            key='password',
            disabled=not proximity
        )
    with spec_col:
        if (width >= 1000):
            st.write("")
            st.write("")
        spectator = st.toggle(
            label=translations.get(
                'spec_col', 'Separate VC for players in Spectator mode'),
            help=translations.get("default_enabled", "Default: Enabled"),
            key='spectator',
            disabled=not proximity
        )

if (width >= 1000):
    specDim_col, specListen_col, = st.columns([1.4, 2])
else:
    specDim_col, specListen_col, = st.columns(2)
with specDim_col:
    specDim = st.toggle(
        label=translations.get(
            "specDim_col", "Separate spectator VC by dimension"),
        help=translations.get("default_disabled", "Default: Disabled"),
        key='specDim',
        disabled=not spectator or not proximity
    )
with specListen_col:
    specListen = st.toggle(
        label=translations.get(
            "specListen_col", "Allow spectators to hear non-spectator players"),
        help=translations.get("default_enabled", "Default: Enabled"),
        key='specListen',
        disabled=not spectator or not proximity
    )
if not st.session_state.spectator:
    specDim = False
    specListen = False

with st.expander(translations.get("advanced_settings", "Advanced Settings")):
    f"### {translations.get('tcp_exposer_settings_title', 'TCP Exposer Settings')}"
    f"{translations.get("tcp_exposer_settings_description", "Used to fix the room ID for Minecraft /connect or VC connections")}"
    username_col, tcp_pass_col = st.columns(2)
    sub_domain_col1, sub_domain_col2 = st.columns(2)
    with username_col:
        userName = st.text_input(
            label=translations.get("username_col", "TCP Exposer Username"),
            key='username'
        )
    with tcp_pass_col:
        sshPassword = st.text_input(
            label=translations.get("ssh_password_col", "TCP Exposer Password"),
            type="password",
            key='ssh_password'
        )
    with sub_domain_col1:
        subDomain = st.text_input(
            label=translations.get(
                "sub_domain_col", "TCP Exposer Subdomain for RoomID"),
            key='sub_domain'
        )
    with sub_domain_col2:
        subDomain2 = st.text_input(
            label=translations.get(
                "sub_domain2_col", "TCP Exposer Subdomain for Minecraft"),
            key='sub_domain2'
        )
    f"### {translations.get('skyway_settings_title', 'SkyWay Settings')}"
    f"{translations.get("skyway_settings_description", "SkyWay noise cancellation and other features can be used.")}"
    appId = st.text_input(
        label=translations.get("app_id_col", "SkyWay Application ID"),
        key='app_id'
    )
    secretKey = st.text_input(
        label=translations.get("secret_key_col", "SkyWay Secret Key"),
        type="password",
        key="secret_key"
    )

# --- 設定を構築する関数 ---


def change_config():
    language = st.session_state.lang or "English (en)"
    try:
        langCode = language.split("(")[1].split(")")[0]
    except IndexError:
        langCode = "en"

    new_config = {
        "app_id": appId,
        "secret_key": secretKey,
        "username": userName,
        "sub_domain": subDomain,
        "sub_domain2": subDomain2,
        "ssh_password": sshPassword,
        "port": 19132,
        "web_port": 8000,
        "proximity": proximity,
        "spectator": spectator,
        "specListen": specListen,
        "specDim": specDim,
        "password": password,
        "distance": distance,
        "lang": langCode,
    }
    return new_config


if "show_download" not in st.session_state:
    st.session_state.show_download = False
    st.rerun()

# --- 遅延してボタンを表示 ---
if st.session_state.show_download:
    st.download_button(
        label=translations.get("download_config", "Download Config File"),
        data=json.dumps(change_config(), indent=4, ensure_ascii=False),
        file_name="config.json",
        help=translations.get('download_config_description',
                              'You can download the current settings as a config.json file.'),
        mime="application/json"
    )
else:
    # 初回の一瞬だけ表示
    st.info("Loading download button...")
    st.session_state.show_download = True

# --- 1. セッション状態の初期化 ---
# is_running: プロセスが実行中かどうかのフラグ
# process: Popenオブジェクトを保存する場所
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'process' not in st.session_state:
    st.session_state.process = None

# ANSIコードを除去する関数（仮置き）


def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


# --- 2. UIの定義（実行中か否かで表示を切り替え） ---
if not st.session_state.is_running:
    new_config = change_config()

    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            # json5.dump() を使って辞書をファイルに書き込む
            json5.dump(new_config, f, indent=2)

    except IOError as e:
        print(f"❌ 設定ファイルの上書き中にエラーが発生しました: {e}")
# config.json を上書き保存
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=4, ensure_ascii=False)
    # --- 停止中のUI ---
    if st.button(translations.get("start", "Start Proximity VC"), type="primary", use_container_width=True):
        # プロセスを開始する
        st.session_state.is_running = True
        # Popenでプロセスを開始し、セッション状態に保存
        process = subprocess.Popen(
            ['node', 'index.js'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1
        )
        st.session_state.process = process
        st.rerun()  # 画面を再描画して「実行中」のUIに切り替える

else:
    # --- 実行中のUI ---
    if st.button(translations.get("stop", "Stop Proximity VC"), type="secondary", use_container_width=True):
        # プロセスを停止する
        if st.session_state.process:
            st.session_state.process.terminate()  # プロセスに終了シグナルを送信
            st.session_state.process.wait()      # 完全に終了するのを待つ

        # 状態をリセット
        st.session_state.is_running = False
        st.session_state.process = None
        with st.spinner(translations.get("stopping", "Stopping...")):
            time.sleep(3)  # メッセージを1秒表示
        st.rerun()  # 画面を再描画して「停止中」のUIに戻す

# --- 3. プロセスの出力表示（実行中のみ動作） ---
if st.session_state.is_running:
    with st.spinner(translations.get("starting", "Starting...")):
        time.sleep(3)
    placeholder = st.empty()
    output_lines = []

    process = st.session_state.process
    if process:
        try:
            # stdoutからリアルタイムで1行ずつ読み込む
            # このループはブロッキングだが、停止ボタンが押されるとst.rerunで中断される
            for line in iter(process.stdout.readline, ''):
                if not line:  # 出力がなくなったらループを抜ける
                    break
                clean_line = strip_ansi_codes(line)
                output_lines.append(clean_line)
                placeholder.code("".join(output_lines))

            # プロセスが自然に終了した場合の処理
            process.wait()  # 念のため終了を待つ
            stderr_output = process.stderr.read()
            if process.returncode != 0:
                st.error("エラーが発生しました:")
                st.code(stderr_output)
            else:
                st.success("Finish！")
                time.sleep(2)  # 完了メッセージを2秒表示

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            # 正常終了でもエラーでも、必ず状態をリセットしてUIを元に戻す
            st.session_state.is_running = False
            st.session_state.process = None

"""surfaceseal demo video — fully automated build pipeline.

Three-stage orchestrator:
  1. Synthesize per-scene narration WAV via a local Japanese TTS engine
     (AivisSpeech / Style-Bert-VITS2, OpenAI-compatible HTTP API on :10101).
  2. Record the static demo viewer with Playwright (Chromium, 1920x1080 headless).
  3. Compose WebM + narration into an MP4 with ffmpeg, burning in subtitles and
     a closing credit overlay.

Preconditions (must be running / installed):
  - static demo server  http://127.0.0.1:8002/  (python -m http.server 8002 --directory docs/demo-viewer)
  - TTS engine          http://127.0.0.1:10101/version
  - ffmpeg on PATH
  - playwright + chromium

Run:
  SPEAKER_ID=<id> python -m scripts.produce_video
  -> video/out/surfaceseal_demo.mp4  (~95s, 1080p)

Env vars:
  SPEAKER_ID=<int>     TTS speaker id (required; set to your engine's JP narrator)
  PITCH_SCALE=<float>  default 0.0; +/-0.03 is the natural range for the model
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

# Guard against Windows cp932 console failing on Japanese / emoji prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ─── config ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "video" / "out"
TEMP_DIR = BASE_DIR / "video" / "_temp"
STATIC_URL = "http://127.0.0.1:8002"   # Python http.server (--directory docs/demo-viewer)
ENGINE_URL = "http://127.0.0.1:10101"  # local TTS engine (standalone)
SPEAKER_ID = int(os.environ.get("SPEAKER_ID", "0"))  # set via env to your JP narrator

LEAD_IN_SEC = 0.4    # silence from scene start to narration start
TRAIL_OUT_SEC = 0.4  # minimum silence from narration end to next scene

# pitchScale: the TTS model's natural range is +/-0.03; beyond that it distorts.
PITCH_SCALE = float(os.environ.get("PITCH_SCALE", "0.0"))

VIEWPORT = {"width": 1920, "height": 1080}


# ─── scene definitions ────────────────────────────────────────────────

@dataclass
class Scene:
    id: str
    duration: float
    action: Callable
    narration: str


def _scenes_factory() -> list[Scene]:
    """Build the per-scene scroll actions over the demo viewer (surfaceseal).

    demo-viewer section anchors (docs/demo-viewer/index.html):
      .sec-hero / .sec-problem / .sec-diff / .sec-autorun / .sec-baseline /
      .sec-injection / .sec-failclosed / .sec-ci / .sec-design / .sec-free /
      .sec-license

    Narration rules: keep commas to 1-2 per line, spell roman brands in kana
    (surfaceseal -> サーフィスシール, AI -> エーアイ, MIT -> エムアイティー), use plain
    words, and never enumerate concrete dangerous command syntax (doc discipline).
    """

    def _to(p, sel: str) -> None:
        p.evaluate(
            f"document.querySelector('{sel}')?.scrollIntoView({{behavior: 'smooth', block: 'start'}})"
        )

    def s1(p):
        p.goto(f"{STATIC_URL}/")
        p.wait_for_load_state("networkidle")
        p.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")

    def s2(p):
        _to(p, ".sec-problem")

    def s3(p):
        _to(p, ".sec-diff")

    def s4(p):
        _to(p, ".sec-autorun")

    def s5(p):
        _to(p, ".sec-baseline")

    def s6(p):
        _to(p, ".sec-injection")

    def s7(p):
        _to(p, ".sec-failclosed")

    def s8(p):
        _to(p, ".sec-ci")

    def s9(p):
        _to(p, ".sec-design")

    def s10(p):
        _to(p, ".sec-free")

    def s11(p):
        _to(p, ".sec-license")

    return [
        Scene("S1", 9.0, s1, "エーアイ助手の設定変更に紛れた不正な仕掛けを、 世に出す前に止めるツール、 サーフィスシールです。"),
        Scene("S2", 9.5, s2, "エーアイ助手は設定ファイルを自動で信じて動きます。 そこに不正な指示を仕込む攻撃が実際に起きています。"),
        Scene("S3", 9.0, s3, "全部を調べると警告だらけになります。 だから今回の変更が持ち込んだ部分だけを見ます。"),
        Scene("S4", 9.5, s4, "起動時に自動で走る仕掛けが新しく加わったら、 中身を実行せずに見抜いて不合格にします。"),
        Scene("S5", 9.5, s5, "承認した時の姿を指紋として記録し、 あとから黙って書き換わっていないか見張ります。"),
        Scene("S6", 9.5, s6, "指示文に紛れた隠し命令の気配も拾います。 ただし文章の検査は補助として警告どまりです。"),
        Scene("S7", 9.0, s7, "読めない壊れた設定や、 許可していない仕掛けは、 黙って通さず安全側に倒します。"),
        Scene("S8", 9.5, s8, "不正な変更は終了コードでマージを止めます。 結果は標準形式でセキュリティ画面にも並びます。"),
        Scene("S9", 9.0, s9, "合否は決まった計算だけで判定します。 エーアイは説明だけを担当し、 判定には関与しません。"),
        Scene("S10", 8.5, s10, "すべて無料でカード登録も不要。 標準ライブラリのみで動き、 検査の外部送信はゼロです。"),
        Scene("S11", 8.0, s11, "エムアイティーライセンスで公開。 表示データはすべて合成データです。"),
    ]


SCENES = _scenes_factory()


# ─── helpers ───────────────────────────────────────────────────────────

def info(msg: str) -> None:
    print(f"[produce_video] {msg}", flush=True)


def check_preconditions() -> None:
    """Verify static server / TTS engine / ffmpeg / playwright are available."""
    errors = []

    try:
        r = requests.get(f"{STATIC_URL}/", timeout=3)
        assert r.status_code == 200
        info(f"OK static server live ({STATIC_URL}/ = 200)")
    except Exception as e:
        errors.append(f"static demo server down: {STATIC_URL} ({e}). start `python -m http.server 8002 --directory docs/demo-viewer`")

    try:
        r = requests.get(f"{ENGINE_URL}/version", timeout=3)
        assert r.status_code == 200
        info(f"OK TTS engine live ({ENGINE_URL}/version = {r.text.strip()})")
    except Exception as e:
        errors.append(f"TTS engine down: {ENGINE_URL} ({e}). start the AivisSpeech engine on :10101")

    if shutil.which("ffmpeg") is None:
        errors.append("ffmpeg not on PATH (`winget install Gyan.FFmpeg`)")
    else:
        info(f"OK ffmpeg ({shutil.which('ffmpeg')})")

    try:
        from playwright.sync_api import sync_playwright  # noqa
        info("OK playwright (Python binding)")
    except ImportError:
        errors.append("playwright missing (`pip install playwright && playwright install chromium`)")

    if SPEAKER_ID <= 0:
        errors.append("SPEAKER_ID env not set (set it to your TTS engine's JP narrator id)")

    if errors:
        info("==== precondition error ====")
        for e in errors:
            info(f"  - {e}")
        sys.exit(1)


def aivis_synthesize(text: str) -> bytes:
    """Synthesize a WAV via the TTS engine HTTP API (Style-Bert-VITS2)."""
    q = requests.post(
        f"{ENGINE_URL}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
        timeout=15,
    )
    q.raise_for_status()
    q_json = q.json()
    if PITCH_SCALE != 0.0:
        q_json["pitchScale"] = PITCH_SCALE
    s = requests.post(
        f"{ENGINE_URL}/synthesis",
        params={"speaker": SPEAKER_ID},
        json=q_json,
        timeout=60,
    )
    s.raise_for_status()
    return s.content


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    )
    return float(out.decode().strip())


def make_padded_wav(scene: Scene, raw_wav_path: Path, out_path: Path) -> None:
    """Pad a raw WAV to scene.duration with lead-in + trail-out silence."""
    raw_dur = ffprobe_duration(raw_wav_path)
    if raw_dur > scene.duration - LEAD_IN_SEC - TRAIL_OUT_SEC:
        info(f"  WARN [{scene.id}] narration {raw_dur:.2f}s tight vs scene {scene.duration:.1f}s")

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(raw_wav_path),
            "-af", f"adelay={int(LEAD_IN_SEC * 1000)}|{int(LEAD_IN_SEC * 1000)},apad=whole_dur={scene.duration}",
            "-ar", "24000", "-ac", "1",
            str(out_path),
        ],
        check=True,
    )


def concat_narration(scene_padded_wavs: list[Path], out_path: Path) -> None:
    concat_list = TEMP_DIR / "concat_audio.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in scene_padded_wavs),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(out_path),
        ],
        check=True,
    )


def record_demo() -> Path:
    """Record the demo flow with Playwright; return the WebM path."""
    from playwright.sync_api import sync_playwright

    info("Playwright Chromium launching... (initial nav)")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--hide-scrollbars"],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(TEMP_DIR),
            record_video_size=VIEWPORT,
        )
        page = context.new_page()

        for scene in SCENES:
            t0 = time.time()
            info(f"  [{scene.id}] {scene.narration[:30]}... (target {scene.duration}s)")
            scene.action(page)
            elapsed = time.time() - t0
            remaining = max(0.5, scene.duration - elapsed)
            page.wait_for_timeout(int(remaining * 1000))

        context.close()  # flush video
        browser.close()

    webms = sorted(TEMP_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not webms:
        raise RuntimeError(f"no WebM produced in {TEMP_DIR}")
    return webms[-1]


def _fmt_srt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def generate_srt(out_path: Path) -> None:
    lines: list[str] = []
    cum = 0.0
    for i, scene in enumerate(SCENES, 1):
        start = cum + LEAD_IN_SEC
        end = cum + scene.duration - TRAIL_OUT_SEC
        cum += scene.duration
        lines.append(f"{i}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{scene.narration}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def compose_final(webm: Path, narration: Path, out_mp4: Path) -> None:
    """WebM + narration -> MP4 (1080p / H.264 / AAC) + subtitles + closing credit."""
    credit_path = TEMP_DIR / "credit.txt"
    credit_path.write_text(
        "surfaceseal Demo (PoC) / TTS: AivisSpeech (JP narrator) / synthetic data only",
        encoding="utf-8",
    )

    srt_path = TEMP_DIR / "narration.srt"
    generate_srt(srt_path)

    fontfile_escaped = "C\\:/Windows/Fonts/YuGothM.ttc"
    textfile_escaped = credit_path.as_posix().replace(":", "\\:")
    srt_escaped = srt_path.as_posix().replace(":", "\\:")

    narration_dur = ffprobe_duration(narration)
    enable_from = max(0.0, narration_dur - 7.0)

    subtitles_filter = (
        f"subtitles='{srt_escaped}':"
        "force_style='FontName=Yu Gothic UI Semibold,"
        "Fontsize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
        "BackColour=&H80000000&,BorderStyle=1,Outline=2,Shadow=1,"
        "MarginV=30,Alignment=2'"
    )

    drawtext_filter = (
        f"drawtext=fontfile='{fontfile_escaped}':"
        f"textfile='{textfile_escaped}':"
        "fontcolor=white:fontsize=26:"
        "x=(w-text_w)/2:y=h-th-40:"
        "box=1:boxcolor=black@0.75:boxborderw=14:"
        f"enable='gte(t,{enable_from:.2f})'"
    )

    if os.environ.get("SKIP_CREDIT_OVERLAY", "0") == "1":
        vf_chain = subtitles_filter
    else:
        vf_chain = f"{subtitles_filter},{drawtext_filter}"

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(webm),
            "-i", str(narration),
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-metadata", "comment=surfaceseal Demo PoC / synthetic data only",
            str(out_mp4),
        ],
        check=True,
    )


# ─── main orchestrator ───────────────────────────────────────────────

def main() -> int:
    narration_only = "--narration-only" in sys.argv
    info("=== surfaceseal demo video pipeline ===")
    if narration_only:
        info("(--narration-only: TTS synthesis only, skip Playwright + ffmpeg)")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    info("\n[0/3] precondition check")
    if narration_only:
        try:
            r = requests.get(f"{ENGINE_URL}/version", timeout=3)
            assert r.status_code == 200
            info(f"OK TTS engine live ({ENGINE_URL}/version = {r.text.strip()})")
        except Exception as e:
            info(f"TTS engine down: {ENGINE_URL} ({e})")
            sys.exit(1)
        if shutil.which("ffmpeg") is None:
            info("ffmpeg not on PATH")
            sys.exit(1)
        info(f"OK ffmpeg ({shutil.which('ffmpeg')})")
    else:
        check_preconditions()

    info(f"\n[1/3] synthesize {len(SCENES)} scene narration WAVs + auto-sync + pad")
    AUTO_SYNC_MARGIN_SEC = 0.3
    padded_wavs: list[Path] = []
    sync_adjustments: list[tuple[str, float, float]] = []
    for scene in SCENES:
        raw = TEMP_DIR / f"{scene.id}_raw.wav"
        padded = TEMP_DIR / f"{scene.id}_padded.wav"
        wav_bytes = aivis_synthesize(scene.narration)
        raw.write_bytes(wav_bytes)
        actual_raw = ffprobe_duration(raw)
        required = actual_raw + LEAD_IN_SEC + TRAIL_OUT_SEC + AUTO_SYNC_MARGIN_SEC
        if required > scene.duration:
            old_dur = scene.duration
            scene.duration = round(required, 1)
            sync_adjustments.append((scene.id, old_dur, scene.duration))
        make_padded_wav(scene, raw, padded)
        padded_wavs.append(padded)
        info(f"  [{scene.id}] raw={actual_raw:.2f}s -> scene.duration={scene.duration}s padded")
    if sync_adjustments:
        info(f"  [auto-sync] {len(sync_adjustments)} scene(s) auto-extended (overflow guard):")
        for sid, old, new in sync_adjustments:
            info(f"    {sid}: {old}s -> {new}s")

    narration_wav = TEMP_DIR / "narration_full.wav"
    concat_narration(padded_wavs, narration_wav)
    total_audio = ffprobe_duration(narration_wav)
    info(f"  narration joined: {narration_wav.name} = {total_audio:.2f}s")

    if narration_only:
        listen_path = OUTPUT_DIR / "narration_only_preview.wav"
        shutil.copy(narration_wav, listen_path)
        info("\n=== --narration-only Done ===")
        info(f"  preview WAV: {listen_path.relative_to(BASE_DIR)} ({total_audio:.2f}s)")
        return 0

    info(f"\n[2/3] record demo flow with Playwright (target total = {sum(s.duration for s in SCENES):.1f}s)")
    webm = record_demo()
    video_dur = ffprobe_duration(webm)
    info(f"  WebM: {webm.name} = {video_dur:.2f}s")

    info("\n[3/3] compose MP4 with ffmpeg + subtitle burn-in + closing credit")
    out_mp4 = OUTPUT_DIR / "surfaceseal_demo.mp4"
    compose_final(webm, narration_wav, out_mp4)
    final_dur = ffprobe_duration(out_mp4)
    size_mb = out_mp4.stat().st_size / 1024 / 1024
    info(f"  done: {out_mp4} = {final_dur:.2f}s / {size_mb:.1f} MB")

    info("\n=== Done ===")
    info(f"video = {out_mp4.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""PropVid web app. Run with: streamlit run app.py"""

import json
import tempfile
import time
import traceback
from pathlib import Path

import streamlit as st

from propvid import config
from propvid.config import RenderOptions
from propvid.errors import InputError
from propvid.pipeline import generate_video
from propvid.validation import IMAGE_EXTENSIONS, MAX_IMAGES, MIN_IMAGES

ROOT = Path(__file__).parent
SAMPLE_JSON = ROOT / "samples" / "sample_property.json"
OUTPUT_DIR = ROOT / "output" / "web"
FIELDS = ["name", "location", "price", "property_type", "features", "cta", "contact"]

st.set_page_config(page_title="PropVid: property video generator", page_icon="🏠", layout="wide")


def load_sample() -> None:
    """Pre-fill the form from the sample listing (runs as a button callback, before widgets render)."""
    data = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    for key in FIELDS:
        value = data.get(key, "")
        st.session_state[key] = "\n".join(value) if isinstance(value, list) else value
    st.session_state["sample_images"] = [str((SAMPLE_JSON.parent / p).resolve()) for p in data.get("images", [])]


def clear_form() -> None:
    for key in FIELDS:
        st.session_state[key] = ""
    st.session_state["sample_images"] = []
    st.session_state.pop("result", None)


def save_uploads(files, folder: Path) -> list[str]:
    paths = []
    for i, f in enumerate(files):
        target = folder / f"{i:02d}_{Path(f.name).name}"
        target.write_bytes(f.getbuffer())
        paths.append(str(target))
    return paths


st.title("PropVid")
st.caption("Turn property details and 4–8 photos into a 20–40 second video you can share. No video editor needed.")

form_col, result_col = st.columns([1, 1], gap="large")

with form_col:
    b1, b2, _ = st.columns([1, 1, 2])
    b1.button("Load sample listing", on_click=load_sample, width="stretch")
    b2.button("Clear", on_click=clear_form, width="stretch")

    with st.form("property_form"):
        st.text_input("Property name *", key="name", placeholder="Skyline Residency")
        c1, c2 = st.columns(2)
        c1.text_input("Location", key="location", placeholder="Whitefield, Bengaluru")
        c2.text_input("Price", key="price", placeholder="₹85 Lakh")
        st.text_input("Property type", key="property_type", placeholder="2 BHK Apartment")
        st.text_area("Key features (one per line, up to 5)", key="features", height=130,
                     placeholder="1,150 sq ft carpet area\nEast-facing balcony\nCovered parking")
        c3, c4 = st.columns(2)
        c3.text_input("Call to action", key="cta", placeholder="Book your site visit today")
        c4.text_input("Contact", key="contact", placeholder="Call +91 90000 00000")

        uploads = st.file_uploader(
            f"Property photos ({MIN_IMAGES}–{MAX_IMAGES} recommended)",
            type=[e.lstrip(".") for e in sorted(IMAGE_EXTENSIONS)],
            accept_multiple_files=True,
        )
        sample_images = st.session_state.get("sample_images") or []
        if sample_images and not uploads:
            st.caption(f"Using {len(sample_images)} sample photos. Upload your own to replace them.")

        st.markdown("**Options**")
        orientation = st.radio("Format", ["vertical", "horizontal"], horizontal=True,
                               format_func=lambda v: "Vertical 9:16 (Reels, WhatsApp)" if v == "vertical" else "Horizontal 16:9")
        narration = st.toggle("Narration (offline voice)", value=True)
        music = st.toggle("Background music", value=True)
        ai_available = config.has_api_key()
        use_ai = st.toggle(
            "AI-written script (Claude)", value=False, disabled=not ai_available,
            help="Uses Claude to write the captions and narration. The output is fact-checked against your input, "
                 "and the template script is used if the check fails." if ai_available
            else "Set ANTHROPIC_API_KEY in .env to enable. The template script is used otherwise.",
        )
        submitted = st.form_submit_button("Generate video", type="primary", width="stretch")

with result_col:
    if submitted:
        st.session_state.pop("result", None)
        data = {key: st.session_state.get(key, "") for key in FIELDS}
        options = RenderOptions(orientation=orientation, narration=narration, music=music, use_ai=use_ai)
        bar = st.progress(0.0, text="Starting")
        started = time.perf_counter()
        try:
            with tempfile.TemporaryDirectory(prefix="propvid_upload_") as tmp:
                data["images"] = save_uploads(uploads, Path(tmp)) if uploads else sample_images
                out = OUTPUT_DIR / f"propvid_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
                result = generate_video(data, out, options,
                                        progress=lambda f, label: bar.progress(min(max(f, 0.0), 1.0), text=label))
            st.session_state["result"] = {"result": result, "seconds": time.perf_counter() - started}
        except InputError as exc:
            st.error(f"**Please fix the input:** {exc}")
        except Exception as exc:  # noqa: BLE001 - show a readable message instead of a stack trace
            st.error(f"Something went wrong while making the video: {exc}")
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
        finally:
            bar.empty()

    stored = st.session_state.get("result")
    if stored:
        result = stored["result"]
        st.success(f"Video ready: {result.duration:.1f} s, made in {stored['seconds']:.0f} s.")
        for warning in result.warnings:
            st.warning(warning)
        video_bytes = result.output_path.read_bytes()
        # a 9:16 video at full column width would be taller than the screen
        st.video(video_bytes, width=340 if result.vertical else "stretch")
        st.download_button("Download MP4", video_bytes, file_name=result.output_path.name,
                           mime="video/mp4", width="stretch")
        source = "AI (Claude, fact-checked)" if result.script.source == "ai" else "template"
        with st.expander(f"Script used ({source})", expanded=False):
            st.table([
                {"Scene": i, "Type": s.kind, "Seconds": f"{s.duration:.1f}", "On screen": s.caption,
                 "Narration": s.narration or "(music only)"}
                for i, s in enumerate(result.script.scenes, 1)
            ])
    elif not submitted:
        st.info("Fill the form or click **Load sample listing**, then **Generate video**. "
                "Rendering takes about 30–90 seconds.")

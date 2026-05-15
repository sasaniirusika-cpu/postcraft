import streamlit as st
from PIL import Image, ImageDraw, ImageFilter
import io
import json
import base64
import requests
import anthropic
from streamlit_drawable_canvas import st_canvas
from data import TEMPLATES, UNSPLASH_PHOTOS, GRADIENTS
from image_utils import (
    make_gradient_bg, load_photo_bg, build_post,
    get_font, hex_to_rgb, sketch_to_post_prompt, CANVAS_SIZE
)

st.set_page_config(
    page_title="PostCraft — Institute Post Maker",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Noto+Sans+Sinhala:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', 'Noto Sans Sinhala', sans-serif; }
.pc-header { background: linear-gradient(135deg, #13131f 0%, #1a1a2e 100%); border: 1px solid #ffffff14; border-radius: 16px; padding: 1.5rem 2rem; margin-bottom: 1.5rem; }
.pc-logo { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; color: #f0eeff; letter-spacing: -0.03em; }
.pc-logo span { color: #7c5cfc; }
.pc-sub { font-size: 13px; color: #8885aa; margin-top: 2px; }
.stTabs [data-baseweb="tab-list"] { background: #13131f; border-radius: 12px; padding: 4px; gap: 4px; border: 1px solid #ffffff0f; }
.stTabs [data-baseweb="tab"] { border-radius: 9px; color: #8885aa; font-weight: 600; font-size: 13px; padding: 8px 20px; }
.stTabs [aria-selected="true"] { background: #1a1a2e !important; color: #f0eeff !important; border: 1px solid #ffffff20 !important; }
section[data-testid="stSidebar"] { background: #13131f; border-right: 1px solid #ffffff0f; }
.stButton > button { border-radius: 10px !important; font-weight: 600 !important; font-size: 13px !important; border: 1px solid #ffffff20 !important; background: #1a1a2e !important; color: #f0eeff !important; }
.stButton > button:hover { border-color: #7c5cfc !important; background: #20203a !important; }
.sec-head { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #7c5cfc; margin: 1rem 0 0.5rem; }
.ai-box { background: #1a1a2e; border: 1px solid #ffffff14; border-radius: 12px; padding: 1rem; font-family: 'Noto Sans Sinhala', sans-serif; font-size: 14px; line-height: 1.8; color: #f0eeff; white-space: pre-wrap; margin-top: 0.75rem; }
.info-box { background: rgba(124,92,252,0.1); border: 1px solid rgba(124,92,252,0.3); border-radius: 10px; padding: 0.75rem 1rem; font-size: 13px; color: #c4b5fd; margin: 0.5rem 0; }
.stTextInput input, .stTextArea textarea { background: #13131f !important; border: 1px solid #ffffff14 !important; border-radius: 8px !important; color: #f0eeff !important; }
hr { border-color: #ffffff0f !important; }
</style>
""", unsafe_allow_html=True)

def init_state():
    defaults = {
        "bg_image": None, "bg_type": "gradient", "bg_gradient_idx": 0,
        "logo_img": None, "generated_post": None, "ai_caption": "",
        "ai_result": "", "saved_posts": [], "beautify": False,
        "form": {
            "institute": "", "course": "", "tagline": "",
            "bullets": "📚 ඉහළ ප්‍රමිතියේ අධ්‍යාපනය\n🏆 සුදුසුකම් ලත් ගුරු මඩුල්ල\n🎯 100% රැකියා සහාය\n📜 සහතිකය ලබා දේ",
            "cta": "අදම ලියාපදිංචි වන්න!", "phone": "", "website": "",
            "accent": "#a78bfa", "accent2": "#60a5fa",
        }
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def img_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def get_bg():
    if st.session_state.bg_image is not None:
        return st.session_state.bg_image.copy()
    idx = st.session_state.bg_gradient_idx
    colors = GRADIENTS[idx]["colors"]
    return make_gradient_bg(colors)

def render_post():
    f = st.session_state.form
    bullets = [b.strip() for b in f["bullets"].split("\n") if b.strip()][:6]
    bg = get_bg()
    post = build_post(
        bg_image=bg, institute_name=f["institute"], course_name=f["course"],
        tagline=f["tagline"], bullets=bullets, cta=f["cta"],
        phone=f["phone"], website=f["website"],
        accent=hex_to_rgb(f["accent"]), accent2=hex_to_rgb(f["accent2"]),
        logo_img=st.session_state.logo_img,
        add_vignette_=st.session_state.beautify, add_noise_=True,
    )
    st.session_state.generated_post = post
    return post

def apply_template(tname):
    t = TEMPLATES[tname]
    f = st.session_state.form
    f["course"] = t["title_si"]
    f["tagline"] = t["subtitle_si"]
    f["bullets"] = "\n".join(t["bullets_si"])
    f["cta"] = t["cta_si"]
    st.session_state.bg_image = make_gradient_bg(t["gradient"])
    r, g, b = t["accent"]
    f["accent"] = "#{:02x}{:02x}{:02x}".format(r, g, b)
    r2, g2, b2 = t["accent2"]
    f["accent2"] = "#{:02x}{:02x}{:02x}".format(r2, g2, b2)

st.markdown('<div class="pc-header"><div class="pc-logo">Post<span>Craft</span></div><div class="pc-sub">✦ Institute Social Media Post Maker · Sinhala + English · AI Powered</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="sec-head">⚙️ Post Details</div>', unsafe_allow_html=True)
    f = st.session_state.form
    f["institute"] = st.text_input("Institute Name", value=f["institute"], placeholder="e.g. Excel Academy")
    f["course"] = st.text_area("Course / Title (Sinhala)", value=f["course"], placeholder="e.g. වෙබ් ඩිසයිනිං", height=90)
    f["tagline"] = st.text_input("Tagline", value=f["tagline"], placeholder="e.g. ඔබේ අනාගතය සකසන්න")
    f["bullets"] = st.text_area("Bullet Points (one per line)", value=f["bullets"], height=130)
    f["cta"] = st.text_input("Call to Action", value=f["cta"])
    col1, col2 = st.columns(2)
    with col1: f["phone"] = st.text_input("Phone", value=f["phone"])
    with col2: f["website"] = st.text_input("Website", value=f["website"])
    col1, col2 = st.columns(2)
    with col1: f["accent"] = st.color_picker("Accent 1", value=f["accent"])
    with col2: f["accent2"] = st.color_picker("Accent 2", value=f["accent2"])
    st.markdown("---")
    logo_file = st.file_uploader("Upload Logo", type=["png","jpg","jpeg","webp"])
    if logo_file:
        st.session_state.logo_img = Image.open(logo_file)
        st.image(st.session_state.logo_img, width=100)
    if st.session_state.logo_img and st.button("❌ Remove Logo"):
        st.session_state.logo_img = None
    st.markdown("---")
    st.session_state.beautify = st.toggle("🪄 Magic Beautify", value=st.session_state.beautify)
    st.markdown("---")
    if st.button("✨ Generate Post", use_container_width=True, type="primary"):
        with st.spinner("Creating your post..."):
            render_post()
        st.success("Post generated!")

tab_preview, tab_templates, tab_bg, tab_draw, tab_ai, tab_save = st.tabs([
    "🖼 Preview & Export", "📋 Templates", "🌄 Backgrounds",
    "✏️ Draw & Sketch → AI", "✨ AI Helper", "💾 Save & Load",
])

with tab_preview:
    col_prev, col_exp = st.columns([2, 1])
    with col_prev:
        st.markdown('<div class="sec-head">🖼 Post Preview</div>', unsafe_allow_html=True)
        if st.session_state.generated_post:
            st.image(st.session_state.generated_post, use_column_width=True)
        else:
            st.markdown('<div class="info-box">👈 Fill the sidebar form → Click <b>Generate Post</b> to start. Or pick a template!</div>', unsafe_allow_html=True)
    with col_exp:
        st.markdown('<div class="sec-head">📥 Export HD</div>', unsafe_allow_html=True)
        if st.session_state.generated_post:
            post = st.session_state.generated_post
            st.download_button("⬇️ Square (1080×1080)", img_to_bytes(post),
                file_name="postcraft_square.png", mime="image/png", use_container_width=True)
            story = Image.new("RGB", (1080, 1920), (10, 10, 25))
            story.paste(post, (0, (1920-1080)//2))
            st.download_button("⬇️ Story (1080×1920)", img_to_bytes(story),
                file_name="postcraft_story.png", mime="image/png", use_container_width=True)
            st.markdown("---")
            if st.button("🔄 Regenerate", use_container_width=True):
                with st.spinner("Regenerating..."): render_post()
                st.rerun()

with tab_templates:
    st.markdown('<div class="sec-head">📋 Ready Institute Templates</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (tname, tdata) in enumerate(TEMPLATES.items()):
        with cols[i % 3]:
            r, g, b = tdata["accent"]
            r2, g2, b2 = tdata["gradient"][0]
            st.markdown(f'<div style="background:linear-gradient(135deg,#{r2:02x}{g2:02x}{b2:02x},#{r:02x}{g:02x}{b:02x}22);border-radius:12px;padding:14px;margin-bottom:8px;border:1px solid rgba(255,255,255,0.12)"><div style="font-size:22px">{tname.split()[0]}</div><div style="font-weight:700;color:#fff;font-size:13px">{tname[2:]}</div><div style="font-size:11px;color:#{r:02x}{g:02x}{b:02x}">{tdata["title_si"]}</div></div>', unsafe_allow_html=True)
            if st.button(f"Use Template", key=f"tmpl_{i}", use_container_width=True):
                apply_template(tname)
                with st.spinner("Applying..."): render_post()
                st.success(f"✅ Applied!")
                st.rerun()

with tab_bg:
    bg_tab1, bg_tab2, bg_tab3, bg_tab4 = st.tabs(["📸 Photos", "🎨 Gradients", "🎨 Solid Color", "📁 Upload"])
    with bg_tab1:
        st.markdown('<div class="sec-head">📸 Education Photo Backgrounds</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, photo in enumerate(UNSPLASH_PHOTOS):
            with cols[i % 4]:
                st.image(photo["url"], caption=photo["label"], use_column_width=True)
                if st.button("Use", key=f"photo_{i}", use_container_width=True):
                    with st.spinner(f"Loading {photo['label']}..."):
                        st.session_state.bg_image = load_photo_bg(photo["url"])
                    st.success("✅ Set!")
    with bg_tab2:
        st.markdown('<div class="sec-head">🎨 Gradient Backgrounds</div>', unsafe_allow_html=True)
        cols = st.columns(5)
        for i, grad in enumerate(GRADIENTS):
            with cols[i % 5]:
                preview = make_gradient_bg(grad["colors"], size=200)
                st.image(preview, caption=grad["label"], use_column_width=True)
                if st.button("Use", key=f"grad_{i}", use_container_width=True):
                    st.session_state.bg_image = make_gradient_bg(grad["colors"])
                    st.session_state.bg_gradient_idx = i
                    st.success("✅ Set!")
    with bg_tab3:
        bg_color = st.color_picker("Pick color", value="#0f0c29")
        if st.button("Apply Color", use_container_width=True):
            from PIL import Image as PILImage
            rgb = hex_to_rgb(bg_color)
            st.session_state.bg_image = PILImage.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), rgb)
            st.success("✅ Applied!")
    with bg_tab4:
        st.markdown('<div class="sec-head">📁 Upload Your Own Background</div>', unsafe_allow_html=True)
        uploaded_bg = st.file_uploader("Upload image", type=["png","jpg","jpeg","webp"])
        if uploaded_bg:
            from PIL import ImageEnhance
            img = Image.open(uploaded_bg).convert("RGB")
            w, h = img.size; m = min(w, h)
            img = img.crop(((w-m)//2, (h-m)//2, (w+m)//2, (h+m)//2))
            img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)
            darkness = st.slider("Darken", 0.1, 1.0, 0.45, 0.05)
            img_dark = ImageEnhance.Brightness(img).enhance(darkness)
            st.image(img_dark, use_column_width=True)
            if st.button("✅ Use This Background", use_container_width=True):
                st.session_state.bg_image = img_dark
                st.success("✅ Set!")

with tab_draw:
    st.markdown('<div class="sec-head">✏️ Draw Sketch → AI Makes Real Post</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">🎨 Draw your post idea → describe it → AI generates all Sinhala text automatically!</div>', unsafe_allow_html=True)
    col_draw, col_ctrl = st.columns([3, 1])
    with col_ctrl:
        draw_tool = st.selectbox("Tool", ["freedraw","line","rect","circle","transform"])
        stroke_color = st.color_picker("Color", "#a78bfa")
        stroke_width = st.slider("Size", 1, 40, 4)
        bg_draw_color = st.color_picker("Canvas BG", "#1a1a2e")
        st.markdown("---")
        sketch_desc = st.text_area("Describe your sketch", placeholder="e.g. Big title at top, 3 bullet points, phone number at bottom. For Web Design course admission.", height=120)
        api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.get("api_key",""), placeholder="sk-ant-...")
        if api_key: st.session_state["api_key"] = api_key
        gen_sketch = st.button("🪄 Sketch → Real Post", use_container_width=True, type="primary")
    with col_draw:
        canvas_result = st_canvas(
            fill_color="rgba(167,139,250,0.2)", stroke_width=stroke_width,
            stroke_color=stroke_color, background_color=bg_draw_color,
            height=540, width=540, drawing_mode=draw_tool, key="canvas_main", display_toolbar=True,
        )
    if gen_sketch:
        if not sketch_desc.strip(): st.error("Please describe your sketch!")
        elif not api_key: st.error("Please enter your API key.")
        else:
            with st.spinner("🪄 AI is creating your post..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    msg = client.messages.create(
                        model="claude-opus-4-5", max_tokens=800,
                        messages=[{"role":"user","content":sketch_to_post_prompt(sketch_desc, st.session_state.form["institute"])}]
                    )
                    raw = msg.content[0].text.strip()
                    if "```" in raw: raw = raw.split("```")[1]; raw = raw[4:] if raw.startswith("json") else raw
                    data = json.loads(raw)
                    f = st.session_state.form
                    f["course"] = data.get("course_name", f["course"])
                    f["tagline"] = data.get("tagline", f["tagline"])
                    f["bullets"] = "\n".join(data.get("bullets", []))
                    f["cta"] = data.get("cta", f["cta"])
                    render_post()
                    st.success("✅ AI transformed your sketch into a real post!")
                    if data.get("caption_fb"):
                        st.markdown('<div class="sec-head">📘 Facebook Caption</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="ai-box">{data["caption_fb"]}</div>', unsafe_allow_html=True)
                        st.download_button("📋 Copy FB Caption", data["caption_fb"], file_name="caption_fb.txt")
                    if data.get("caption_ig"):
                        st.markdown('<div class="sec-head">📸 Instagram Caption</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="ai-box">{data["caption_ig"]}</div>', unsafe_allow_html=True)
                    if data.get("hashtags"):
                        st.markdown('<div class="sec-head">🏷 Hashtags</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="ai-box">{data["hashtags"]}</div>', unsafe_allow_html=True)
                    st.rerun()
                except Exception as e: st.error(f"Error: {str(e)}")

with tab_ai:
    st.markdown('<div class="sec-head">✨ AI Creative Helper</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        ai_mode = st.selectbox("What do you need?", [
            "📝 Full caption (Sinhala + English)", "🇱🇰 Sinhala only",
            "📸 Instagram caption + hashtags", "📘 Facebook post",
            "🔥 Make it more exciting", "🏷 Hashtags only",
        ])
        ai_topic = st.text_area("Your topic", placeholder="e.g. Web Design course, 3 months, starts January, fee 15000", height=120)
        api_key_ai = st.text_input("Anthropic API Key", type="password", value=st.session_state.get("api_key",""), key="ai_key", placeholder="sk-ant-...")
        if api_key_ai: st.session_state["api_key"] = api_key_ai
        if st.button("✨ Generate", use_container_width=True, type="primary"):
            if not ai_topic.strip(): st.error("Please enter a topic.")
            elif not api_key_ai: st.error("Please enter your API key.")
            else:
                prompts = {
                    "📝 Full caption (Sinhala + English)": f"Write a professional social media caption for a Sri Lankan educational institute in BOTH Sinhala and English. Topic: {ai_topic}. Include emojis. Max 200 words.",
                    "🇱🇰 Sinhala only": f"Write beautiful Sinhala social media text for an educational institute about: {ai_topic}. Use proper Sinhala. Include emojis.",
                    "📸 Instagram caption + hashtags": f"Write an Instagram caption with emojis for a Sri Lankan institute about: {ai_topic}. Include 15 hashtags in Sinhala and English.",
                    "📘 Facebook post": f"Write a Facebook post for a Sri Lankan institute about: {ai_topic}. Mix Sinhala and English. Include CTA.",
                    "🔥 Make it more exciting": f"Rewrite this to be more exciting for Sri Lankan students: {ai_topic}. Use Sinhala and English.",
                    "🏷 Hashtags only": f"Generate 20 hashtags in Sinhala and English for a Sri Lankan institute post about: {ai_topic}.",
                }
                with st.spinner("AI is writing..."):
                    try:
                        client = anthropic.Anthropic(api_key=api_key_ai)
                        msg = client.messages.create(model="claude-opus-4-5", max_tokens=600,
                            messages=[{"role":"user","content":prompts[ai_mode]}])
                        st.session_state.ai_result = msg.content[0].text
                    except Exception as e: st.error(f"Error: {str(e)}")
    with col2:
        if st.session_state.ai_result:
            st.markdown('<div class="sec-head">✅ AI Output</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-box">{st.session_state.ai_result}</div>', unsafe_allow_html=True)
            st.download_button("📋 Download as text", st.session_state.ai_result, file_name="caption.txt", use_container_width=True)

with tab_save:
    st.markdown('<div class="sec-head">💾 Save & Load Posts</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💾 Save Current Post")
        save_name = st.text_input("Save name", placeholder="e.g. Web Design January 2025")
        if st.button("💾 Save Post", use_container_width=True):
            if not save_name.strip(): st.error("Enter a name.")
            else:
                entry = {"name": save_name, "form": dict(st.session_state.form), "beautify": st.session_state.beautify}
                st.session_state.saved_posts.append(entry)
                st.success(f"✅ Saved: {save_name}")
        if st.session_state.saved_posts:
            st.download_button("⬇️ Download all saves (JSON)",
                json.dumps(st.session_state.saved_posts, indent=2),
                file_name="postcraft_saves.json", mime="application/json", use_container_width=True)
        import_file = st.file_uploader("📥 Import saves JSON", type=["json"])
        if import_file:
            st.session_state.saved_posts = json.load(import_file)
            st.success(f"✅ Loaded {len(st.session_state.saved_posts)} saves!")
    with col2:
        st.markdown("#### 📂 Saved Posts")
        if not st.session_state.saved_posts:
            st.markdown('<div class="info-box">No saved posts yet.</div>', unsafe_allow_html=True)
        for i, post in enumerate(reversed(st.session_state.saved_posts)):
            idx = len(st.session_state.saved_posts) - 1 - i
            cols = st.columns([3,1,1])
            with cols[0]: st.markdown(f"**{post['name']}**")
            with cols[1]:
                if st.button("📂", key=f"load_{i}", use_container_width=True):
                    st.session_state.form = dict(post["form"])
                    st.session_state.beautify = post.get("beautify", False)
                    render_post(); st.rerun()
            with cols[2]:
                if st.button("🗑", key=f"del_{i}", use_container_width=True):
                    st.session_state.saved_posts.pop(idx); st.rerun()
            st.markdown("---")

st.markdown('<div style="text-align:center;padding:2rem 0 1rem;color:#3a385a;font-size:12px">PostCraft · Institute Post Maker · Streamlit + Claude AI · Sinhala + English</div>', unsafe_allow_html=True)

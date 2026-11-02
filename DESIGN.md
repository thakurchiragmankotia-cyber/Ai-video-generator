# DESIGN — PropVid visual system

PropVid has two visual surfaces: the **video itself** (most important) and a **Streamlit form**.
Every colour, font and size used in code comes from this file. The video tokens live in
`propvid/theme.py`; the UI tokens live in `.streamlit/config.toml` and `app.py`.

## 1. Brand feel

Calm, premium and trustworthy, like a good property brochure. The photos are the hero, and the text
supports them without shouting.

**Design principles**
1. **Photo first.** Text never covers more than the bottom ~35% of the frame. The image stays visible.
2. **Readable on a phone in 2 seconds.** Large bold type, high contrast, one idea per scene.
3. **Only true things.** No decorative badges or claims ("Hot deal!") that the input didn't provide.

## 2. Colour palette

The video is always rendered on photos, so it uses one palette. The UI follows Streamlit's light
and dark themes, using these tokens as primary/accent.

| Token | HEX | Use |
|---|---|---|
| `primary` | `#0F3D3E` | Deep teal: CTA card, placeholders, UI primary button |
| `secondary` | `#C8A45C` | Muted gold: accent bar, price tag, progress dots |
| `background` (UI light) | `#F7F5F0` | App background |
| `background` (UI dark) | `#121615` | App background in dark mode |
| `surface` (UI light / dark) | `#FFFFFF` / `#1C2221` | Cards, inputs |
| `text` (on photo) | `#FFFFFF` | All video captions |
| `text` (UI light / dark) | `#1A1F1E` / `#ECEFEE` | Body text |
| `text_muted` | `#D9D4C7` (video), `#5B6563` (UI) | Secondary lines (location, labels) |
| `scrim` | `#000000` at 0→78% alpha | Bottom gradient behind captions |
| `success` | `#2E7D5B` | "Video ready" |
| `warning` | `#B7791F` | Non-blocking warnings (image reused, TTS unavailable) |
| `error` | `#B3261E` | Blocking validation errors |

Contrast: white text on the 78% scrim measures above 7:1 against any photo (WCAG AAA). Gold `#C8A45C`
is used for fills behind dark text (`#0F3D3E`), never as text on photos.

## 3. Typography

- **Font family:** a bold sans-serif from the system, tried in order: Segoe UI Bold → Arial Bold →
  DejaVu Sans Bold → Liberation Sans Bold → Helvetica → Pillow's bundled font. The regular weight
  follows the same order.
- **Scale (vertical 720×1280; horizontal scales by frame height ÷ 1280 × 1.6, capped at 1.0×):**

| Role | Size px | Weight | Line height |
|---|---|---|---|
| Title (property name) | 64 | Bold | 1.15 |
| Caption (feature) | 52 | Bold | 1.2 |
| Subtitle (location, type) | 34 | Regular | 1.3 |
| Price tag | 38 | Bold | 1.0 |
| Label ("Feature 2 of 4") | 24 | Bold, letter-spaced, uppercase | 1.0 |
| CTA heading | 56 | Bold | 1.15 |
| CTA contact | 36 | Regular | 1.3 |

Captions wrap to a maximum of 3 lines, and the font steps down 10% at a time if the text still doesn't fit.

## 4. Spacing, radius, shadows, motion

- **Spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64 px. The safe margin is 48 px (vertical) or 40 px (horizontal).
- **Radius:** price tag and CTA card 16 px, labels 8 px.
- **Shadow:** text gets a 2 px offset, 6 px blur, 55% black drop shadow on top of the scrim.
- **Motion:**
  - Ken Burns zoom from 1.00 to 1.08 over the scene, with the direction alternating per scene.
  - Text fades in and slides up 24 px over 0.6 s, starting 0.3 s into the scene.
  - Crossfade of 0.6 s between scenes.
  - The last 0.8 s of the video fades the audio out.
- **Timing:** title scene 4 s, feature scenes 4–7 s (fit to narration + 0.8 s), CTA scene 5 s.

## 5. Video scene layouts

```
Title scene               Feature scene             CTA scene
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│              │          │ ● ● ○ ○      │ progress │   (photo,     │
│    photo     │          │    photo     │          │   darkened)   │
│              │          │              │          │ ┌──────────┐ │
│▓▓ TYPE label │          │▓▓ FEATURE 2/4│          │ │ CTA text │ │
│▓▓ Name (big) │          │▓▓ Caption    │          │ │ contact  │ │
│▓▓ Location   │          │▓▓ wraps ≤3   │          │ │ price    │ │
│▓▓ [₹ price]  │          │▓▓ lines      │          │ └──────────┘ │
└──────────────┘          └──────────────┘          └──────────────┘
▓ = bottom gradient scrim; [ ] = gold price tag;  CTA card = teal, 92% opacity, centred
```

If no image is available, the scene uses a teal→dark-teal gradient placeholder with the same layout.

## 6. UI components (Streamlit)

Streamlit draws its own components. We set the theme and use only these:

| Component | Usage | States |
|---|---|---|
| Primary button | "Generate video" | default (teal), hover (Streamlit darkens), disabled while rendering, loading = spinner + progress bar |
| Secondary button | "Load sample listing", "Download MP4" | default, hover, disabled |
| Text input / text area | Property fields; features one per line | default, focus (teal ring), error shown as `st.error` below the form |
| File uploader | 4–8 images | default, has files (shows thumbnails), error |
| Toggle / radio | narration, music, AI script, orientation | default, on, disabled (AI toggle disabled when no API key) |
| Alerts | `st.error` blocking, `st.warning` non-blocking, `st.success` done | — |
| Video player | `st.video` preview | — |

**Page layout (single screen):** a header with the title and one-line description, then two columns
on desktop (the form on the left, the result on the right). On a narrow viewport the columns stack.

## 7. Accessibility

- The video caption contrast is at least 7:1 (scrim + white). The minimum caption size is 34 px at 720p.
- Each scene shows text for at least 3 s, so it can be read.
- The narration says the same facts as the on-screen text.
- UI: Streamlit's native widgets are keyboard reachable and show a visible focus ring, and every input has a label.
- No information is given by colour alone. Errors always carry text.

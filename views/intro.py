"""
First-visit intro, about 3.6 seconds, once per browser session.

A light popup over the blurred page: a frosted glass prism tilts up into
view, a beam with a travelling gold spark enters it, light flashes at
the exit face and splits into five coloured lines that grow into a
rising line chart, each ending in a dot. "PRISM" then appears letter by letter with the tagline,
and the whole popup zooms gently away.

The drawing itself is static/prism-intro.svg (animated with SMIL/CSS
inside the file), because Streamlit strips inline <svg> from st.html.
No JavaScript; it never blocks clicks once it has faded.
"""

import streamlit as st

LETTERS = "PRISM"

_letters_html = "".join(
    f'<span style="animation-delay:{1.35 + i * 0.07:.2f}s">{ch}</span>'
    for i, ch in enumerate(LETTERS)
)

INTRO_HTML = """
<style>
.pi-overlay {
  position: fixed; inset: 0; z-index: 1000000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(244, 246, 248, 0.72);
  backdrop-filter: blur(8px) saturate(0.9); -webkit-backdrop-filter: blur(8px) saturate(0.9);
  animation: pi-out 0.6s ease 3.05s forwards;
}
.pi-card {
  position: relative; overflow: hidden;
  background: radial-gradient(120% 100% at 50% 30%, #FFFFFF 0%, #FBFCFD 60%, #F2F5F8 100%);
  border: 1px solid #E3E8EE;
  border-radius: 22px; padding: 30px 40px 30px 40px;
  box-shadow: 0 30px 80px rgba(27, 37, 51, 0.18), 0 2px 10px rgba(27, 37, 51, 0.06);
  text-align: center;
  animation: pi-pop 0.6s cubic-bezier(.2,.9,.25,1.15) both,
             pi-leave 0.6s cubic-bezier(.5,0,.75,0) 3.05s forwards;
}
.pi-card::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(115deg, transparent 35%, rgba(31,78,121,0.05) 50%, transparent 65%);
  transform: translateX(-120%); animation: pi-sheen 1.1s ease 1.9s forwards;
}
.pi-art { display:block; width:400px; max-width:76vw; height:auto; margin:0 auto; }
.pi-word {
  font-family: Inter, sans-serif; font-weight: 700; font-size: 30px;
  letter-spacing: 0.38em; color: #1B2533; margin: 10px 0 6px 0.38em;
}
.pi-word span {
  display: inline-block; opacity: 0; transform: translateY(10px); filter: blur(4px);
  animation: pi-letter 0.5s cubic-bezier(.2,.8,.2,1) forwards;
}
.pi-tag {
  font-family: Inter, sans-serif; font-size: 13px; letter-spacing: 0.04em;
  color: #6B7480; opacity: 0; animation: pi-fade 0.6s ease 1.85s forwards;
}
.pi-rule {
  width: 0; height: 2px; margin: 12px auto 12px auto; border-radius: 2px;
  background: linear-gradient(90deg, #1F4E79, #2F8F9D, #C08A2E, #5E9A62, #8E5B9F);
  animation: pi-grow 0.6s ease 1.7s forwards;
}
@keyframes pi-letter { to { opacity: 1; transform: none; filter: none; } }
@keyframes pi-fade { to { opacity: 1; } }
@keyframes pi-grow { to { width: 64px; } }
@keyframes pi-sheen { to { transform: translateX(120%); } }
@keyframes pi-pop { from { transform: translateY(14px) scale(0.92); opacity: 0; }
                     to { transform: none; opacity: 1; } }
@keyframes pi-leave { to { transform: scale(1.06); opacity: 0; } }
@keyframes pi-out { to { opacity: 0; visibility: hidden; pointer-events: none; } }
@media (prefers-reduced-motion: reduce) {
  .pi-overlay { animation-delay: 0.8s; }
  .pi-card { animation: none; }
  .pi-word span, .pi-tag { animation-delay: 0s; animation-duration: 0.01s; }
  .pi-rule { animation-delay: 0s; animation-duration: 0.01s; }
}
</style>
<div class="pi-overlay" aria-hidden="true">
  <div class="pi-card">
    <img class="pi-art" src="/app/static/prism-intro.svg?v=4" alt="">
    <div class="pi-word">LETTERS_HTML</div>
    <div class="pi-rule"></div>
    <div class="pi-tag">Factor intelligence for Indian markets</div>
  </div>
</div>
""".replace("LETTERS_HTML", _letters_html)


def show():
    st.html(INTRO_HTML)

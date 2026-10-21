"""
First-visit intro: a small popup in which a beam of light enters a prism
and splits into coloured rays, then the PRISM wordmark appears and the
popup fades away on its own (about 3 seconds). Pure CSS/SVG, no
JavaScript, and it never blocks clicks once it has faded.

Shown once per browser session (see app.py).
"""

import streamlit as st

INTRO_HTML = """
<style>
.pi-overlay {
  position: fixed; inset: 0; z-index: 1000000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(244, 246, 248, 0.78);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  animation: pi-out 0.55s ease 2.75s forwards;
}
.pi-card {
  background: #fff; border-radius: 18px; padding: 34px 44px 30px 44px;
  box-shadow: 0 24px 60px rgba(27, 37, 51, 0.16), 0 2px 8px rgba(27, 37, 51, 0.06);
  text-align: center; animation: pi-pop 0.45s cubic-bezier(.2,.9,.3,1.2) both;
}
.pi-art { display:block; width:340px; max-width:72vw; height:auto; margin:0 auto; }
.pi-word {
  font-family: Inter, sans-serif; font-weight: 700; letter-spacing: 0.32em;
  font-size: 26px; color: #1B2533; margin: 18px 0 4px 0.32em;
  opacity: 0; animation: pi-fade 0.5s ease 1.45s forwards;
}
.pi-tag {
  font-family: Inter, sans-serif; font-size: 13px; color: #6B7480;
  opacity: 0; animation: pi-fade 0.5s ease 1.65s forwards;
}
@keyframes pi-fade { to { opacity: 1; } }
@keyframes pi-pop { from { transform: scale(0.94); opacity: 0; }
                     to { transform: scale(1); opacity: 1; } }
@keyframes pi-out { to { opacity: 0; visibility: hidden; pointer-events: none; } }
@media (prefers-reduced-motion: reduce) {
  .pi-overlay { animation-delay: 0.6s; }
  .pi-word, .pi-tag { animation-delay: 0s; }
}
</style>
<div class="pi-overlay" aria-hidden="true">
  <div class="pi-card">
    <img class="pi-art" src="/app/static/prism-intro.svg" alt="">
    <div class="pi-word">PRISM</div>
    <div class="pi-tag">Factor intelligence for Indian markets</div>
  </div>
</div>
"""


def show():
    st.html(INTRO_HTML)

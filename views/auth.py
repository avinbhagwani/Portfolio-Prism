"""
Google sign-in, using Streamlit's built-in OpenID Connect (st.login).

Signing in is optional: every page stays open to everyone. The sign-in
control only appears once Google credentials are configured, so the app
runs exactly as before locally or if the secret is missing.

Credentials live in a secrets.toml that is NEVER committed:
  * locally:   .streamlit/secrets.toml (git-ignored)
  * Cloud Run: Secret Manager secret "prism-auth", mounted at
               /root/.streamlit/secrets.toml (see cloudbuild.yaml)

    [auth]
    redirect_uri = "https://<your-site>/oauth2callback"
    cookie_secret = "<long random string>"
    client_id = "<...>.apps.googleusercontent.com"
    client_secret = "<...>"
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

Use signed_in() / user() from any page, e.g. to save game scores later.
"""

import streamlit as st


def enabled():
    """True when Google credentials are configured."""
    try:
        auth = st.secrets.get("auth", {})
        return bool(auth.get("client_id") and auth.get("redirect_uri"))
    except Exception:          # no secrets file at all
        return False


def signed_in():
    return enabled() and bool(getattr(st.user, "is_logged_in", False))


def user():
    """{'name', 'first', 'email', 'picture'} for the signed-in visitor, else None."""
    if not signed_in():
        return None
    name = st.user.get("name") or st.user.get("email", "")
    return {
        "name": name,
        "first": st.user.get("given_name") or name.split(" ")[0],
        "email": st.user.get("email", ""),
        "picture": st.user.get("picture", ""),
    }


CSS = """
<style>
.st-key-ph_auth {justify-content:flex-end; align-items:center; gap:0.6rem !important;
  margin:-1.2rem 0 1.2rem 0;}
.st-key-ph_auth .who {display:flex; align-items:center; gap:0.5rem; font-size:0.86rem; color:#66707C;}
.st-key-ph_auth .who img {width:24px; height:24px; border-radius:50%;}
.st-key-ph_auth .who b {color:#17212D; font-weight:500;}
.st-key-ph_auth button {border-radius:999px !important; min-height:2.1rem !important;
  padding:0.2rem 0.95rem !important; border:1px solid #D5DCE3 !important; background:#fff !important;}
.st-key-ph_auth button:hover {border-color:#1F4E79 !important; background:#F4F7FA !important;}
.st-key-ph_auth button p {font-size:0.86rem !important; font-weight:500 !important; color:#1F4E79 !important;}
</style>
"""


def control(key="ph_auth"):
    """Small top-right sign-in / signed-in strip. Renders nothing if not configured."""
    if not enabled():
        return
    st.markdown(CSS, unsafe_allow_html=True)
    u = user()
    with st.container(key=key, horizontal=True):
        if u:
            pic = f"<img src='{u['picture']}' alt=''>" if u["picture"] else ""
            st.markdown(f"<div class='who'>{pic}Signed in as <b>{u['first']}</b></div>",
                        unsafe_allow_html=True)
            if st.button("Sign out", key=f"{key}_out"):
                st.logout()
        else:
            if st.button("Sign in with Google", key=f"{key}_in",
                         icon=":material/account_circle:"):
                st.login()

"""Hyundai / Kia Connect – Streamlit UI"""
from __future__ import annotations

import datetime
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for p in (_ROOT, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
from cryptography.fernet import Fernet
from streamlit_cookies_controller import CookieController

from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.ApiImpl import OTPRequest
from hyundai_kia_connect_api.Token import Token
from hyundai_kia_connect_api.const import BRANDS, REGIONS, GEO_LOCATION_PROVIDERS, OTP_NOTIFY_TYPE
from hyundai_kia_connect_api.exceptions import AuthenticationError

_COOKIE_NAME = "kc_session"
_COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days

st.set_page_config(
    page_title="Hyundai / Kia Connect",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.brand-title {
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(135deg, #00b4d8, #0077b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 0.25rem;
}
.brand-sub { text-align: center; color: #6b7280; font-size: 0.9rem; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)


# ── Fernet encryption ──────────────────────────────────────────────────────────

_DEV_KEY_PATH = os.path.join(_HERE, ".cookie_key")


def _get_fernet() -> Fernet:
    key = os.environ.get("COOKIE_KEY")
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    # Local dev: persist a generated key to disk so it survives page reloads.
    if os.path.exists(_DEV_KEY_PATH):
        with open(_DEV_KEY_PATH, "rb") as f:
            dev_key = f.read().strip()
    else:
        dev_key = Fernet.generate_key()
        with open(_DEV_KEY_PATH, "wb") as f:
            f.write(dev_key)
    return Fernet(dev_key)


# ── Cookie helpers ─────────────────────────────────────────────────────────────

def _save_cookie(cookies: CookieController, vm: VehicleManager, region: int, brand: int) -> None:
    t = vm.token
    data = {
        "region": region,
        "brand": brand,
        "username": t.username or "",
        "pin": t.pin or "",
        "access_token": t.access_token or "",
        "refresh_token": t.refresh_token or "",
        "device_id": t.device_id or "",
        "valid_until": t.valid_until.isoformat() if t.valid_until else "",
    }
    encrypted = _get_fernet().encrypt(json.dumps(data).encode()).decode()
    # No `secure=True` — Fernet already encrypts the payload, and over HTTP
    # (local dev) the browser would reject a secure cookie outright.
    cookies.set(
        _COOKIE_NAME, encrypted,
        max_age=_COOKIE_MAX_AGE,
        same_site="strict",
    )


def _clear_cookie(cookies: CookieController) -> None:
    try:
        cookies.remove(_COOKIE_NAME)
    except Exception:
        pass


def _restore_from_cookie(
    cookies: CookieController, raw: str
) -> tuple[VehicleManager, int, int] | None:
    """Decrypt cookie and rebuild a logged-in VehicleManager.

    Returns None on failure. Cookie is cleared only on auth/decrypt failure,
    not on transient errors — that way a flaky network won't log the user out.
    """
    try:
        data = json.loads(_get_fernet().decrypt(raw.encode()).decode())
    except Exception:
        # Cookie is corrupt or encrypted with a different key — drop it.
        _clear_cookie(cookies)
        return None

    try:
        valid_until_str = data.get("valid_until", "")
        valid_until = datetime.datetime.fromisoformat(valid_until_str) if valid_until_str else None
        token = Token(
            username=data.get("username", ""),
            password="",
            pin=data.get("pin", ""),
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            device_id=data.get("device_id"),
            valid_until=valid_until,
            stamp=None,
        )
        region = int(data["region"])
        brand = int(data["brand"])
        vm = VehicleManager(
            region=region, brand=brand,
            username=data.get("username", ""), password="", pin=data.get("pin", ""),
            token=token,
        )
        prev_valid_until = token.valid_until
        vm.check_and_refresh_token()
        vm.initialize_vehicles()
        vm.update_all_vehicles_with_cached_state()
        # If the token was refreshed, request a deferred cookie save so the
        # write reaches the browser without being clipped by st.rerun().
        if vm.token.valid_until != prev_valid_until:
            st.session_state._needs_cookie_save = True
        return vm, region, brand
    except AuthenticationError:
        _clear_cookie(cookies)
        return None
    except Exception:
        # Transient (network, API) — keep the cookie so we can retry next load.
        return None


# ── State helpers ──────────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "logged_in": False,
        "vm": None,
        "vehicles": [],
        "selected_vehicle_id": None,
        "otp_pending": False,
        "_otp_region": None,
        "_otp_brand": None,
        "_session_checked": False,
        "_cookie_attempts": 0,
        "_region": None,
        "_brand": None,
        "_needs_cookie_save": False,
        "_redirect_after_login": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _apply_login(cookies: CookieController, vm: VehicleManager, region: int, brand: int) -> None:
    # Don't save the cookie here — st.rerun() that follows would discard the
    # cookie-controller component message. Defer to the logged-in view, which
    # renders cleanly without an immediate rerun.
    st.session_state.vm = vm
    st.session_state.vehicles = list(vm.vehicles.values())
    st.session_state.logged_in = True
    st.session_state.otp_pending = False
    st.session_state._region = region
    st.session_state._brand = brand
    st.session_state._needs_cookie_save = True


def _do_logout(cookies: CookieController) -> None:
    _clear_cookie(cookies)
    st.session_state.logged_in = False
    st.session_state.vm = None
    st.session_state.vehicles = []
    st.session_state.selected_vehicle_id = None
    st.session_state.otp_pending = False
    st.session_state._session_checked = False
    st.session_state._needs_cookie_save = False


# ── Bootstrap ──────────────────────────────────────────────────────────────────

_init_state()
cookies = CookieController(key="kc_ctrl")

# Cookie restoration:
#   - Render 1 of a fresh page load: getAll() returns {} (controller still mounting).
#   - Render 2 (after controller reports cookies): getAll() returns the real dict.
# We must NOT mark _session_checked until we've either restored or proven there's
# no cookie to restore. Empty dict on render 1 looks identical to "no cookie",
# so we wait one extra render before giving up.
if not st.session_state.logged_in and not st.session_state._session_checked:
    raw = (cookies.getAll() or {}).get(_COOKIE_NAME)
    if raw:
        st.session_state._session_checked = True  # only retry once
        with st.spinner("Restoring session…"):
            restored = _restore_from_cookie(cookies, raw)
        if restored:
            vm, region, brand = restored
            st.session_state.vm = vm
            st.session_state.vehicles = list(vm.vehicles.values())
            st.session_state.logged_in = True
            st.session_state._region = region
            st.session_state._brand = brand
            st.rerun()
    else:
        # No cookie visible yet. Could be (a) controller still loading, or (b) no
        # cookie exists. Give the controller one chance to deliver before falling
        # through to the login form.
        if st.session_state._cookie_attempts < 1:
            st.session_state._cookie_attempts += 1
            st.stop()
        st.session_state._session_checked = True

# ── Already logged in ──────────────────────────────────────────────────────────

if st.session_state.logged_in:
    # Persist the cookie now that the page is rendering normally (no immediate
    # rerun pending). The cookie-controller component message reaches the
    # browser as part of this render's deltas.
    if st.session_state._needs_cookie_save and st.session_state.vm is not None:
        _save_cookie(
            cookies, st.session_state.vm,
            st.session_state._region, st.session_state._brand,
        )
        st.session_state._needs_cookie_save = False

    redirect = st.session_state._redirect_after_login
    if redirect:
        st.session_state._redirect_after_login = None
        st.switch_page(redirect)

    vehicles = st.session_state.vehicles
    st.markdown('<div class="brand-title">🚗 Hyundai / Kia Connect</div>', unsafe_allow_html=True)
    st.success(f"Logged in · {len(vehicles)} vehicle(s) found")
    for v in vehicles:
        st.markdown(f"- **{v.name}** — {v.model} {v.year or ''} · `{v.VIN or 'VIN unknown'}`")
    st.info("Use the sidebar to navigate between pages.")
    if st.button("🚪 Log out"):
        _do_logout(cookies)
        st.rerun()
    st.stop()

# ── OTP verification ───────────────────────────────────────────────────────────

if st.session_state.otp_pending:
    st.markdown('<div class="brand-title">🔐 Two-Factor Auth</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">An OTP code is required to complete login</div>', unsafe_allow_html=True)

    vm = st.session_state.vm
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📧 Send via Email", width="stretch"):
            with st.spinner("Sending…"):
                vm.send_otp(OTP_NOTIFY_TYPE.EMAIL)
            st.success("OTP sent via email")
    with c2:
        if st.button("📱 Send via SMS", width="stretch"):
            with st.spinner("Sending…"):
                vm.send_otp(OTP_NOTIFY_TYPE.SMS)
            st.success("OTP sent via SMS")

    with st.form("otp_form"):
        otp_code = st.text_input("OTP code", placeholder="123456", max_chars=10)
        submitted = st.form_submit_button("✅ Verify & Login", width="stretch", type="primary")
        if submitted:
            if not otp_code:
                st.error("Enter the OTP code.")
            else:
                with st.spinner("Verifying…"):
                    try:
                        vm.verify_otp_and_complete_login(otp_code)
                        vm.initialize_vehicles()
                        vm.update_all_vehicles_with_cached_state()
                        _apply_login(cookies, vm, st.session_state._otp_region, st.session_state._otp_brand)
                        st.rerun()
                    except Exception as e:
                        st.error(f"OTP failed: {e}")

    if st.button("← Back"):
        st.session_state.otp_pending = False
        st.session_state.vm = None
        st.rerun()
    st.stop()

# ── Login form ─────────────────────────────────────────────────────────────────

st.markdown('<div class="brand-title">🚗 Hyundai / Kia Connect</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-sub">Sign in to manage your vehicle</div>', unsafe_allow_html=True)

_, center, _ = st.columns([1, 2, 1])
with center:
    with st.form("login_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            region = st.selectbox("Region", options=list(REGIONS.keys()),
                                  format_func=lambda k: REGIONS[k])
        with col_b:
            brand = st.selectbox("Brand", options=list(BRANDS.keys()),
                                 format_func=lambda k: BRANDS[k])

        email = st.text_input("Email / Username", placeholder="your@email.com", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        pin = st.text_input("PIN (optional)", type="password",
                            placeholder="Required for some regions (CA, USA)",
                            autocomplete="one-time-code")

        with st.expander("⚙️ Location lookup (optional)"):
            geocode_enable = st.checkbox("Enable reverse geocoding", value=True)
            geocode_provider = st.radio("Provider", options=list(GEO_LOCATION_PROVIDERS.keys()),
                                        format_func=lambda k: GEO_LOCATION_PROVIDERS[k].title(),
                                        horizontal=True)
            geocode_key = st.text_input("Google API Key", type="password",
                                        autocomplete="one-time-code",
                                        help="Only required when Google is selected as provider")

        submitted = st.form_submit_button("🔑 Sign in", width="stretch", type="primary")

if submitted:
    if not email or not password:
        st.error("Email and password are required.")
    else:
        with st.spinner("Signing in…"):
            try:
                vm = VehicleManager(
                    region=region, brand=brand,
                    username=email, password=password, pin=pin or "",
                    geocode_api_enable=geocode_enable,
                    geocode_provider=geocode_provider,
                    geocode_api_key=geocode_key or "",
                )
                result = vm.login()
                if result is True:
                    vm.initialize_vehicles()
                    vm.update_all_vehicles_with_cached_state()
                    _apply_login(cookies, vm, region, brand)
                    st.rerun()
                elif isinstance(result, OTPRequest):
                    st.session_state.vm = vm
                    st.session_state.otp_pending = True
                    st.session_state._otp_region = region
                    st.session_state._otp_brand = brand
                    st.rerun()
            except AuthenticationError as e:
                st.error(f"Authentication failed: {e}")
            except Exception as e:
                st.error(f"Error: {e}")

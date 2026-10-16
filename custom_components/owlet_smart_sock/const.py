"""Constants for the Owlet Smart Sock integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "owlet_smart_sock"

# Config entry / options keys
CONF_REGION: Final = "region"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Supported regions and the (reverse engineered) Owlet / Ayla / Firebase
# endpoints used to authenticate and poll each account's devices.
REGION_WORLD: Final = "world"
REGION_EUROPE: Final = "europe"

REGIONS: Final[dict[str, dict[str, str]]] = {
    REGION_WORLD: {
        "url_mini": "https://ayla-sso.owletdata.com/mini/",
        "url_signin": (
            "https://user-field-1a2039d9.aylanetworks.com/api/v1/token_sign_in"
        ),
        "url_base": "https://ads-field-1a2039d9.aylanetworks.com/apiv1",
        "api_key": "AIzaSyCsDZ8kWxQuLJAMVnmEhEkayH1TSxKXfGA",
        "app_id": "sso-prod-3g-id",
        "app_secret": "sso-prod-UEjtnPCtFfjdwIwxqnC0OipxRFU",
    },
    REGION_EUROPE: {
        "url_mini": "https://ayla-sso.eu.owletdata.com/mini/",
        "url_signin": (
            "https://user-field-eu-1a2039d9.aylanetworks.com/api/v1/token_sign_in"
        ),
        "url_base": "https://ads-field-eu-1a2039d9.aylanetworks.com/apiv1",
        "api_key": "AIzaSyDm6EhV70wudwN3iOSq3vTjtsdGjdFLuuM",
        "app_id": "OwletCare-Android-EU-fw-id",
        "app_secret": "OwletCare-Android-EU-JKupMPBoj_Npce_9a95Pc8Qo0Mw",
    },
}

# Firebase (Google Identity Toolkit) sign-in endpoint and the headers that
# unlock the app-restricted API key.
FIREBASE_SIGNIN_URL: Final = (
    "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword"
)
ANDROID_PACKAGE: Final = "com.owletcare.owletcare"
ANDROID_CERT: Final = "2A3BC26DB0B8B0792DBE28E6FFDC2598F9B12B74"

# Polling cadence. These are vital signs, so the default is intentionally
# frequent, but it is user-configurable from the options flow. The sock itself
# streams real-time vitals roughly every 3 seconds, so there is no benefit to
# polling faster than that - 3 seconds is the enforced minimum.
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 3
MAX_SCAN_INTERVAL: Final = 300
DEVICE_LIST_REFRESH: Final = timedelta(hours=1)

MANUFACTURER: Final = "Owlet"

# Normalised sock status values. These are used as the enum sensor's options
# and must line up with the translation keys in translations/en.json.
STATUS_MONITORING: Final = "monitoring"
STATUS_CHARGING: Final = "charging"
STATUS_CHARGED: Final = "charged"
STATUS_NO_SIGNAL: Final = "no_signal"
STATUS_DISCONNECTED: Final = "disconnected"
STATUS_ERROR: Final = "error"

SOCK_STATUSES: Final = [
    STATUS_MONITORING,
    STATUS_CHARGING,
    STATUS_CHARGED,
    STATUS_NO_SIGNAL,
    STATUS_DISCONNECTED,
    STATUS_ERROR,
]

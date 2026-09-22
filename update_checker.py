"""
Güncelleme kontrolü — GitHub Releases üzerinden sürüm sorgulama.

Streamlit bağımsız saf modül (UI'dan ayrı, test edilebilir). Yalnızca Python
standart kütüphanesi kullanılır (`urllib`); ek bağımlılık gerekmez.

Davranış:
- Ağ hatası / rate-limit / parse hatası → exception YOK, `status="error"`.
- Sonuç, TTL boyunca modül-seviyesi önbellekte tutulur (GitHub API 60/saat limiti).
- İndirme yapılmaz; yalnızca bilgi ve indirme linki üretilir.
"""

import json
import platform
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from version import REPO_SLUG

try:  # macOS framework Python'da sistem CA deposu boş olabilir
    import certifi

    _CAFILE: Optional[str] = certifi.where()
except Exception:  # pragma: no cover - certifi yoksa sistem deposuna düş
    _CAFILE = None

_API_URL = "https://api.github.com/repos/{slug}/releases/latest"
_USER_AGENT = "ASME-B31.8-Pipeline-Designer-UpdateCheck"
DEFAULT_TIMEOUT = 3.0
DEFAULT_TTL_SECONDS = 3600.0

# Modül-seviyesi basit TTL önbellek: {"ts": epoch, "data": {...}}
_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}


def _ssl_context() -> ssl.SSLContext:
    """certifi CA paketi varsa onu kullanır; yoksa sistem varsayılanına düşer."""
    try:
        if _CAFILE:
            return ssl.create_default_context(cafile=_CAFILE)
    except Exception:  # pragma: no cover
        pass
    return ssl.create_default_context()


def _parse_semver(tag: str) -> Optional[Tuple[int, int, int]]:
    """'v3.6.1' / 'V3.6.1' / '3.6.1-rc1' → (3, 6, 1). Geçersizse None."""
    if not tag:
        return None
    text = str(tag).strip().lstrip("vV")
    # Ön-sürüm / yapı metadata'sını at
    text = text.split("+", 1)[0].split("-", 1)[0]
    parts = text.split(".")
    nums: List[int] = []
    for part in parts[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        nums.append(int(digits))
    if not nums:
        return None
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def compare_versions(a: str, b: str) -> int:
    """a > b → 1, a < b → -1, eşit veya parse edilemezse 0."""
    pa, pb = _parse_semver(a), _parse_semver(b)
    if pa is None or pb is None:
        return 0
    if pa > pb:
        return 1
    if pa < pb:
        return -1
    return 0


def _platform_keywords() -> List[List[str]]:
    """
    Mevcut ortama uygun asset anahtar kelime gruplarını (VE mantığı) döndürür.
    Sıra önceliklidir; ilk eşleşen kullanılır.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return [["windows"], ["win"]]
    if system == "darwin":
        if machine in ("arm64", "aarch64"):
            return [["macos", "arm64"], ["macos", "applesilicon"], ["macos"]]
        return [["macos", "intel"], ["macos", "x86"], ["macos"]]
    if system == "linux":
        return [["linux", "x86_64"], ["linux"]]
    return []


_PREFERRED_EXTS = (".dmg", ".exe", ".zip")


def select_platform_asset(assets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Release asset'leri içinden mevcut platforma en uygun dosyayı seçer.

    Tercih sırası: `.dmg` → `.exe` → `.zip` (tek dosya kurulum önce gelir).
    Aynı platform için birden fazla asset varsa (ör. .exe + Portable.zip)
    tek dosya olan seçilir.
    """
    if not assets:
        return None
    # Yalnızca gerçek arşivleri düşün (sha256 hariç)
    candidates = [
        a for a in assets
        if a.get("name") and not str(a.get("name", "")).lower().endswith(".sha256")
    ]

    def _rank(asset: Dict[str, Any]) -> int:
        name = str(asset.get("name", "")).lower()
        for idx, ext in enumerate(_PREFERRED_EXTS):
            if name.endswith(ext):
                return idx
        return len(_PREFERRED_EXTS)

    for kws in _platform_keywords():
        matches = []
        for asset in candidates:
            name = str(asset.get("name", "")).lower()
            if kws[0] not in name:
                continue
            if len(kws) > 1 and kws[1] not in name:
                continue
            matches.append(asset)
        if matches:
            matches.sort(key=_rank)
            return matches[0]
    return None


def fetch_latest_release(
    slug: str = REPO_SLUG,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
) -> Dict[str, Any]:
    """GitHub 'latest release' JSON'unu döndürür. Hata durumunda exception fırlatır."""
    now = time.time()
    if use_cache and _CACHE["data"] is not None and (now - _CACHE["ts"]) < ttl_seconds:
        return _CACHE["data"]

    url = _API_URL.format(slug=slug)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:  # noqa: S310 (sabit HTTPS URL)
        payload = json.loads(resp.read().decode("utf-8"))

    if use_cache:
        _CACHE["ts"] = now
        _CACHE["data"] = payload
    return payload


def _error_result(current_version: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "current": current_version,
        "latest": None,
        "release_url": None,
        "release_name": None,
        "asset_url": None,
        "asset_name": None,
        "error": message,
    }


def check_for_update(
    current_version: str,
    slug: str = REPO_SLUG,
    timeout: float = DEFAULT_TIMEOUT,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Mevcut sürümü GitHub'daki en son release ile karşılaştırır.

    Returns:
        {
          status: "update_available" | "up_to_date" | "error",
          current, latest, release_url, release_name, asset_url, asset_name, error
        }
    """
    try:
        payload = fetch_latest_release(slug=slug, timeout=timeout, use_cache=use_cache)
    except urllib.error.HTTPError as exc:  # noqa: PERF203
        return _error_result(current_version, f"HTTP {exc.code}")
    except Exception as exc:  # ağ/timeout/parse — sessiz düşüş
        return _error_result(current_version, f"{type(exc).__name__}: {exc}")

    latest_tag = payload.get("tag_name") or payload.get("name") or ""
    latest_ver = _parse_semver(latest_tag)
    if latest_ver is None:
        return _error_result(current_version, "Sürüm etiketi okunamadı")

    assets = payload.get("assets") or []
    asset = select_platform_asset(assets)

    result = {
        "status": "update_available" if compare_versions(latest_tag, current_version) > 0 else "up_to_date",
        "current": current_version,
        "latest": f"{latest_ver[0]}.{latest_ver[1]}.{latest_ver[2]}",
        "release_url": payload.get("html_url"),
        "release_name": payload.get("name"),
        "asset_url": (asset or {}).get("browser_download_url"),
        "asset_name": (asset or {}).get("name"),
        "error": None,
    }
    return result


def clear_cache() -> None:
    """Önbelleği temizler (test / manuel yenileme için)."""
    _CACHE["ts"] = 0.0
    _CACHE["data"] = None

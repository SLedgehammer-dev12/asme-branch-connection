"""
Güncelleme kontrolü (update_checker) ve sürüm tek kaynağı testleri.

Ağ çağrısı YAPILMAZ; `fetch_latest_release` monkeypatch ile taklit edilir.
"""

import importlib

import pytest

import update_checker as uc
import version


def test_version_module_format():
    assert isinstance(version.__version__, str)
    assert version.__version__.count(".") == 2
    assert version.__version_label__ == f"V{version.__version__}"
    assert version.REPO_SLUG and "/" in version.REPO_SLUG
    assert version.RELEASES_PAGE.startswith("https://github.com/")


class TestSemver:
    def test_parse_basic(self):
        assert uc._parse_semver("v3.6.1") == (3, 6, 1)
        assert uc._parse_semver("3.6.1") == (3, 6, 1)
        assert uc._parse_semver("V3.10.0") == (3, 10, 0)

    def test_parse_short_and_suffix(self):
        assert uc._parse_semver("3.6") == (3, 6, 0)
        assert uc._parse_semver("v3.6.1-rc1") == (3, 6, 1)
        assert uc._parse_semver("v3.6.1+build9") == (3, 6, 1)

    def test_parse_invalid(self):
        assert uc._parse_semver("") is None
        assert uc._parse_semver("latest") is None
        assert uc._parse_semver(None) is None

    def test_compare(self):
        assert uc.compare_versions("v3.6.1", "3.6.0") == 1
        assert uc.compare_versions("v3.6.0", "3.6.1") == -1
        assert uc.compare_versions("3.6.1", "v3.6.1") == 0
        # 3.10 > 3.9 (sayısal, sözlüksel değil)
        assert uc.compare_versions("3.10.0", "3.9.9") == 1
        # parse edilemezse nötr
        assert uc.compare_versions("abc", "3.6.1") == 0


class TestPlatformAsset:
    def _assets(self):
        return [
            {"name": "ASME_Branch_Connection_v3.6.1_macOS_AppleSilicon_ARM64.zip",
             "browser_download_url": "https://example/mac_arm.zip"},
            {"name": "ASME_Branch_Connection_v3.6.1_Windows_x64.zip",
             "browser_download_url": "https://example/win.zip"},
            {"name": "ASME_Branch_Connection_v3.6.1_macOS_AppleSilicon_ARM64.zip.sha256",
             "browser_download_url": "https://example/mac_arm.zip.sha256"},
        ]

    def test_windows(self, monkeypatch):
        monkeypatch.setattr(uc.platform, "system", lambda: "Windows")
        monkeypatch.setattr(uc.platform, "machine", lambda: "AMD64")
        a = uc.select_platform_asset(self._assets())
        assert a and "Windows" in a["name"]

    def test_macos_arm(self, monkeypatch):
        monkeypatch.setattr(uc.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(uc.platform, "machine", lambda: "arm64")
        a = uc.select_platform_asset(self._assets())
        assert a and "macOS" in a["name"] and "ARM64" in a["name"]
        assert not a["name"].endswith(".sha256")

    def test_no_match_returns_none(self, monkeypatch):
        monkeypatch.setattr(uc.platform, "system", lambda: "Linux")
        monkeypatch.setattr(uc.platform, "machine", lambda: "riscv64")
        assert uc.select_platform_asset(self._assets()) is None
        assert uc.select_platform_asset([]) is None

    def test_prefers_single_file_dmg_over_zip(self, monkeypatch):
        """macOS: .dmg, .zip'e tercih edilir (tek dosya kurulum)."""
        monkeypatch.setattr(uc.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(uc.platform, "machine", lambda: "arm64")
        assets = [
            {"name": "ASME_Branch_Connection_v3.8.0_macOS_AppleSilicon_ARM64.zip",
             "browser_download_url": "u1"},
            {"name": "ASME_Branch_Connection_v3.8.0_macOS_AppleSilicon_ARM64.dmg",
             "browser_download_url": "u2"},
            {"name": "ASME_Branch_Connection_v3.8.0_macOS_AppleSilicon_ARM64.dmg.sha256",
             "browser_download_url": "u3"},
        ]
        a = uc.select_platform_asset(assets)
        assert a["browser_download_url"] == "u2"

    def test_prefers_exe_over_portable_zip(self, monkeypatch):
        """Windows: .exe, Portable .zip'e tercih edilir."""
        monkeypatch.setattr(uc.platform, "system", lambda: "Windows")
        monkeypatch.setattr(uc.platform, "machine", lambda: "AMD64")
        assets = [
            {"name": "ASME_Branch_Connection_v3.8.0_Windows_x64_Portable.zip",
             "browser_download_url": "u1"},
            {"name": "ASME_Branch_Connection_v3.8.0_Windows_x64.exe",
             "browser_download_url": "u2"},
            {"name": "ASME_Branch_Connection_v3.8.0_Windows_x64.exe.sha256",
             "browser_download_url": "u3"},
        ]
        a = uc.select_platform_asset(assets)
        assert a["browser_download_url"] == "u2"

    def test_falls_back_to_zip_when_no_single_file(self, monkeypatch):
        monkeypatch.setattr(uc.platform, "system", lambda: "Windows")
        monkeypatch.setattr(uc.platform, "machine", lambda: "AMD64")
        assets = [
            {"name": "ASME_Branch_Connection_v3.8.0_Windows_x64_Portable.zip",
             "browser_download_url": "u1"},
        ]
        a = uc.select_platform_asset(assets)
        assert a["browser_download_url"] == "u1"


class TestCheckForUpdate:
    def test_update_available(self, monkeypatch):
        payload = {
            "tag_name": "v3.7.0",
            "name": "v3.7.0",
            "html_url": "https://github.com/x/y/releases/tag/v3.7.0",
            "assets": [{"name": "pkg.zip", "browser_download_url": "https://example/pkg.zip"}],
        }
        monkeypatch.setattr(uc, "fetch_latest_release", lambda **kw: payload)
        res = uc.check_for_update("3.6.1")
        assert res["status"] == "update_available"
        assert res["latest"] == "3.7.0"
        assert res["release_url"].endswith("v3.7.0")

    def test_up_to_date(self, monkeypatch):
        payload = {"tag_name": "v3.6.1", "name": "v3.6.1", "html_url": "u", "assets": []}
        monkeypatch.setattr(uc, "fetch_latest_release", lambda **kw: payload)
        assert uc.check_for_update("3.6.1")["status"] == "up_to_date"

    def test_offline_is_silent_error(self, monkeypatch):
        def _boom(**kw):
            raise OSError("network down")
        monkeypatch.setattr(uc, "fetch_latest_release", _boom)
        res = uc.check_for_update("3.6.1")
        assert res["status"] == "error"
        assert res["error"]
        assert res["latest"] is None

    def test_bad_tag_is_error(self, monkeypatch):
        monkeypatch.setattr(uc, "fetch_latest_release", lambda **kw: {"tag_name": "", "assets": []})
        assert uc.check_for_update("3.6.1")["status"] == "error"


class TestCache:
    def test_cache_avoids_second_fetch(self, monkeypatch):
        uc.clear_cache()
        calls = {"n": 0}

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"tag_name": "v9.9.9", "assets": []}'

        def _fake_urlopen(req, timeout=0, context=None):
            calls["n"] += 1
            return _Resp()

        monkeypatch.setattr(uc.urllib.request, "urlopen", _fake_urlopen)
        uc.fetch_latest_release(use_cache=True)
        uc.fetch_latest_release(use_cache=True)
        assert calls["n"] == 1
        uc.clear_cache()
        uc.fetch_latest_release(use_cache=True)
        assert calls["n"] == 2

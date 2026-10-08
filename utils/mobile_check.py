"""Preflight for mobile runs (Appium on the host, emulator running, Grafana reachable).

    python -m utils.mobile_check          # run on the HOST before `docker compose --profile mobile ...`
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from utils.settings import get_settings


def _find_adb() -> str | None:
    found = shutil.which("adb")
    if found:
        return found
    for root in (os.getenv("ANDROID_HOME"), os.getenv("ANDROID_SDK_ROOT")):
        if root:
            for name in ("adb.exe", "adb"):
                candidate = Path(root) / "platform-tools" / name
                if candidate.exists():
                    return str(candidate)
    return None


def main() -> int:
    s = get_settings()
    ok = True

    print(f"Appium server : {s.appium_url}")
    try:
        data = requests.get(f"{s.appium_url}/status", timeout=3).json().get("value", {})
        print(f"  OK  ready={data.get('ready', 'unknown')}")
    except Exception as exc:
        ok = False
        print(f"  FAIL  not reachable ({type(exc).__name__}). Start it:  appium --allow-insecure=uiautomator2:chromedriver_autodownload")

    adb = _find_adb()
    print("Android device:")
    if adb:
        out = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=15).stdout
        devices = [ln.split()[0] for ln in out.splitlines()[1:] if ln.strip().endswith("device")]
        if devices:
            print(f"  OK  {', '.join(devices)}" + ("  (several: set MOBILE_UDID)" if len(devices) > 1 else ""))
        else:
            ok = False
            print("  FAIL  no emulator/device online. Start your AVD from Android Studio > Device Manager.")
    else:
        print("  skipped: adb not found (normal inside Docker; run this check on the host, with ANDROID_HOME set)")

    print(f"Grafana (from this machine): {s.base_url}")
    try:
        version = requests.get(f"{s.base_url}/api/health", timeout=3).json().get("version", "?")
        print(f"  OK  version {version}")
    except Exception as exc:
        ok = False
        print(f"  FAIL  not reachable ({type(exc).__name__})")

    print(f"Grafana (from the emulator): {s.mobile_base_url}")
    print("  cannot be verified here; open that URL in the emulator's Chrome once to confirm.")
    print("\nAll checks passed." if ok else "\nFix the FAIL items above, then re-run.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

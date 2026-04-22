#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


HOST_NAME = "com.gptokens.bridge"


def host_manifest_dir(browser: str) -> Path:
    home = Path.home()
    mapping = {
        "brave": home / ".config" / "BraveSoftware" / "Brave-Browser" / "NativeMessagingHosts",
        "brave-beta": home / ".config" / "BraveSoftware" / "Brave-Browser-Beta" / "NativeMessagingHosts",
        "chrome": home / ".config" / "google-chrome" / "NativeMessagingHosts",
        "chromium": home / ".config" / "chromium" / "NativeMessagingHosts",
    }
    return mapping[browser]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python install_native_host.py <brave|brave-beta|chrome|chromium> <extension_id>")
        return 1

    browser = sys.argv[1]
    extension_id = sys.argv[2]
    if browser not in {"brave", "brave-beta", "chrome", "chromium"}:
        print("Browser must be brave, brave-beta, chrome or chromium")
        return 1

    manifest_dir = host_manifest_dir(browser)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    host_path = Path(__file__).resolve().parent / "gptokens_native_host.py"
    current_mode = host_path.stat().st_mode
    host_path.chmod(current_mode | 0o111)
    manifest_path = manifest_dir / f"{HOST_NAME}.json"
    manifest = {
        "name": HOST_NAME,
        "description": "GPTokens native bridge",
        "path": str(host_path),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Native host installed to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

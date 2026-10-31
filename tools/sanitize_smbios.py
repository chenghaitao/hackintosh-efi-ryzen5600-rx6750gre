#!/usr/bin/env python3
"""把 config.plist 里的「三码」替换成占位符，便于公开分享。

三码 = SystemSerialNumber + MLB + SystemUUID（+ ROM，ROM 一般填有线网卡 MAC）。
用法：python3 tools/sanitize_smbios.py OC/config.plist
"""
import plistlib, sys, os

PLACEHOLDER = {
    "SystemSerialNumber": "XXXXXXXXXXXX",
    "MLB": "XXXXXXXXXXXXXXXXX",
    "SystemUUID": "00000000-0000-0000-0000-000000000000",
    "ROM": b"\x00\x00\x00\x00\x00\x00",
}

path = sys.argv[1] if len(sys.argv) > 1 else "OC/config.plist"
c = plistlib.load(open(path, "rb"))
generic = c["PlatformInfo"]["Generic"]

print(f"{path}")
for k, v in PLACEHOLDER.items():
    old = generic.get(k)
    if old is None:
        print(f"  - {k}: 不存在，跳过")
        continue
    generic[k] = v
    shown = "<bytes>" if isinstance(old, bytes) else old
    print(f"  ✓ {k}: {shown}  →  {'<zeros>' if isinstance(v, bytes) else v}")

plistlib.dump(c, open(path, "wb"))
print("已写回。")

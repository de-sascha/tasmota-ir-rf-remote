#!/usr/bin/env python3
"""Print the release notes for one release.

Usage: release_notes.py <CHANGELOG.md> <tag>

The notes are the CHANGELOG section of that tag plus a short, fixed part that
tells people which file to take.
"""
import re
import sys
from pathlib import Path


def section(changelog, tag):
    text = Path(changelog).read_text()
    m = re.search(rf"^## \[{re.escape(tag)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
    if not m:
        sys.exit(f"release_notes: no section '## [{tag}]' in {changelog}")
    return m.group(1).strip()


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: release_notes.py <CHANGELOG.md> <tag>")
    changelog, tag = sys.argv[1], sys.argv[2]
    version = re.sub(r"-r\d+$", "", tag)
    print(section(changelog, tag))
    print(f"""
---

### Which file do I need?

| File | When |
|---|---|
| `tasmota32-ir-rf.bin` | Your box already runs Tasmota: *Firmware Upgrade → Upgrade by file upload*. |
| `tasmota32-ir-rf.factory.bin` | First install over USB, for example with [web.esphome.io](https://web.esphome.io/). |
| `SHA256SUMS.txt` | Checksums, if you want to verify the download. |

Step-by-step instructions: [README](https://github.com/de-sascha/tasmota-ir-rf-remote/blob/main/README.md#install).
Inside: [Tasmota {version.lstrip('v')}](https://github.com/arendst/Tasmota/releases/tag/{version}) plus the [ir-rf additions](https://github.com/de-sascha/tasmota-ir-rf-remote/blob/main/docs/how-it-is-built.md).""")


if __name__ == "__main__":
    main()

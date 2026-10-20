#!/usr/bin/env python3
"""Apply the ir-rf changes to an upstream Tasmota checkout.

Usage: patch_tasmota.py <path-to-tasmota-src>

Works by anchors, not by line numbers, so it survives new Tasmota releases.
If an anchor is missing, it stops with a clear message instead of building
something half-patched.
"""
import re
import sys
from pathlib import Path

# RfSend commands in people's automations use this protocol number for the
# CREATE ceiling fan remote, so it must never move.
FAN_PROTOCOL = 41

PLACEHOLDER = ('  { 380,  0, { 0, 0 }, 0, {    0, 0 }, { 1,  3 }, { 3, 1 }, false, 18 },'
               '  // {n} ir-rf: placeholder (first CREATE attempt, fan ignores it), keeps the fan protocol number fixed\n')
FAN_ENTRY = ('  {  20,  0, { 0, 0 }, 0, {    0, 0 }, {16, 60 }, {55,22 }, false, 291 }'
             '  // {n} ir-rf: CREATE ceiling fan remote K9678, 30 bits, timings as measured (320/1200, 1100/440, gap ~7 ms)\n')


def fail(msg):
    sys.exit(f"patch_tasmota: {msg}")


def enable_rc_switch(src):
    p = src / "tasmota/include/tasmota_configurations.h"
    s = p.read_text()
    m = re.search(r"#ifdef FIRMWARE_IR\b(.*?)#endif\s*//\s*FIRMWARE_IR", s, re.S)
    if not m:
        fail("block FIRMWARE_IR not found in tasmota_configurations.h")
    block = m.group(1)
    n = len(re.findall(r"^#undef USE_RC_SWITCH\b.*$", block, re.M))
    if n != 1:
        fail(f"expected exactly one '#undef USE_RC_SWITCH' in FIRMWARE_IR, found {n}")
    block = re.sub(r"^#undef USE_RC_SWITCH\b.*$",
                   "#define USE_RC_SWITCH                            // ir-rf: RcSwitch for the 433 MHz part of the IoTorero AR01V3",
                   block, flags=re.M)
    p.write_text(s[:m.start(1)] + block + s[m.end(1):])


def add_fan_protocol(src):
    p = src / "lib/lib_rf/rc-switch/src/RCSwitch.cpp"
    s = p.read_text()
    start = s.find("RCSwitch::Protocol PROGMEM proto[] = {")
    if start < 0:
        fail("protocol table 'proto[]' not found in RCSwitch.cpp")
    end = s.find("\n};", start)
    table = s[start:end]
    entries = re.findall(r"^\s*\{\s*\d+\s*,.*\}\s*,?\s*(?://.*)?$", table, re.M)
    count = len(entries)
    if count >= FAN_PROTOCOL:
        fail(f"upstream already has {count} RF protocols; protocol {FAN_PROTOCOL} would collide. "
             "Pick a new number and tell users in the changelog.")
    # The last upstream entry has no trailing comma; give it one.
    last_line_start = table.rstrip().rfind("\n") + 1
    last_line = table[last_line_start:]
    code, sep, comment = last_line.partition("//")
    if not code.rstrip().endswith(","):
        brace = code.rstrip().rfind("}")
        gap = code[brace + 1:]
        gap = gap[1:] if len(gap) >= 2 else gap  # keep the comment column
        last_line = code[:brace + 1] + "," + gap + sep + comment
    added = "".join(PLACEHOLDER.replace("{n}", str(n)) for n in range(count + 1, FAN_PROTOCOL))
    added += FAN_ENTRY.replace("{n}", str(FAN_PROTOCOL))
    new_table = table[:last_line_start] + last_line.rstrip("\n") + "\n" + added.rstrip("\n")
    p.write_text(s[:start] + new_table + s[end:])
    return count


def log_raw_timings(src):
    p = src / "tasmota/tasmota_xdrv_driver/xdrv_17_rcswitch.ino"
    s = p.read_text()
    anchor = re.search(r'^([ \t]*)AddLog\(LOG_LEVEL_DEBUG, PSTR\("RFR: Data .*?\);\n', s, re.M)
    if not anchor:
        fail("log line 'RFR: Data' not found in xdrv_17_rcswitch.ino")
    ind = anchor.group(1)
    code = (
        f"{ind}if (HighestLogLevel() >= LOG_LEVEL_DEBUG) {{  // ir-rf: raw pulse timings, to rebuild unknown remotes\n"
        f"{ind}  unsigned int* raw = mySwitch.getReceivedRawdata();\n"
        f"{ind}  char rbuf[700];\n"
        f"{ind}  int pos = 0;\n"
        f"{ind}  for (uint32_t i = 0; i < 2 * bits + 2 && i < RCSWITCH_MAX_CHANGES && pos < (int)sizeof(rbuf) - 8; i++) {{\n"
        f"{ind}    pos += snprintf(rbuf + pos, sizeof(rbuf) - pos, \"%u,\", raw[i]);\n"
        f"{ind}  }}\n"
        f"{ind}  AddLog(LOG_LEVEL_DEBUG, PSTR(\"RFR: Raw %s\"), rbuf);\n"
        f"{ind}}}\n"
    )
    p.write_text(s[:anchor.end()] + code + s[anchor.end():])


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_tasmota.py <path-to-tasmota-src>")
    src = Path(sys.argv[1])
    if "ir-rf" in (src / "lib/lib_rf/rc-switch/src/RCSwitch.cpp").read_text():
        fail("source is already patched")
    enable_rc_switch(src)
    upstream = add_fan_protocol(src)
    log_raw_timings(src)
    print(f"patch_tasmota: ok ({upstream} upstream RF protocols, fan protocol {FAN_PROTOCOL})")


if __name__ == "__main__":
    main()

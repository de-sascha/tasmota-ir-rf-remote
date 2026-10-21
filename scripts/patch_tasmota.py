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


def replace_once(s, old, new, where):
    n = s.count(old)
    if n != 1:
        fail(f"expected exactly one '{old.strip()[:60]}' in {where}, found {n}")
    return s.replace(old, new, 1)


IR_HEADER = """
#if defined(ESP32) && !defined(UNIT_TEST)
// ir-rf: steady IR carrier on ESP32. The 38 kHz carrier is made in software, so
// its frequency depends on how fast this loop runs from flash. Measured on an
// AR01V3 (160 MHz): official tasmota32-ir 34.7 kHz, ir-rf r1 28.7 kHz, and at
// 28.7 kHz a GREE air conditioner took only 25 of 40 commands (official 40/40).
// Here the loop runs from IRAM, switches the LED by register and waits with the
// ROM delay, and Tasmota measures it once at start-up (calibrate) and corrects
// the period for every IRsend object through ir_rf_period_offset.
#include "esp_attr.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "hal/gpio_ll.h"
#define IRRF_IRAM IRAM_ATTR
int8_t ir_rf_period_offset = 0;
#define IRRF_PERIOD_OFFSET ir_rf_period_offset
#else
#define IRRF_IRAM
#define IRRF_PERIOD_OFFSET kPeriodOffset
#endif  // ir-rf
"""


def steady_ir_carrier(src):
    lib = src / "lib/lib_basic/IRremoteESP8266/IRremoteESP8266/src"
    p = lib / "IRsend.cpp"
    s = p.read_text()
    w = "IRsend.cpp"
    s = replace_once(s, '#include "IRtimer.h"\n', '#include "IRtimer.h"\n' + IR_HEADER, w)
    s = replace_once(s, "periodOffset(kPeriodOffset)", "periodOffset(IRRF_PERIOD_OFFSET)", w)
    for fn, level in (("ledOff", "outputOff"), ("ledOn", "outputOn")):
        s = replace_once(s, f"void IRsend::{fn}() {{\n#ifndef UNIT_TEST\n  digitalWrite(IRpin, {level});\n",
                         f"void IRRF_IRAM IRsend::{fn}() {{\n#if defined(ESP32) && !defined(UNIT_TEST)\n"
                         f"  gpio_ll_set_level(&GPIO, IRpin, {level});\n#elif !defined(UNIT_TEST)\n"
                         f"  digitalWrite(IRpin, {level});\n", w)
    s = replace_once(s, "void IRsend::_delayMicroseconds(uint32_t usec) {\n  // delayMicroseconds() is only accurate",
                     "void IRRF_IRAM IRsend::_delayMicroseconds(uint32_t usec) {\n  // delayMicroseconds() is only accurate", w)
    s = replace_once(s, "  if (usec <= kMaxAccurateUsecDelay) {\n#ifndef UNIT_TEST\n    delayMicroseconds(usec);\n",
                     "  if (usec <= kMaxAccurateUsecDelay) {\n#if defined(ESP32) && !defined(UNIT_TEST)\n"
                     "    esp_rom_delay_us(usec);\n#elif !defined(UNIT_TEST)\n    delayMicroseconds(usec);\n", w)
    s = replace_once(s, "uint16_t IRsend::mark(uint16_t usec) {", "uint16_t IRRF_IRAM IRsend::mark(uint16_t usec) {", w)
    s = replace_once(s, "void IRsend::space(uint32_t time) {", "void IRRF_IRAM IRsend::space(uint32_t time) {", w)
    p.write_text(s)

    p = lib / "IRtimer.cpp"
    s = p.read_text()
    w = "IRtimer.cpp"
    s = replace_once(s, "#ifndef UNIT_TEST\n#include <Arduino.h>\n#endif\n",
                     "#ifndef UNIT_TEST\n#include <Arduino.h>\n#endif\n"
                     "#if defined(ESP32) && !defined(UNIT_TEST)  // ir-rf: see IRsend.cpp\n"
                     "#include \"esp_attr.h\"\n#include \"esp_timer.h\"\n"
                     "#define IRRF_IRAM IRAM_ATTR\n#define IRRF_MICROS() ((uint32_t)esp_timer_get_time())\n"
                     "#else\n#define IRRF_IRAM\n#define IRRF_MICROS() micros()\n#endif\n", w)
    s = replace_once(s, "IRtimer::IRtimer() { reset(); }", "IRRF_IRAM IRtimer::IRtimer() { reset(); }", w)
    s = replace_once(s, "void IRtimer::reset() {\n#ifndef UNIT_TEST\n  start = micros();",
                     "void IRRF_IRAM IRtimer::reset() {\n#ifndef UNIT_TEST\n  start = IRRF_MICROS();", w)
    s = replace_once(s, "uint32_t IRtimer::elapsed() {\n#ifndef UNIT_TEST\n  uint32_t now = micros();",
                     "uint32_t IRRF_IRAM IRtimer::elapsed() {\n#ifndef UNIT_TEST\n  uint32_t now = IRRF_MICROS();", w)
    p.write_text(s)

    p = src / "tasmota/tasmota_xdrv_driver/xdrv_05_irremote_full.ino"
    s = p.read_text()
    w = "xdrv_05_irremote_full.ino"
    m = re.search(r"void IrInit\(void\) \{\n(.*?)\n\}\n", s, re.S)
    if not m:
        fail(f"function IrInit not found in {w}")
    calib = (
        "\n#ifdef ESP32\n"
        "  if (ir_send_active) {  // ir-rf: measure the carrier loop once, see IRsend.cpp\n"
        "    extern int8_t ir_rf_period_offset;\n"
        "    IRsend cal = IrSendInitGPIO();\n"
        "    ir_rf_period_offset = cal.calibrate(38000);\n"
        "    AddLog(LOG_LEVEL_INFO, PSTR(\"IR : ir-rf carrier calibrated, period offset %d us (38 kHz = 26 us)\"), ir_rf_period_offset);\n"
        "  }\n"
        "#endif  // ESP32"
    )
    s = s[:m.end(1)] + calib + s[m.end(1):]
    p.write_text(s)


def main():
    if len(sys.argv) != 2:
        fail("usage: patch_tasmota.py <path-to-tasmota-src>")
    src = Path(sys.argv[1])
    if "ir-rf" in (src / "lib/lib_rf/rc-switch/src/RCSwitch.cpp").read_text():
        fail("source is already patched")
    enable_rc_switch(src)
    upstream = add_fan_protocol(src)
    log_raw_timings(src)
    steady_ir_carrier(src)
    print(f"patch_tasmota: ok ({upstream} upstream RF protocols, fan protocol {FAN_PROTOCOL})")


if __name__ == "__main__":
    main()

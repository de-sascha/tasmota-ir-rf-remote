# How it is built

[← back to the README](../README.md)

This repository contains no copy of Tasmota. Every build takes an untouched
official Tasmota release, applies a small script and compiles it. That keeps
the project tiny and lets it follow new Tasmota versions on its own.

## What is changed in Tasmota

`scripts/patch_tasmota.py` makes exactly four changes. It finds them by
text, not by line number, so it keeps working when Tasmota moves code around.
If one of the places is missing, it stops with a clear message instead of
building something half-changed.

| File in Tasmota | Change | Why |
|---|---|---|
| `tasmota/include/tasmota_configurations.h` | In the `FIRMWARE_IR` block, `USE_RC_SWITCH` is switched on instead of off. | The official IR image deliberately leaves radio out. A `user_config_override.h` cannot undo it, because Tasmota reads that file *before* this block. |
| `lib/lib_rf/rc-switch/src/RCSwitch.cpp` | Protocol 41 (CREATE ceiling fan) is appended. Empty slots up to 40 are filled with a placeholder. | Home Assistant and other automations refer to the protocol by number, so it must never move. If Tasmota itself ever ships 41 or more protocols, the script stops and asks for a new number. |
| `tasmota/tasmota_xdrv_driver/xdrv_17_rcswitch.ino` | With log level 4 (`WebLog 4`), the raw pulse lengths of each received code are logged as `RFR: Raw …`. | To measure unknown remotes, see [rf-remotes.md](rf-remotes.md). Costs nothing at normal log levels. |
| `lib/lib_basic/IRremoteESP8266/…/IRsend.cpp`, `IRtimer.cpp` and `xdrv_05_irremote_full.ino` | The infrared carrier loop runs from fast internal RAM (IRAM) and switches the LED directly. At start-up the box measures the loop, corrects the carrier period to 38 kHz and measures again. The result is in the log (`IR : carrier 38.x kHz OK …`, or an error outside 36-40 kHz), on the main page (*IR carrier*) and in the sensor telemetry (`"IR":{"Carrier":38.x}`). Without IR and radio pins, the main page shows a hint to set the template. | The 38 kHz carrier is made in software, so its frequency depends on how fast the loop runs. From flash it came out at 28.7 kHz in r1 (official image: 34.7 kHz), and a GREE air conditioner took only 25 of 40 commands. Side effect: the IR LED sends two 20 ms bursts at start-up; they carry no command. |

`platformio_override.ini` defines the build `tasmota32-ir-rf`. It is the
official `tasmota32-ir` plus the radio library folder `lib/lib_rf`, and it sets
the update address to this project's latest tested release.

## Build it yourself

You need Python 3 and [PlatformIO](https://platformio.org/install/cli).

```bash
git clone https://github.com/de-sascha/tasmota-ir-rf-remote.git
cd tasmota-ir-rf-remote
git clone --depth 1 --branch v15.4.0 https://github.com/arendst/Tasmota.git tasmota-src
python3 scripts/patch_tasmota.py tasmota-src
cp platformio_override.ini tasmota-src/
cd tasmota-src && pio run -e tasmota32-ir-rf
# result: build_output/firmware/tasmota32-ir-rf.bin and .factory.bin
```

## How releases are made

Everything runs in GitHub Actions; there is nothing to do by hand except the
hardware test.

```
new Tasmota release ──► Monday check ──► build ──► pre-release + changelog entry
                                                        │
                               test on a real box ◄─────┘
                                        │
                     "Mark release as tested" ──► normal release
                                                  (update button offers it)
```

**Version names** are `v<Tasmota version>-r<revision>`, for example
`v15.4.0-r1`. The revision counts changes to this project's additions on the
same Tasmota version.

**Workflows:**

| Workflow | Starts | Does |
|---|---|---|
| `Build firmware` (`build.yml`) | every Monday; by hand; on a pushed tag | Picks the Tasmota version (newest, or the one given), finds the next free revision, builds, checks the result (file type, size, radio and IR both present), writes the changelog entry and publishes a **pre-release** with checksums. The Monday run does nothing if the newest Tasmota is already built. |
| `Mark release as tested` (`mark-tested.yml`) | by hand | Records the hardware test in the changelog and turns the pre-release into a normal release, which makes it *latest*. |

**Checks in every build:**

- the patch script ran without complaint
- both files start like real ESP32 images
- the update file fits into the box's app partition (2,949,120 bytes)
- radio (`RfReceived`) and air-conditioner infrared (`IRHVAC`) are both inside
- the infrared carrier self-check is inside, and the carrier loop lies in fast
  internal RAM (IRAM), checked by the address of `IRsend::mark` in the build

If a build fails, GitHub sends an e-mail. GitHub also pauses the Monday run
after 60 days without any commit in the repository and sends an e-mail about
that; one click on *Enable workflow* turns it back on.

**Cutting a new revision by hand** (for example after improving the patch
script): add a section `## [v15.4.0-r2] - YYYY-MM-DD` to `CHANGELOG.md`,
commit, then push the tag `v15.4.0-r2`. The build uses that section as the
release notes.

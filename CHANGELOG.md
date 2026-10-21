# Changelog

All notable changes to this project are listed here, newest first. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Release
names are `v<Tasmota version>-r<revision>`, see
[Versions and changelog](README.md#versions-and-changelog).

Each entry ends with the **hardware test**: *pending* means the release was
built but has not run on a real box yet (it stays a pre-release); *passed*
means it has.

<!-- releases: new entries go directly below this line -->

## [v16.0.0-r2] - 2026-10-21

Built on [Tasmota 16.0.0](https://github.com/arendst/Tasmota/releases/tag/v16.0.0).

### Fixed

- Infrared commands to air conditioners arrive reliably again. The 38 kHz
  carrier is made in software, and in r1 it came out at 28.7 kHz instead of
  38 kHz (official tasmota32-ir: 34.7 kHz). A GREE air conditioner then took
  only 25 of 40 commands. The carrier loop now runs from internal RAM and is
  measured once at start-up, see [How it is built](docs/how-it-is-built.md).
  Test on the real air conditioner, from the box's own spot, 40 commands
  each: official 40/40, r1 25/40, test build of this fix 40/40.

**Hardware test:** pending.


## [v15.4.0-r2] - 2026-10-21

Built on [Tasmota 15.4.0](https://github.com/arendst/Tasmota/releases/tag/v15.4.0).

### Fixed

- Infrared commands to air conditioners arrive reliably again. The 38 kHz
  carrier is made in software, and in r1 it came out at 28.7 kHz instead of
  38 kHz (official tasmota32-ir: 34.7 kHz). A GREE air conditioner then took
  only 25 of 40 commands. The carrier loop now runs from internal RAM and is
  measured once at start-up, see [How it is built](docs/how-it-is-built.md).
  Test on the real air conditioner, from the box's own spot, 40 commands
  each: official 40/40, r1 25/40, test build of this fix 40/40.

**Hardware test:** passed on 2026-10-21: IoTorero AR01V3 at its usual spot, GREE air conditioner: IRHVAC on/off 40 of 40 (official tasmota32-ir 15.4.0 at the same spot: 40 of 40; r1: 25 of 40). CREATE ceiling fan via RfSend: 3 of 3. Carrier calibrated at start-up (period offset -1 us).


## [v16.0.0-r1] - 2026-10-20

Built automatically on [Tasmota 16.0.0](https://github.com/arendst/Tasmota/releases/tag/v16.0.0).

### Changed

- Based on Tasmota 16.0.0. The ir-rf additions are unchanged.

**Hardware test:** pending. Not to be used for air conditioners: see the known issue in v15.4.0-r1.


## [v15.4.0-r1] - 2026-10-20

First release, based on [Tasmota 15.4.0](https://github.com/arendst/Tasmota/releases/tag/v15.4.0).

### Added

- 433 MHz radio (`RfSend`, `RfReceived`) in the infrared firmware: all
  air-conditioner protocols (`IRHVAC`) and radio in one image.
- Protocol 41 for CREATE ceiling fan remotes (K9678), measured from a real
  remote.
- Raw pulse lengths of received radio codes at log level 4 (`RFR: Raw …`),
  to measure unknown remotes.
- The *Start upgrade* button fetches the newest tested release of this
  project (after `OtaUrl 1`).

**Hardware test:** failed on 2026-10-20, release withdrawn. Radio (433 MHz, CREATE fan) and TV infrared work, but IRHVAC commands to a GREE air conditioner about 3 m away arrived only about half the time (8 of 15). The official tasmota32-ir 15.4.0 on the same box and spot: every time (4 of 4). Switching off the radio receiver did not help. Under investigation.

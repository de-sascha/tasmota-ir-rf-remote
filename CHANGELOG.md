# Changelog

All notable changes to this project are listed here, newest first. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Release
names are `v<Tasmota version>-r<revision>`, see
[Versions and changelog](README.md#versions-and-changelog).

Each entry ends with the **hardware test**: *pending* means the release was
built but has not run on a real box yet (it stays a pre-release); *passed*
means it has.

<!-- releases: new entries go directly below this line -->

## [v16.0.0-r1] - 2026-10-20

Built automatically on [Tasmota 16.0.0](https://github.com/arendst/Tasmota/releases/tag/v16.0.0).

### Changed

- Based on Tasmota 16.0.0. The ir-rf additions are unchanged.

**Hardware test:** pending


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

**Hardware test:** passed on 2026-10-20: IoTorero AR01V3: 433 MHz send and receive (CREATE ceiling fan, protocol 41), infrared send and receive (TV, NEC). Air-conditioner IRHVAC not yet tried on a real unit with this build.

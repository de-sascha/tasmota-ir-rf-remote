# tasmota-ir-rf-remote: notes for Claude Code

**This repository is public.** Nothing private goes in here: no IP addresses,
host names, MQTT topics, Wi-Fi names, passwords, personal names or details of
anyone's home. Notes about specific devices and their setup belong in the
owner's private Home Assistant repository, not here. This also applies to
`.claude/memory/`, which is published with the repository.

Talk to the owner in German. Everything in this repository (code, comments,
docs, changelog, commit messages) is in English, written so that people
without deep technical knowledge can follow it.

## Session pre-flight

```bash
cd ~/github/tasmota-ir-rf-remote
git fetch origin --quiet
git status -sb
```

If `main` is behind `origin/main`: `git pull --ff-only origin main`. The build
workflows commit to `main` themselves (changelog entries), so this happens.

## How things work

- `docs/how-it-is-built.md` describes the build, the three changes to
  Tasmota, versioning (`v<Tasmota>-r<revision>`) and the release flow.
- Releases are pre-releases until a hardware test; then the workflow
  `Mark release as tested` makes them a normal release. Only normal releases
  are installed by the box's update button.
- Never mark a release as tested without a real test on a box (air conditioner
  reacts to `IRHVAC`, a radio device reacts to `RfSend`).
- A new revision by hand: add the `CHANGELOG.md` section first, then push the
  tag `v<Tasmota>-r<N>`.
- Flashing a device needs the owner's explicit go-ahead every time.

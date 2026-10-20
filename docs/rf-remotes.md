# Measuring and rebuilding a 433 MHz remote

[← back to the README](../README.md)

Most cheap 433 MHz remotes speak one of the ~40 "languages" (protocols) that
Tasmota knows. You read the code with `RfReceived` and send it back with
`RfSend`, done. This page is for the case where the box *reads* a code fine,
but your device ignores it when the box *sends* it. That happened with my
CREATE ceiling fan.

## Why receiving works but sending does not

When Tasmota receives, it is generous: a pulse may be up to 60 % longer or
shorter than the protocol says, and it still counts. When it sends, it uses
the exact timing from its table. If your remote's real timing sits between
two table entries, Tasmota still *recognises* the code, but what it sends
back is too far off for your device.

My fan's remote was received as protocol 2 *and* protocol 5 (both are
"close enough"), but neither of them, nor any other built-in protocol, made
the fan react.

## Step 1: Look at the real pulses

This firmware can print the raw pulse lengths of everything it receives.

1. Open **Tools → Console** on the box.
2. Type `WebLog 4` and press Enter (more detail in the console).
3. Press the button on your remote once.
4. Next to `RfReceived` you now also see a line like this:

   ```
   RFR: Raw 7017,360,1167,1109,427,1094,428,318,1213,313,1207, ...
   ```

5. Type `WebLog 2` to go back to the normal amount of detail.

The numbers are microseconds (µs), alternating "radio on" and "radio off":

- The **first** number is the pause before the code started (here about 7 ms).
- Then come **pairs**: on, off, on, off. Each pair is one bit.

In my case the pairs came in two shapes:

| Pair | Meaning |
|---|---|
| short on (~320 µs), long off (~1200 µs) | bit **0** |
| long on (~1100 µs), short off (~440 µs) | bit **1** |

The pause between two repeats was about 7 ms, and there was no extra start
signal. Those three facts are all it takes to describe the remote.

## Step 2: Describe it as a protocol

Protocols live in a table in Tasmota's radio library (rc-switch). One line
holds a base time and multiples of it. Protocol 41 in this firmware is my
fan's remote with a base time of 20 µs:

```c
{ 20, 0, {0,0}, 0, {0,0}, {16,60}, {55,22}, false, 291 }
//  │                       │        │              └ pause after each code: 291 × 20 µs ≈ 5.8 ms
//  │                       │        └ bit 1: 55 × 20 = 1100 µs on, 22 × 20 = 440 µs off
//  │                       └ bit 0: 16 × 20 = 320 µs on, 60 × 20 = 1200 µs off
//  └ base time in µs
```

To add your own, add a line to `scripts/patch_tasmota.py` (see
[how-it-is-built.md](how-it-is-built.md)) and build the firmware.

**Check it without guessing:** while testing, this firmware can listen to
its own transmission. If the `Raw` line of your own `RfSend` matches the
remote's line within a few dozen µs, you are there. Mine:

| | pause | bit 0 | bit 1 |
|---|---|---|---|
| original remote | 7017 | 360 / 1167 | 1109 / 427 |
| box, protocol 41 | 7020 | 336 / 1188 | 1116 / 437 |

## CREATE ceiling fans

Tested with a CREATE ceiling fan with two lights (main light with three
colour temperatures, plus a top light) and the remote **K9678**.

**The code has 30 bits, Tasmota receives only 29.** The first numbers in a
code identify the remote, so your codes will start differently from mine.
Tasmota cuts off the last bit when receiving because it sits right next to
the pause. To get the code to send:

1. Take `Data` from `RfReceived` (29 bits), for example `0xC67006E`.
2. Double it (shift left by one bit), giving `0x18CE00DC`.
3. Add the last bit. In the `Raw` line, the first number tells you which it is:
   about **7000** means the last bit is **0** (add nothing), about **6250**
   means it is **1** (add 1).

> [!TIP]
> If you are unsure, just try both: one of them makes the fan react.

My remote's codes, to show the pattern:

| Button | Received (29 bit) | Send (30 bit, protocol 41) | Behaviour |
|---|---|---|---|
| Speed 1 | `0xC67006E` | `0x18CE00DC` | sets speed 1 |
| Speed 2 | `0xC6700CC` | `0x18CE0199` | sets speed 2 |
| Speed 3 | `0xC67012B` | `0x18CE0256` | sets speed 3 |
| Speed 4 | `0xC67010B` | `0x18CE0217` | sets speed 4 |
| Speed 5 | `0xC6700EC` | `0x18CE01D8` | sets speed 5 |
| Speed 6 | `0xC67008D` | `0x18CE011B` | sets speed 6 |
| Power (fan off) | `0xC6700AD` | `0x18CE015A` | fan off |
| Direction | `0xC67014A` | `0x18CE0295` | toggles direction |
| Main light | `0xC67002F` | `0x18CE005E` | toggles main light |
| Colour | `0xC67004E` | `0x18CE009D` | next colour: warm → cold → neutral → warm |
| Top light | `0xC670189` | `0x18CE0313` | toggles top light |
| Timer 1 h | `0xC670017` | `0x18CE002F` | fan off after 1 h |
| Timer 2 h | `0xC670056` | `0x18CE00AD` | fan off after 2 h |
| Timer 4 h | `0xC670076` | `0x18CE00EC` | fan off after 4 h |
| Timer 8 h | `0xC6700B5` | `0x18CE016A` | fan off after 8 h |

Send:

```
RfSend {"Data":"0x18CE00DC","Bits":30,"Protocol":41,"Repeat":15}
```

Things worth knowing about this fan, all measured:

- **Toggles have no "on" or "off".** Main light, top light and direction
  switch to the other state each time. Home Assistant has to remember the
  state; the box reports every press of the original remote, so it can.
- **Quick off-and-on changes the colour.** If the main light is switched off
  and on again within about 6–9 seconds (by remote *or* by cutting the
  power), it moves to the next colour. Waiting 10 seconds keeps the colour.
- **After a power cut**, the main light comes on, the fan resumes its last
  speed, and the colour is the last one used.

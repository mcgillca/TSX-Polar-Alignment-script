# TSX Polar Alignment Script

**Polar alignment for TheSkyX, on Mac, Windows and Linux.**

The script takes two plate-solved images at the same declination but different
hour angles, works out where your mount's polar axis really points, and then
shows — live, updating after every image — how far to raise or lower it and
which way to rotate it. You watch the numbers shrink while your hands are on
the adjusters.

The aim is to get you close enough that after running a TPoint model, the star
you choose for accurate polar alignment is still in the field of view. In
practice it does better than that: see [How accurate is it?](#how-accurate-is-it)

![Polar Alignment](tsxpolar.png)

---

## What's new in version 2

Version 2 is a complete rewrite. Everything the old script did, it still does.

- **No more editing the script.** Exposure, binning, image scale, filter,
  subframe, declination and the two hour angles are all in a Settings dialog
  and remembered between sessions.
- **Proper installers** for macOS, Windows and Linux. Nothing to install
  first — not even Python.
- **It checks your choice of alignment points** and tells you, in plain
  numbers, what they will achieve and what is wrong with them if anything is.
  It will not let you save two points that are below your horizon.
- **It reads your custom horizon** if TheSkyX has one, so a point behind a
  tree is caught before you slew to it.
- **It waits for darkness.** If the first image has too few stars the script
  waits a minute and tries again, rather than giving up, and starts over when
  the sky is dark enough.
- **It survives a failed plate solve**, which happens routinely while you are
  moving the mount.
- **Filter names are read from your wheel** instead of typed in. If you have
  no filter wheel, the setting disappears and the script never touches one.
- **It says what it put back.** Binning, subframe and filter are restored when
  the run ends, however it ends, and the log says so.

Upgrading from v1.x: your old settings were constants inside `PAUI.py`. Open
Settings and enter them once; they are saved to `~/.tsxpolar.json` from then
on.

---

## Requirements

- **TheSkyX**, running on the same machine, with its **TCP server enabled**
  (Tools menu). The script will not start without it and will tell you so.
- A connected **mount** and **camera**.
- **TPoint pointing corrections switched off** while the script runs — see
  [Workflow](#workflow).
- An internet connection the first time you run it, so it can fetch Python and
  the libraries it needs.

You do **not** need to install Python. The installers use
[uv](https://docs.astral.sh/uv/), which they will fetch automatically, and
which keeps its own Python out of the way of anything else on your machine.

---

## Installing

Download this repository (green **Code** button → **Download ZIP**) and unzip
it, or clone it. Then:

### macOS

Double-click **TSXS Polar Alignment.app**.

The first launch opens a Terminal window while it downloads Python and the
libraries — a minute or so, once. macOS may block the app the first time
because it is not signed: right-click it and choose **Open**, or run

```
xattr -dr com.apple.quarantine "TSXS Polar Alignment.app"
```

Keep the `.app` in the folder you unzipped, beside `PAUI.py` — it runs the
script next to it.

### Windows

Double-click **install.bat**. It copies the script to your user area and puts
shortcuts on the Desktop and in the Start Menu. The first launch downloads
Python and the libraries.

To remove it later, run **uninstall.bat**.

### Linux

```
bash install.sh
```

Installs under `~/.local/` — no sudo — and adds a desktop entry. The first
launch opens a terminal window for the one-time download.

To remove it later:

```
bash install.sh --uninstall
```

### Running it directly

If you already use uv, you can skip all of the above:

```
uv run PAUI.py
```

---

## Workflow

TPoint pointing corrections must be off, or the mount will quietly steer back
towards your *previous* alignment and the script will chase its own tail. It
asks you to confirm this when you press Start.

1. Disable TPoint pointing corrections.
2. Run this script and adjust the mount until you are close enough.
3. Re-enable TPoint pointing corrections.
4. Run a TPoint calibration model.
5. Use TheSkyX's accurate polar alignment.

Both this script and TPoint only need to plate solve, so all of it can be done
before nautical dusk.

### While it is running

Press **Start**. The script slews to the first point, images, slews to the
second, images, and then shows the two corrections:

- **Altitude** — raise or lower the polar axis.
- **Azimuth** — rotate the mount, clockwise or anticlockwise *as seen from
  above*, following the TPoint convention.

Use only the mount's altitude and azimuth adjusters. **Do not move the
telescope itself** — let it track normally.

It then keeps imaging and updating the numbers as you work. While you are
turning a bolt the image will be blurred and some solves will fail; the
script says so and carries on.

You do not need perfection. Anything within 5 arcminutes is fine for guided
imaging — polar alignment only prevents field rotation. Unguided imaging wants
better, and TPoint's own routine will take you the rest of the way.

Press **Stop** when you are done. The script finishes the image it is taking
before stopping, which avoids upsetting TheSkyX.

---

## Settings

Everything lives in the **Settings** dialog and is saved to
`~/.tsxpolar.json`.

### Camera

| Setting | What it is |
|---|---|
| **Exposure** | Long enough to plate solve, and no longer — it sets how often the numbers update. |
| **Binning** | A high bin is fine and speeds up downloads. |
| **Image scale** | Arcseconds per pixel **at the binning above**. Getting this wrong is the most common cause of failed solves. |
| **Filter** | Read from your wheel. Leave as *(leave unchanged)* to use whatever is in place. Hidden entirely if you have no wheel. |
| **Frame area** | Full frame, centre half or centre quarter. Cropping speeds up solving a lot on large sensors. |

### Alignment

| Setting | Default |
|---|---|
| **Declination** | +60° |
| **First hour angle** | −1 h |
| **Second hour angle** | −5 h |

Negative hour angles are east of the meridian, positive west. The defaults
suit most northern sites; the mirror image, +1 h to +5 h, is just as good
where your western sky is the clearer one.

As you change these, the message pane tells you what they will achieve:

```
Points good.  4.0 h apart at declination +60°: 10" of plate-solve error
or flexure would put the polar axis about 16" out.
```

or what is wrong with them:

```
• The second point clears your skyline by only 0.1° (altitude 49° against
  49° at azimuth 312°).  To lift it, bring the hour angle an hour nearer
  the meridian (+7.5°), or raise the declination by 5° (+1.4°).
```

Points below your horizon cannot be saved at all.

---

## Choosing the alignment points

There is a **Choosing the points…** button in the Settings dialog with all of
this in it. In short, a good pair is:

1. **Both points visible.** Checked against TheSkyX's custom horizon if you
   have one, so a point 45° up but behind a tree is caught.

2. **Both hour angles the same sign.** Opposite signs put the two images
   either side of the meridian, so the mount flips between them and the tube
   changes sides of the pier. The script reads the change in flexure as
   misalignment.

3. **Three to five hours apart.** This is where the solve gets its leverage,
   and the error falls off as one over the separation:

   | Separation | Resulting error in the axis |
   |---|---|
   | 1 h | 63″ |
   | 2 h | 32″ |
   | 4 h | 16″ |
   | 6 h | 10″ |

   Much beyond five hours the two points sit at very different altitudes, so
   flexure differs more between them.

4. **The second point clear of the zenith and of due east and west.** Only the
   second matters — that is where the mount is standing while you adjust it.
   Near the zenith, turning the azimuth bolts does not move the star; near the
   east–west axis, turning the altitude bolts does not. Either way one of the
   two adjustments stops telling you anything and the correction is magnified.

5. **Work away from the meridian, not towards it.** The same two hour angles
   in the other order can be two or three times worse, for the reason above.

6. **Declination well away from the celestial equator.** Two axes fit both
   images equally well and the script picks the one nearer the pole. Near the
   equator that choice stops being reliable. Very close to the pole is no good
   either — the two points converge, and the script says so.

---

## How accurate is it?

Starting a few degrees out, aim for about 10 arcminutes. Run it again and the
answer will differ by roughly another 10 arcminutes, often in the opposite
direction — that spread is a fair measure of the real uncertainty.

But if you then align from that much closer starting point and drive the
numbers towards zero, 2 arcminutes is achievable, as confirmed against TPoint.
So the script can give you a good alignment on its own, without TPoint.

The floor on all this is flexure and refraction, neither of which the script
models. The figure it quotes in Settings — "10″ of plate-solve error or
flexure would put the polar axis about 16″ out" — is the best the geometry can
do, not the alignment you will walk away with.

---

## If something goes wrong

**"TheSkyX not found" when starting.** TheSkyX is not running, or its TCP
server is off. Enable it from the Tools menu, then press Retry.

**Too few stars to plate solve.** Usually the sky is still too light. The
script waits 60 seconds and tries again, as often as needed, and starts the
whole run again once it succeeds — the mount will have moved by then. Press
Stop if you would rather not wait.

**Plate solves failing from the start.** Check **Image scale** against your
**Binning** — they must match. A scale correct for 1×1 will fail at 4×4. The
script searches for the right scale if the first solve fails, and remembers
what it finds.

**The corrections look implausible.** Check the Settings message pane for a
warning about the points you have chosen, and that TPoint pointing corrections
really are off.

---

## Changelog

**V 2.0** — Rewritten in PySide6. Settings dialog and saved settings; installers
for macOS, Windows and Linux; screening and horizon checks for the alignment
points; waits for darkness; survives failed solves; reads filter names from the
wheel; restores and reports camera state; requires TheSkyX at startup.

**V 1.4** — `CAM_SUBFRAME` to use the whole frame, half or a quarter; subframe
state reset after the run.

**V 1.3** — The subframe state is left unchanged, letting users with large
cameras limit the area used for plate solving.

**V 1.2** — A filter could be specified for plate solving; image and SRC files
removed by default; binning and filter wheel position restored after the run.

**V 1.1** — Tidied up the interface. Scrollbar and Clear button.

**V 1.0** — Initial release.

# Wasl · وصل

**Messages that ride the water truck, with a receipt.**
GDG Breaking Bytes · track: *Staying Connected in the Deep Desert*.

**Live:** https://siddharth-vegesna.github.io/wasl/ (pitch deck, network simulation, design kit). The three-machine demo runs locally with one command, below.

"Wasl" means both *connection* and *receipt* in Arabic. That double meaning is the project.

## The look

Pixel art, built from nothing stock: one locked 16-colour desert palette, one pixel size, a 5×7 font and 20 sprites drawn by hand, hard edges everywhere. No gradients, blur, glow or emoji. Light sand background with ink text, because it has to be read in sunlight.

## Why this angle (the one-minute version)

Moving bytes across a dead zone is half the problem. The other half is what actually kills people. Someone who sends an SOS with no signal never learns whether anyone heard it, so they leave their vehicle or camp to look for coverage. Every desert survival guide says the same thing: stay put. Silence makes people walk.

So Wasl's product is not the message, it is the **receipt**:

1. The water truck already visits every camp. A Raspberry Pi in the cab is an offline Wi-Fi hotspot. Phones hand it their messages; it delivers them in town; replies ride back.
2. The moment the truck takes a message, the phone shows a custody receipt and an honest forecast learned from that truck's own trip history: *"Truck 7 has your message. Likely at the clinic by 03:53, 9 of 10 trips arrive by 05:38. Stay where you are."*
3. Every later hop (delivered, read, answered) comes back as another receipt.

For people who do not read: six pictograms, hold to send, and every status can be read aloud. English and Arabic.

## Run it on one laptop

```bash
./scripts/run-local.sh
```

Then open http://localhost:8081/stage (phone, truck and clinic side by side), http://localhost:8081/pitch (the deck), http://localhost:8081/sim (network simulation) and http://localhost:8081/clinic.

Setting up the Raspberry Pi and a phone: [SETUP.md](SETUP.md).

No installs. Python 3 standard library and plain HTML/JS; nothing is fetched from the internet.

## Run it with the Raspberry Pi (untested on real hardware so far)

1. Flash Raspberry Pi OS Lite (64-bit) with Raspberry Pi Imager, setting Wi-Fi, a user and SSH in its settings. Copy this folder to the Pi with `scp -r`, then run `./scripts/pi-setup.sh` on it over SSH. It installs the truck node as a boot service, then turns the Pi's Wi-Fi into a hotspot called `WASL-TRUCK-7` (password `waslwasl7`). The Pi's address becomes `10.42.0.1`. The SSH session drops at that point; that is expected.
2. Phone: join `WASL-TRUCK-7`, open `http://10.42.0.1:8080`. If the phone complains there is no internet, choose "stay connected" and switch mobile data off.
3. Laptop: join the same Wi-Fi and run:

```bash
python3 wasl.py --role clinic --port 8081 --peers http://10.42.0.1:8080
```

4. Laptop browser: `http://localhost:8081/clinic` and, in a second tab, `http://10.42.0.1:8080/truck` (the stage controls).

In one room the phone and the laptop are both in Wi-Fi range of the Pi, so use the **range emulation** buttons on the truck page (At camp / On the road / In town), or do it for real: carry the Pi out of the room, or switch Wi-Fi off on one device. Both work. Say which one you are doing.

## Three-minute demo script

1. **Truck at camp.** Open the phone app once so it is "installed", then press *On the road*. The sky goes dark: no signal, no truck, "next truck in about 3 hours".
2. **SOS with no signal.** Tap *Someone is hurt*, *Life in danger*, add a photo, hold to send. Status: *Waiting for the truck*. Nothing is lost.
3. **Truck arrives on a weak link.** Press *Weak*, then *At camp*. Dawn breaks on the phone. The SOS crosses first and the receipt appears: *"Truck 7 has your message. Stay where you are."* with the ETA. The photo is still crawling.
4. **Truck leaves mid-transfer.** Press *On the road* while the photo is partway. Phone: *"82% sent. Continues when the truck is back."* The truck manifest shows the partial.
5. **Town.** Press *Strong*, *In town*. The clinic console lights up with the case, the chain of custody and "arrived inside the promised window". Send *Stay where you are. Help is coming.*
6. **Back to camp.** Press *At camp*. The reply lands on the phone, can be read aloud, and the photo finishes from where it stopped. Next time in town the clinic sees "Delivered to Salem's phone".
7. **Scale.** Open the simulation: 27 camps, 3 trucks. Add other vehicles, start a sandstorm, point at the measured "promises kept" figure.

## How it respects the desert rules

| Rule | Answer |
| --- | --- |
| Power is scarce | The relay rides a vehicle with an alternator: 5 V from the truck's 12 V socket, about 5 W. Camps need no solar and no batteries beyond the phones people already charge. |
| Heat, dust, distance | One sealed box inside a cab. No towers, no field electronics, no line of sight. Distance is covered by a truck that makes the trip anyway. |
| Cost per user | Roughly one Pi, SD card, case and 12 V adapter per truck, on the order of $100, serving every camp on the route. Zero per-user hardware, zero airtime fees. |
| Weak or dropped link | Priority order (life-threatening first, photos last), per-request retry, resumable 8 KB chunks, and custody is only granted for bundles received whole. |
| No clock | A Pi has no clock battery and no internet. The truck learns the time from the first phone it meets. |

## What is real and what is simulated

- **Real, working code:** the node (store, sync, receipts, priority, resume, purge on delivery), the phone app, the clinic console, the truck panel, range and loss emulation.
- **Simulated, and labelled so in the UI:** camp locations and distances, the 40 past trips and 26 past visits per camp that the forecast learns from, and everything in `/sim`.
- **Not built:** phone-to-phone relaying (browsers cannot do it; it needs a native app with Wi-Fi Direct or Bluetooth), message signing, and any satellite fallback.

## The hard question, answered honestly

*"An SOS that takes a day is not an SOS."* Correct, and the simulation says so: with three trucks the median SOS reaches town in about 33 hours. Today that number is "never, unless someone walks". Wasl's claim is narrower and true: the sender **knows** within seconds of the truck arriving that help has been told, and roughly when. The same node software runs on any vehicle, so every extra carrier shortens the wait (12 extra vehicles cut the SOS median to about 24 hours in the sim). The next step is a satellite messenger on the truck used only for priority-0 bundles.

Sandstorms break the forecast, because the trip history has no storm in it. So when a truck is carrying a sandstorm alert from the clinic, new receipts promise a wider window (1.5× the median, 2.5× the 9-in-10 time) and say so. Promises made just before a storm can still break.

## Files

- `wasl.py` — the node. `--role truck` or `--role clinic`.
- `world.json` — simulated camps.
- `web/app.html` phone · `web/clinic.html` clinic · `web/truck.html` truck · `web/sim.html` simulation · `web/stage.html` all three · `web/pitch.html` deck.
- `web/common.css` is structure only; `web/pixel.css` is the skin. Add `?bare` to any page to see it without the skin.
- `web/common.js` holds the hand-drawn pixel font, the sprite set and the desert scene. `web/kit.html` (open `/kit.html`) shows all of them on one page.
- `_old_ui/` is the previous look, kept only as a backup.
- `scripts/run-local.sh`, `scripts/pi-setup.sh`, `scripts/reset-demo.sh`.
- `docs/` — the static pages behind the live link, built by `scripts/build-pages.py`.

## Status

Verified on the laptop: an automated 19-check run of sync, priority, receipts, mid-transfer drop, resume, delivery, reply and purge; and the same flow by hand through the phone, truck and clinic screens, including a photo that resumed from 9% to 82% to complete across three contacts.

Not yet done: running on the actual Raspberry Pi, testing on a real phone over the Pi's hotspot, and a native speaker's review of the Arabic text.

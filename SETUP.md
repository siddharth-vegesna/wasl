# Setting up the Raspberry Pi and the phone

One-time setup, about 30 minutes. **None of this has been run on a real Pi yet.** Follow it in order, and note anything that differs so it can be fixed here.

You need: Raspberry Pi 4, microSD card, a USB-C power supply (5 V, 3 A) or a power bank that can give 2.4 A or more, your laptop, a phone, and a Wi-Fi network that both the laptop and the Pi can join for the first ten minutes (home Wi-Fi or a phone hotspot).

## Part 1 · Flash the card (laptop, 10 min)

1. Install **Raspberry Pi Imager** from raspberrypi.com/software and open it.
2. Device: **Raspberry Pi 4**.
3. OS: **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (64-bit)**. Lite has no desktop; that is what we want.
4. Storage: your microSD card.
5. Press **Next**, then **Edit settings** when it asks about customisation. Set:
   - Hostname: `wasl`
   - Username: `pi`, and a password you will remember
   - Wireless LAN: the name and password of the Wi-Fi your laptop is on right now, and your country
   - Services tab: **Enable SSH**, **Use password authentication**
6. Save, write the card, wait for "you can remove the card".

Checkpoint: the card is written and verified with no error.

## Part 2 · First boot (5 min)

1. Put the card in the Pi and plug in power. The green light flickers while it boots.
2. Wait two full minutes. The first boot is slow.
3. On the laptop:

```bash
ssh pi@wasl.local
```

4. Answer `yes` to the fingerprint question, type the password. You should see a `pi@wasl` prompt. Type `exit`.

If it fails:

| What you see | What to do |
| --- | --- |
| `Could not resolve hostname wasl.local` | Find the Pi's IP in your router's or phone hotspot's device list and use `ssh pi@<that IP>`. Use that IP in place of `wasl.local` below. |
| `Connection refused` or it hangs | Wait another minute and retry. If still nothing, the Wi-Fi details were wrong: reflash and retype them. |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | You reflashed the card. Run `ssh-keygen -R wasl.local` and try again. |

## Part 3 · Copy Wasl to the Pi (2 min)

On the laptop, from inside the project folder:

```bash
rsync -av --exclude data --exclude _old_ui --exclude .git ./ pi@wasl.local:wasl/
```

Checkpoint: it lists `wasl.py`, `world.json` and the `web/` files, then finishes with a "sent ... bytes" line.

## Part 4 · Turn the Pi into the truck (2 min)

```bash
ssh -t pi@wasl.local wasl/scripts/pi-setup.sh
```

What should happen, in order:

1. `1/2 Installing the wasl service ...`
2. `truck node is answering on port 8080`
3. `2/2 Switching Wi-Fi to hotspot "WASL-TRUCK-7" in 3 seconds. This SSH session will drop: that is expected.`
4. The connection freezes or closes. That is correct: the Pi has left your Wi-Fi and become its own.

If step 2 says the node is **not** answering, do not continue. Run `ssh pi@wasl.local journalctl -u wasl -n 30` and send me the output.

## Part 5 · Check the hotspot (laptop, 3 min)

1. On the laptop, open Wi-Fi settings. After about 20 seconds a network called **WASL-TRUCK-7** appears. Join it, password `waslwasl7`. The laptop will say there is no internet. That is correct.
2. Open http://10.42.0.1:8080/truck in the browser. You should see the truck panel with the desert scene.
3. Check the Pi comes back by itself after a power cut: unplug it, plug it back in, wait 90 seconds, rejoin `WASL-TRUCK-7`, reload the truck panel. **This matters: on demo day you only want to plug it in.**

If the network never appears, connect a keyboard and screen to the Pi, log in, and run `nmcli connection show` and `cat /tmp/wasl-hotspot.log`. Send me both.

## Part 6 · The phone (5 min)

1. Switch **mobile data off** (or use Airplane mode and then turn Wi-Fi back on). Otherwise the phone may quietly prefer mobile data.
2. Join **WASL-TRUCK-7**, password `waslwasl7`.
   - iPhone: when it says "No Internet Connection", tap **Use Without Internet** or just stay.
   - Android: when it asks, tap **Stay connected** / "Don't ask again".
3. In the browser, type the whole address including `http://`:

```
http://10.42.0.1:8080
```

4. Enter a name, pick **Umm Ghaf**. The sky should turn to day with the truck parked, and the box should say "Truck 7 is here."
5. Set the phone's **auto-lock to Never** for the demo. When the screen sleeps, the page stops syncing.
6. Optional: use the browser's "Add to Home Screen" so it opens like an app.

Test hold-to-send with your thumb now: tap a picture, hold the red button for a second. If the page scrolls or zooms instead of sending, tell me which phone and browser.

## Part 7 · The laptop as the clinic

While joined to `WASL-TRUCK-7`:

```bash
python3 wasl.py --role clinic --port 8081 --peers http://10.42.0.1:8080
```

Then open http://localhost:8081/clinic. The tag at the top right should say **Truck 7 in range**. Keep http://10.42.0.1:8080/truck open in a second tab: those are your range buttons.

## Later · Updating the Pi after code changes

With the laptop joined to `WASL-TRUCK-7`, from inside the project folder:

```bash
rsync -av --exclude data --exclude _old_ui --exclude .git ./ pi@10.42.0.1:wasl/
```

```bash
ssh pi@10.42.0.1 sudo systemctl restart wasl
```

## Useful commands on the Pi

| Command | What it tells you |
| --- | --- |
| `systemctl status wasl` | Is the truck node running |
| `journalctl -u wasl -n 30` | Its last 30 log lines |
| `nmcli connection show --active` | Is the hotspot up |
| `sudo shutdown -h now` | Power off safely. Pulling the plug risks corrupting the card. |
| `sudo nmcli connection delete Hotspot && sudo reboot` | Undo everything: back to normal Wi-Fi |

## Things that go wrong on demo day

- **Weak power.** A cheap cable or small power bank makes the Pi's Wi-Fi flaky. Use the official supply or a bank rated 2.4 A or more.
- **The venue's Wi-Fi is crowded.** The Pi's hotspot shares the 2.4 GHz band with everyone. Keep the phone and laptop within a few metres of the Pi.
- **The phone hops networks.** If it shows "No truck nearby" while the Pi is next to it, it has left `WASL-TRUCK-7`. Rejoin and turn off auto-join for the venue's Wi-Fi.
- **The laptop has no internet** while on the Pi's network. Everything you need is local: the deck is at `/pitch`.

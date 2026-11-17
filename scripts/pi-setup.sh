#!/usr/bin/env bash
# Turn a Raspberry Pi (Raspberry Pi OS Lite, Bookworm or newer) into a Wasl truck node.
# Safe to run over Wi-Fi SSH: the service is installed first, and the hotspot switch happens
# last, detached, so losing the SSH session does not interrupt it.
# Undo (back to normal Wi-Fi):  sudo nmcli connection delete Hotspot && sudo reboot
set -e
SSID="${SSID:-WASL-TRUCK-7}"
PASS="${PASS:-waslwasl7}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v nmcli >/dev/null; then
  echo "NetworkManager (nmcli) not found. This OS is too old: reflash with a current Raspberry Pi OS Lite."
  exit 1
fi

echo "1/2 Installing the wasl service ..."
sudo tee /etc/systemd/system/wasl.service >/dev/null <<EOF
[Unit]
Description=Wasl truck node
After=network.target

[Service]
User=$USER
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/wasl.py --role truck --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now wasl.service
sleep 2
if curl -fs http://localhost:8080/api/world >/dev/null; then echo "    truck node is answering on port 8080"; else echo "    WARNING: truck node is not answering; check: journalctl -u wasl -n 30"; fi

echo "2/2 Switching Wi-Fi to hotspot \"$SSID\" in 3 seconds. This SSH session will drop: that is expected."
sudo nohup sh -c "sleep 3; nmcli device wifi hotspot ifname wlan0 ssid '$SSID' password '$PASS'; nmcli connection modify Hotspot connection.autoconnect yes connection.autoconnect-priority 100" >/tmp/wasl-hotspot.log 2>&1 &

echo
echo "Next: join Wi-Fi \"$SSID\" (password: $PASS) and open http://10.42.0.1:8080"
echo "Truck panel: http://10.42.0.1:8080/truck    SSH again with: ssh $USER@10.42.0.1"

#!/usr/bin/env bash
# Start a truck node and a clinic node on this laptop. Ctrl-C stops both.
cd "$(dirname "$0")/.." || exit 1
python3 wasl.py --role truck --port 8080 &
T=$!
python3 wasl.py --role clinic --port 8081 --peers http://localhost:8080 &
C=$!
trap 'kill $T $C 2>/dev/null' EXIT INT TERM
sleep 1
echo
echo "  Stage (phone + truck + clinic):  http://localhost:8081/stage"
echo "  Simulation:                      http://localhost:8081/sim"
echo "  Clinic console:                  http://localhost:8081/clinic"
echo "  Phone app:                       http://localhost:8080/"
echo "  Truck panel:                     http://localhost:8080/truck"
echo
wait

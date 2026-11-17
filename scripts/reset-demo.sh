#!/usr/bin/env bash
# Wipe the truck and the clinic and reseed the simulated history, so a demo starts clean.
#   ./scripts/reset-demo.sh              laptop only (truck on localhost)
#   ./scripts/reset-demo.sh 10.42.0.1    truck is the Raspberry Pi
TRUCK="${1:-localhost}"
STAMP="$(date +%s)"
ok() { curl -fs -m 4 -X POST "http://$1/api/admin/reset" -d '{}' >/dev/null && echo "  reset $2" || echo "  COULD NOT REACH $2 at http://$1"; }
ok "$TRUCK:8080" "truck"
ok "localhost:8081" "clinic"
curl -fs -m 4 -X POST "http://$TRUCK:8080/api/admin/link" -d '{"position":"camp","quality":"strong"}' >/dev/null && echo "  truck parked at camp, strong link"
echo
echo "Now open this on the phone (it also wipes the phone's old messages):"
echo "  http://$TRUCK:8080/?wipe=$STAMP"

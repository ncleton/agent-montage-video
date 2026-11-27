#!/bin/sh
# Routeur Valhalla du studio, sur la boucle locale uniquement, avec le graphe routier libre.
set -eu
studio=$(cd "$(dirname "$0")" && pwd)
data="$studio/data"
container=bigup-studio-routing
volume=bigup-studio-valhalla-data
image=ghcr.io/valhalla/valhalla-scripted:3.9.1

if ! docker info --format '{{.ServerVersion}}' >/dev/null; then
  echo 'Valhalla : démarrez Docker Desktop sur le poste de montage.' >&2
  exit 1
fi
if ! docker container inspect "$container" >/dev/null 2>&1; then
  mkdir -p "$data/valhalla"
  for region in nord-pas-de-calais picardie; do
    pbf="$data/valhalla/$region.osm.pbf"
    if [ ! -s "$pbf" ]; then
      curl -fLsS --retry 2 "https://download.geofabrik.de/europe/france/$region/$region-latest.osm.pbf" -o "$pbf.part"
      mv "$pbf.part" "$pbf"
    fi
  done
  docker volume create "$volume" >/dev/null
  docker create --name "$container" --restart unless-stopped -p 127.0.0.1:55816:8002 \
    -v "$volume:/custom_files" -e build_admins=False -e build_time_zones=False \
    -e serve_tiles=True "$image" >/dev/null
fi
if [ "$(docker inspect -f '{{.State.Running}}' "$container")" != true ]; then
  for region in nord-pas-de-calais picardie; do
    pbf="$data/valhalla/$region.osm.pbf"
    [ -s "$pbf" ] || { echo "Valhalla : extrait OpenStreetMap absent : $pbf" >&2; exit 1; }
    docker cp "$pbf" "$container:/custom_files/"
  done
  docker start "$container" >/dev/null
fi
attempt=0
until curl -fsS -m 5 http://127.0.0.1:55816/status >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 120 ] || { echo "Valhalla non prêt : docker logs $container" >&2; exit 1; }
  sleep 5
done
printf '%s\n' "$image" > "$data/valhalla-enabled"
echo 'Valhalla répond sur 127.0.0.1:55816.'

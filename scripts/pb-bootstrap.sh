#!/usr/bin/env bash
# Idempotent first-time setup for the Film Room Tagger PocketBase store.
# Runs on the VPS after `docker compose up`. Safe to re-run.
set -euo pipefail

PB_CONTAINER="flim-review-pocketbase"
PB_URL="http://127.0.0.1:8090"
SUPERUSER_EMAIL="${PB_SUPERUSER_EMAIL:-tagreel@flim.local}"
SUPERUSER_PASSWORD="${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD must be set}"
COLLECTION="tagreel"

echo "Waiting for PocketBase to be healthy..."
for i in $(seq 1 30); do
  if curl -fsS "$PB_URL/api/health" -o /dev/null 2>/dev/null; then
    echo "PocketBase is up."; break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then echo "PocketBase did not become healthy."; exit 1; fi
done

# 1) Ensure a superuser exists (idempotent). `superuser create` fails if it already exists.
if ! docker exec "$PB_CONTAINER" pocketbase superuser list 2>/dev/null | grep -q "$SUPERUSER_EMAIL"; then
  echo "Creating superuser $SUPERUSER_EMAIL"
  docker exec "$PB_CONTAINER" pocketbase superuser create "$SUPERUSER_EMAIL" "$SUPERUSER_PASSWORD" || true
else
  echo "Superuser already exists."
fi

# 2) Authenticate as superuser.
TOKEN=$(curl -fsS -X POST "$PB_URL/api/collections/_superusers/auth-with-password" \
  -H "Content-Type: application/json" \
  -d "{\"identity\":\"$SUPERUSER_EMAIL\",\"password\":\"$SUPERUSER_PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
AUTH="Authorization: Bearer $TOKEN"

# 3) Ensure the tagreel collection exists with public read/write rules + name/data fields.
COLLECTIONS=$(curl -fsS "$PB_URL/api/collections?perPage=500" -H "$AUTH")
if echo "$COLLECTIONS" | python3 -c "import sys,json; sys.exit(0 if any(c['name']=='$COLLECTION' for c in json.load(sys.stdin)['items']) else 1)"; then
  echo "Collection '$COLLECTION' already exists."
else
  echo "Creating collection '$COLLECTION'..."
  SCHEMA=$(cat <<JSON
{
  "name": "$COLLECTION",
  "type": "base",
  "listRule": "",
  "viewRule": "",
  "createRule": "",
  "updateRule": "",
  "deleteRule": "",
  "fields": [
    {"name":"name","type":"text","required":true,"unique":true,"options":{"min":1,"max":64}},
    {"name":"data","type":"json","required":false,"options":{"maxSize":2000000}}
  ]
}
JSON
)
  curl -fsS -X POST "$PB_URL/api/collections" -H "$AUTH" -H "Content-Type: application/json" -d "$SCHEMA" -o /dev/null
  echo "Collection created."
fi

# 4) Seed the three logical documents if missing.
seed_if_missing() {
  local NAME="$1" DATA="$2"
  local EXISTS
  EXISTS=$(curl -fsS "$PB_URL/api/collections/$COLLECTION/records?filter=name%3D%27$NAME%27" -H "$AUTH" \
    | python3 -c "import sys,json; print('yes' if json.load(sys.stdin)['totalItems']>0 else 'no')")
  if [ "$EXISTS" = "no" ]; then
    echo "Seeding $NAME"
    curl -fsS -X POST "$PB_URL/api/collections/$COLLECTION/records" -H "$AUTH" -H "Content-Type: application/json" \
      -d "{\"name\":\"$NAME\",\"data\":$DATA}" -o /dev/null
  else
    echo "$NAME already present."
  fi
}

seed_if_missing "roster/main"  '["Aidan","Zay","Martise","Jakari","Darrias","Josiah","Alijah","Chris","Tatt","Jonquil"]'
seed_if_missing "codes/main"   '[]'
seed_if_missing "session/current" '{"entries":[],"createdAt":""}'

echo "PocketBase bootstrap complete."

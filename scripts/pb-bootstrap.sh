#!/bin/sh
# Idempotent first-time setup for the Film Room Tagger PocketBase store.
# Runs on the VPS after `docker compose up`. POSIX sh only (no bash, no python).
set -eu

PB_CONTAINER="flim-review-pocketbase"
PB_URL="http://127.0.0.1:8090"
SUPERUSER_EMAIL="${PB_SUPERUSER_EMAIL:-tagreel@flim.local}"
SUPERUSER_PASSWORD="${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD must be set}"
COLLECTION="tagreel"

echo "Waiting for PocketBase to be healthy..."
i=0
while [ "$i" -lt 30 ]; do
  if curl -fsS "$PB_URL/api/health" >/dev/null 2>&1; then
    echo "PocketBase is up."; break
  fi
  i=$((i + 1)); sleep 2
  if [ "$i" -eq 30 ]; then echo "PocketBase did not become healthy."; exit 1; fi
done

# 1) Upsert superuser (create or update) so its password matches the persisted one.
echo "Upserting superuser $SUPERUSER_EMAIL"
docker exec "$PB_CONTAINER" /pb/pocketbase --dir=/pb_data superuser upsert "$SUPERUSER_EMAIL" "$SUPERUSER_PASSWORD"

# 2) Authenticate as superuser -> extract token.
TOKEN=$(curl -fsS -X POST "$PB_URL/api/collections/_superusers/auth-with-password" \
  -H "Content-Type: application/json" \
  -d "{\"identity\":\"$SUPERUSER_EMAIL\",\"password\":\"$SUPERUSER_PASSWORD\"}" \
  | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
if [ -z "$TOKEN" ]; then echo "Failed to authenticate as superuser."; exit 1; fi
AUTH="Authorization: Bearer $TOKEN"

# 3) Ensure the tagreel collection exists with public read/write rules + name/data fields.
COLLS=$(curl -fsS "$PB_URL/api/collections?perPage=500" -H "$AUTH")
echo "Existing collections: $(echo "$COLLS" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p' | tr '\n' ' ')"
if echo "$COLLS" | grep -q "\"name\":\"$COLLECTION\""; then
  echo "Collection '$COLLECTION' already exists."
else
  echo "Creating collection '$COLLECTION'..."
  SCHEMA=$(cat <<'JSON'
{
  "name": "tagreel",
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
  echo "Create response: $(curl -s -X POST "$PB_URL/api/collections" -H "$AUTH" -H "Content-Type: application/json" -d "$SCHEMA")"
  echo "Collection created."
fi

# 4) Seed the three logical documents if missing.
seed_if_missing() {
  NAME="$1"; DATA="$2"
  TOTAL=$(curl -fsS -G --data-urlencode "filter=name='$NAME'" \
    "$PB_URL/api/collections/$COLLECTION/records" -H "$AUTH" \
    | sed -n 's/.*"totalItems":\([0-9]*\).*/\1/p')
  TOTAL="${TOTAL:-0}"
  if [ "${TOTAL:-0}" -eq 0 ]; then
    echo "Seeding $NAME"
    curl -fsS -X POST "$PB_URL/api/collections/$COLLECTION/records" -H "$AUTH" -H "Content-Type: application/json" \
      -d "{\"name\":\"$NAME\",\"data\":$DATA}" >/dev/null
  else
    echo "$NAME already present."
  fi
}

seed_if_missing "roster/main"  '["Aidan","Zay","Martise","Jakari","Darrias","Josiah","Alijah","Chris","Tatt","Jonquil"]'
seed_if_missing "codes/main"   '[]'
seed_if_missing "session/current" '{"entries":[],"createdAt":""}'

echo "PocketBase bootstrap complete."

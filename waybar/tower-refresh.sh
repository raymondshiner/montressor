#!/usr/bin/env bash
# One SSH round trip that snapshots everything the two `tower` waybar modules
# need (Minecraft + torrent stack), written atomically to a cache file.
#
# The bar-refresh path must stay cheap, so nothing here runs inline from waybar:
# tower-mc-status.sh / tower-dl-status.sh read the cache and fire this in the
# background only when the snapshot has gone stale.
set -uo pipefail

HOST="${TOWER_HOST:-sirlexicon@192.168.86.31}"
CACHE=/tmp/waybar-tower.json
LOCK=/tmp/waybar-tower.lock

exec 9>"$LOCK"
flock -n 9 || exit 0   # a refresh is already in flight

OUT=$(ssh -o ConnectTimeout=6 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$HOST" 'bash -s' 2>/dev/null <<'REMOTE'
set -uo pipefail

# ---------- minecraft ----------
MC_ACTIVE=$(systemctl is-active minecraft 2>/dev/null)
MC_ENABLED=$(systemctl is-enabled minecraft 2>/dev/null)
MC_SINCE=$(systemctl show minecraft -p ActiveEnterTimestamp --value 2>/dev/null)
MC_MEM=$(systemctl show minecraft -p MemoryCurrent --value 2>/dev/null)
case "$MC_MEM" in ''|*[!0-9]*) MC_MEM=0 ;; esac
MC_UP=0
[ -n "$MC_SINCE" ] && MC_UP=$(( $(date +%s) - $(date -d "$MC_SINCE" +%s 2>/dev/null || date +%s) ))

MC_N=0; MC_NAMES=""
if [ "$MC_ACTIVE" = active ] && [ -n "$MC_SINCE" ]; then
  read -r MC_N MC_NAMES <<< "$(sudo journalctl -u minecraft --since "$MC_SINCE" --no-pager 2>/dev/null \
    | grep -oE '[A-Za-z0-9_]{3,16} (joined|left) the game' \
    | awk '{ if ($2=="joined") o[$1]=1; else delete o[$1] }
           END { n=0; s=""; for (k in o) { n++; s = s (s==""?"":",") k } print n, s }')"
fi
case "$MC_N" in ''|*[!0-9]*) MC_N=0 ;; esac
MC_VER=""
[ -n "$MC_SINCE" ] && MC_VER=$(sudo journalctl -u minecraft --since "$MC_SINCE" --no-pager 2>/dev/null \
  | grep -oiE 'Loading Minecraft [0-9][0-9.]* with Fabric Loader [0-9][0-9.]*' | head -1 \
  | awk '{print $3" / Fabric "$NF}')
LOAD=$(cut -d' ' -f1-3 /proc/loadavg)
# Must be asked from tower, not the laptop — the laptop is usually on Mullvad,
# which would report the VPN exit as the Minecraft connect address.
PUB=$(curl -s --max-time 8 https://api.ipify.org 2>/dev/null)

# ---------- torrent stack ----------
GJ=$(sudo docker exec gluetun wget -qO- --timeout=10 https://am.i.mullvad.net/json 2>/dev/null)
[ -z "$GJ" ] && GJ='{}'
TOR=$(sudo docker exec gluetun wget -qO- --timeout=5 http://127.0.0.1:8080/api/v2/torrents/info 2>/dev/null)
echo "$TOR" | jq -e 'type=="array"' >/dev/null 2>&1 || TOR='[]'

CJ='{}'
GSTART=$(date -d "$(sudo docker inspect -f '{{.State.StartedAt}}' gluetun 2>/dev/null)" +%s 2>/dev/null || echo 0)
STALE=""
for c in gluetun qbittorrent prowlarr flaresolverr; do
  S=$(sudo docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo missing)
  H=$(sudo docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$c" 2>/dev/null)
  CJ=$(echo "$CJ" | jq -c --arg c "$c" --arg s "${S:-missing}" --arg h "$H" '. + {($c): {status:$s, health:$h}}')
  if [ "$c" != gluetun ] && [ "$S" = running ]; then
    D=$(date -d "$(sudo docker inspect -f '{{.State.StartedAt}}' "$c" 2>/dev/null)" +%s 2>/dev/null || echo 0)
    [ "$D" -lt "$GSTART" ] && STALE="$STALE $c"
  fi
done
STALEJ=$(printf '%s' "$STALE" | tr ' ' '\n' | jq -R . | jq -sc 'map(select(length>0))')

# qBittorrent hardening — read the config, not the API (no auth needed).
CONF=/opt/torrentstack/qbittorrent/qBittorrent/qBittorrent.conf
PROT_BAD=""
if sudo test -r "$CONF"; then
  chk() { V=$(sudo sed -n "s|^$1=||p" "$CONF" | tail -1); V=${V:-unset}
          [ "$V" = "$2" ] || PROT_BAD="$PROT_BAD $3"; }
  chk 'Session\\DHTEnabled'              false DHT
  chk 'Session\\PeXEnabled'              false PeX
  chk 'Session\\LSDEnabled'              false LSD
  chk 'Session\\AnonymousModeEnabled'    true  anon
  chk 'Session\\Encryption'              1     encryption
  chk 'Connection\\UPnP'                 false UPnP
  chk 'Session\\GlobalMaxRatio'          0     ratio
  chk 'Session\\GlobalMaxSeedingMinutes' 0     seedtime
fi
PROTJ=$(printf '%s' "$PROT_BAD" | tr ' ' '\n' | jq -R . | jq -sc 'map(select(length>0))')

WD_TIMER=$(systemctl is-active vpn-guard.timer 2>/dev/null)
WD_TS=""; WD_ST=""; WD_MSG=""
[ -r /run/vpn-guard.state ] && IFS=$'\t' read -r WD_TS WD_ST WD_MSG < /run/vpn-guard.state

INC=$(df -h --output=avail,size /srv/incomplete 2>/dev/null | awk 'NR==2{print $1" free of "$2}')
MED=$(df -h --output=avail,size /srv/media 2>/dev/null | awk 'NR==2{print $1" free of "$2}')
INCP=$(df --output=pcent /srv/incomplete 2>/dev/null | awk 'NR==2{gsub(/[ %]/,"");print}')
MEDP=$(df --output=pcent /srv/media 2>/dev/null | awk 'NR==2{gsub(/[ %]/,"");print}')
WAIT=$(find /srv/media/downloads -type f 2>/dev/null | wc -l)

jq -nc \
  --arg mc_active "$MC_ACTIVE" --arg mc_enabled "$MC_ENABLED" \
  --argjson mc_up "${MC_UP:-0}" --argjson mc_mem "${MC_MEM:-0}" \
  --argjson mc_n "$MC_N" --arg mc_names "$MC_NAMES" \
  --arg mc_ver "$MC_VER" --arg load "$LOAD" --arg pub "$PUB" \
  --argjson gluetun "$GJ" --argjson torrents "$TOR" \
  --argjson containers "$CJ" --argjson stale "$STALEJ" --argjson prot "$PROTJ" \
  --arg wd_timer "$WD_TIMER" --arg wd_ts "$WD_TS" --arg wd_st "$WD_ST" --arg wd_msg "$WD_MSG" \
  --arg inc "$INC" --arg med "$MED" --argjson incp "${INCP:-0}" --argjson medp "${MEDP:-0}" \
  --argjson waiting "${WAIT:-0}" \
'{
  mc: { active:$mc_active, enabled:$mc_enabled, uptime:$mc_up, mem:$mc_mem,
        players:$mc_n, names:($mc_names|split(",")|map(select(length>0))),
        version:$mc_ver, load:$load, public:$pub },
  dl: {
    mullvad:   ($gluetun.mullvad_exit_ip // false),
    exit_ip:   ($gluetun.ip // null),
    city:      ($gluetun.city // null),
    server:    ($gluetun.mullvad_exit_ip_hostname // null),
    containers:$containers,
    stale:     $stale,
    unhardened:$prot,
    watchdog:  { timer:$wd_timer, state:$wd_st, ts:$wd_ts, msg:$wd_msg },
    disk:      { incomplete:$inc, incomplete_pct:$incp, media:$med, media_pct:$medp, waiting:$waiting },
    torrents:  {
      total:       ($torrents|length),
      downloading: ($torrents|map(select(.state|test("^(downloading|metaDL|forcedDL|stalledDL)$")))|length),
      speed:       ($torrents|map(.dlspeed)|add // 0),
      top:         ($torrents|sort_by(-.dlspeed)|.[0:4]
                    |map({name:.name, pct:((.progress*100)|floor), speed:.dlspeed, state:.state}))
    }
  }
}'
REMOTE
)

if [ -n "$OUT" ] && printf '%s' "$OUT" | jq -e . >/dev/null 2>&1; then
  printf '%s' "$OUT" | jq -c --argjson ts "$(date +%s)" '. + {ts:$ts, reachable:true}' > "$CACHE.tmp"
else
  jq -nc --argjson ts "$(date +%s)" '{ts:$ts, reachable:false}' > "$CACHE.tmp"
fi
mv -f "$CACHE.tmp" "$CACHE"

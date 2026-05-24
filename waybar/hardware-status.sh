#!/bin/bash
# Two /proc/stat reads 0.3s apart for accurate CPU sample
cpu1=$(awk '/^cpu /{for(i=2;i<=NF;i++) s+=$i; print s, $5; s=0}' /proc/stat)
sleep 0.3
cpu2=$(awk '/^cpu /{for(i=2;i<=NF;i++) s+=$i; print s, $5; s=0}' /proc/stat)

read -r total1 idle1 <<< "$cpu1"
read -r total2 idle2 <<< "$cpu2"

dtotal=$((total2 - total1))
didle=$((idle2 - idle1))
cpu_pct=$(( dtotal > 0 ? (dtotal - didle) * 100 / dtotal : 0 ))

mem_total=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
mem_avail=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
ram_pct=$(( (mem_total - mem_avail) * 100 / mem_total ))

agg=$(( cpu_pct > ram_pct ? cpu_pct : ram_pct ))

if   [ "$agg" -ge 85 ]; then class="crit"
elif [ "$agg" -ge 60 ]; then class="warn"
else                         class="ok"
fi

printf '{"text":"󰻠","class":"%s","tooltip":"CPU %d%%  ·  RAM %d%%"}\n' \
    "$class" "$cpu_pct" "$ram_pct"

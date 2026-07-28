#!/bin/bash
# Claude 앱이 살아있는지 확인하고, 죽어 있으면 다시 띄운다.
#
# 한국에 가 있는 동안 맥은 모니터 없이 혼자 돌아간다. 예약 발행은 이 앱이
# 실행 중일 때만 동작하므로, 앱이 크래시하거나 업데이트로 종료되면 그날부터
# 브리핑이 멈춘다. 곁에 아무도 없으니 스스로 되살아나야 한다.
#
# launchd 가 5분마다 호출한다: ~/Library/LaunchAgents/com.nachimban.claude-keeper.plist

LOG="$HOME/nachimban/ops/keeper.log"
MAIN="/Applications/Claude.app/Contents/MacOS/Claude"

# 로그가 무한정 커지지 않게 (1MB 넘으면 절반만 남김)
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 1048576 ]; then
  tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

if pgrep -f "$MAIN" > /dev/null 2>&1; then
  exit 0          # 정상 — 조용히 종료
fi

echo "$(date '+%Y-%m-%d %H:%M:%S')  Claude 앱이 꺼져 있어 다시 실행합니다" >> "$LOG"
open -a "Claude" >> "$LOG" 2>&1

sleep 20
if pgrep -f "$MAIN" > /dev/null 2>&1; then
  echo "$(date '+%Y-%m-%d %H:%M:%S')  재실행 성공" >> "$LOG"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S')  ⚠️ 재실행 실패 — 원격 접속 필요" >> "$LOG"
fi

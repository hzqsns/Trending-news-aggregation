#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/.pids"

echo -e "${YELLOW}正在停止投研 Agent 服务...${NC}"

if [ -f "$PID_FILE" ]; then
    while read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  停止进程 $pid"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

# fallback: kill by port
for port in 8000 5173; do
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null
        echo "  释放端口 $port"
    fi
done

echo -e "${GREEN}✅ 所有服务已停止${NC}"

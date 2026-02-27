#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
PID_FILE="$PROJECT_DIR/.pids"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    # kill child processes
    kill 0 2>/dev/null
    echo -e "${GREEN}已停止所有服务${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  📊 投研 Agent — 一键启动${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# --- Clean up stale processes on ports ---
for port in 8000 5173; do
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}⚠ 端口 $port 被占用，正在释放...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    fi
done

# --- Check prerequisites ---
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}⚙️  首次运行：创建 Python 虚拟环境...${NC}"
    python3 -m venv "$BACKEND_DIR/venv" || python -m venv "$BACKEND_DIR/venv"
    echo -e "${YELLOW}⚙️  安装后端依赖...${NC}"
    "$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}⚙️  首次运行：安装前端依赖...${NC}"
    cd "$FRONTEND_DIR" && pnpm install
fi

# --- Start Backend ---
echo -e "${GREEN}▶ 启动后端 (FastAPI) ...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

sleep 2

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${RED}✗ 后端启动失败，请检查日志${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ 后端已启动 → http://127.0.0.1:8000${NC}"

# --- Start Frontend ---
echo -e "${GREEN}▶ 启动前端 (Vite) ...${NC}"
cd "$FRONTEND_DIR"
pnpm dev &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"

sleep 3

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ 项目已启动！${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  🌐 前端地址:  ${CYAN}http://localhost:5173${NC}"
echo -e "  🔌 后端地址:  ${CYAN}http://127.0.0.1:8000${NC}"
echo -e "  📖 API 文档:  ${CYAN}http://127.0.0.1:8000/docs${NC}"
echo ""
echo -e "  👤 默认账号:  admin / admin123"
echo ""
echo -e "  ${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

wait

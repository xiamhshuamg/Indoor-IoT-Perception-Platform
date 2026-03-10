const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8003";

console.log("API_BASE:", API_BASE);  // 调试信息

function toWsUrl(httpBase) {
  const url = new URL(httpBase);
  url.protocol = "ws";
  // 重要：确保路径为 /ws
  if (!url.pathname || url.pathname === '/') {
    url.pathname = '/ws';
  } else if (!url.pathname.endsWith('/ws')) {
    url.pathname = '/ws';  // 强制设置为 /ws
  }
  const wsUrl = url.toString();
  console.log("WebSocket URL:", wsUrl);
  return wsUrl;
}

export function connectWs(onMsg, onOnline) {
    let ws = null;
    let alive = true;
    let retry = 0;

    const connect = () => {
        if (!alive) return;

        const wsUrl = toWsUrl(API_BASE);
        console.log("尝试连接 WebSocket:", wsUrl);  // 调试信息

        try {
            ws = new WebSocket(wsUrl);
        } catch (error) {
            console.error("创建 WebSocket 失败:", error);
            return;
        }

        ws.onopen = () => {
            console.log("✅ WebSocket 连接成功");
            retry = 0;
            onOnline?.(true);
            try { ws.send("ping"); } catch {}
        };

        ws.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                console.log("📨 收到 WebSocket 消息:", data.type);
                onMsg(data);
            } catch (error) {
                console.error("解析 WebSocket 消息失败:", error);
            }
        };

        ws.onerror = (error) => {
            console.error("❌ WebSocket 错误:", error);
            try { ws.close(); } catch {}
        };

        ws.onclose = (event) => {
            console.log(`🔌 WebSocket 连接关闭，代码: ${event.code}, 原因: ${event.reason}`);
            onOnline?.(false);
            if (!alive) return;
            retry += 1;
            const backoff = Math.min(4000, 300 + retry * 350);
            console.log(`⏳ ${backoff}ms 后重试...`);
            window.setTimeout(connect, backoff);
        };
    };

    connect();

    const timer = window.setInterval(() => {
        try {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send("ping");
            }
        } catch {}
    }, 5000);

    return () => {
        console.log("🛑 清理 WebSocket 连接");
        alive = false;
        window.clearInterval(timer);
        try {
            if (ws) {
                ws.close(1000, "正常关闭");
            }
        } catch {}
    };
}
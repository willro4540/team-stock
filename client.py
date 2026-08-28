"""
client.py — 소켓 채팅 클라이언트 (파트4)
────────────────────────────────────────
· 문제: recv()는 블로킹 함수 → 메인(UI) 스레드에서 돌리면 화면이 멈춤
· 해결: 수신 전용 스레드 + Qt Signal
    수신 스레드가 emit() → Qt가 메인 스레드로 안전하게 전달 → 슬롯에서 UI 갱신
    (스레드에서 UI를 직접 만지면 안 됨! Signal이 다리 역할)
· 송신은 짧게 끝나므로 메인 스레드에서 바로 sendall
"""
import json
import socket
import threading

from PySide6.QtCore import QObject, Signal


class ChatClient(QObject):
    # ── Signal 정의: 수신 스레드 → UI 스레드 통신 통로 ──
    message_received = Signal(dict)    # chat/notice/dm 수신 시
    users_updated = Signal(list)       # user_list 수신 시
    disconnected = Signal()            # 연결 끊김

    def __init__(self):
        super().__init__()
        self.sock = None
        self.name = ""

    def connect_server(self, host: str, port: int, name: str) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3)               # 3초 안에 연결 안 되면 실패
            self.sock.connect((host, port))
            self.sock.settimeout(None)            # 연결 후엔 무제한 대기(recv)
            self.name = name
            self._send({"type": "join", "name": name})
            # 수신 루프는 별도 스레드로 — UI가 멈추지 않게
            threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except OSError:
            self.sock = None
            return False

    def _recv_loop(self):
        buf = ""
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data.decode()
                while "\n" in buf:                # 줄 단위 = 메시지 단위
                    line, buf = buf.split("\n", 1)
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    if msg.get("type") == "user_list":
                        self.users_updated.emit(msg["users"])   # ★ emit → UI로
                    else:
                        self.message_received.emit(msg)
        except (OSError, json.JSONDecodeError):
            pass
        self.disconnected.emit()

    # ── 송신 3종 — 전부 JSON 한 줄로 ──
    def send_chat(self, msg):
        self._send({"type": "chat", "from": self.name, "msg": msg})

    def send_notice(self, msg):                    # admin 전용 (화면에서 제한)
        self._send({"type": "notice", "from": self.name, "msg": msg})

    def send_dm(self, to, msg):                    # 귓속말 — 서버가 대상에게만 전달
        self._send({"type": "dm", "from": self.name, "to": to, "msg": msg})

    def _send(self, obj: dict):
        if self.sock:
            try:
                self.sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())
            except OSError:
                pass

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None


# ── 단독 테스트 (학습용) — GUI 없이 콘솔로 프로토콜 확인 ─────
# 터미널1에서 python server.py 실행해둔 뒤, 주석 풀고 python client.py
# if __name__ == "__main__":
#     import sys, time
#     from PySide6.QtCore import QCoreApplication
#     app = QCoreApplication(sys.argv)
#     c = ChatClient()
#     c.message_received.connect(lambda m: print("수신:", m))
#     c.users_updated.connect(lambda u: print("접속자:", u))
#     if c.connect_server("127.0.0.1", 9500, "테스터"):
#         c.send_chat("소켓 테스트 메시지입니다")
#     else:
#         print("서버 연결 실패 — server.py 먼저 실행했는지 확인")
#     app.exec()

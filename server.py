"""
server.py — 소켓 채팅 서버 (파트4)
────────────────────────────────────────
· 커리큘럼 19~30강 socket 기반. 관리자 PC가 서버 역할 (계획서 명세)
· 구조: accept 루프 → 접속마다 스레드 1개 (threading) → 다중 접속 처리
· JSON 프로토콜 — 메시지마다 type으로 분기 (문서 5.5 파트4):
    {"type":"join",   "name":...}                 클라→서버 : 입장 신고
    {"type":"chat",   "from":..., "msg":...}      전체 브로드캐스트
    {"type":"notice", "from":..., "msg":...}      공지 (admin) 브로드캐스트
    {"type":"dm",     "from":..., "to":..., ...}  귓속말 — 대상에게만 전송
    {"type":"user_list", "users":[...]}           서버→전체 : 접속자 목록
· 메시지 구분: 한 줄(\\n) = 메시지 1개  → recv 버퍼를 줄 단위로 잘라 처리
"""
import json
import socket
import threading

HOST = "0.0.0.0"      # 모든 네트워크 인터페이스에서 접속 허용 (같은 LAN)
PORT = 9500


class ChatServer:
    def __init__(self, host=HOST, port=PORT):
        self.host, self.port = host, port
        self.clients = {}                 # {socket: 이름} — 접속자 관리의 핵심
        self.lock = threading.Lock()      # 여러 스레드가 clients를 동시에 만지므로 잠금
        self.running = False

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 재시작 시 "포트 사용 중" 오류 방지
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        self.running = True
        print(f"[서버] {self.host}:{self.port} 대기 중")
        while self.running:
            try:
                conn, addr = self.sock.accept()
                print("www")
            except OSError:
                break                     # stop()으로 소켓이 닫힌 경우
            # ★ 접속 1명 = 스레드 1개 (daemon=True: 메인 종료 시 같이 종료)
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

    # ── 클라이언트 1명 전담 스레드 ──
    def _handle(self, conn: socket.socket):
        name = "?"
        buf = ""
        try:
            while True:
                data = conn.recv(4096)
                if not data:              # 빈 데이터 = 연결 끊김
                    break
                buf += data.decode()
                # 줄 단위로 잘라서 JSON 파싱 (TCP는 경계가 없어서 직접 구분 필요)
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    name = self._route(conn, msg, name)
        except (ConnectionError, json.JSONDecodeError):
            pass
        finally:
            with self.lock:
                self.clients.pop(conn, None)
            conn.close()
            self._broadcast_users()       # 퇴장도 목록 갱신으로 알림

    # ── type별 분기 — 프로토콜 설계의 핵심 ──
    def _route(self, conn, msg, name):
        t = msg.get("type")
        if t == "join":
            name = msg["name"]
            with self.lock:
                self.clients[conn] = name
            self._broadcast_users()
        elif t in ("chat", "notice"):
            self._broadcast(msg)          # 전체에게
        elif t == "dm":
            self._send_to(msg["to"], msg)  # 대상에게만 = 귓속말
            self._send_conn(conn, msg)     # 보낸 본인 화면에도 표시
        return name

    def _broadcast(self, msg: dict):
        with self.lock:
            targets = list(self.clients.keys())
        for c in targets:
            self._send_conn(c, msg)

    def _send_to(self, to_name: str, msg: dict):
        with self.lock:
            targets = [c for c, n in self.clients.items() if n == to_name]
        for c in targets:
            self._send_conn(c, msg)

    def _send_conn(self, conn, msg: dict):
        try:
            conn.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode())
        except OSError:
            pass                          # 전송 실패한 소켓은 recv 쪽에서 정리됨

    def _broadcast_users(self):
        with self.lock:
            users = sorted(set(self.clients.values()))
        self._broadcast({"type": "user_list", "users": users})


def run_in_background() -> ChatServer:
    """앱 안에서 서버를 백그라운드 스레드로 실행 (관리자 PC = 서버 겸용)"""
    sv = ChatServer()
    threading.Thread(target=sv.start, daemon=True).start()
    return sv


if __name__ == "__main__":
    # 서버 단독 실행:  python server.py   (관리자 PC에서)
    ChatServer().start()

# ── 단독 테스트 (학습용) ──────────────────────────────
# 터미널 2개로 실습:
#   터미널1:  python server.py
#   터미널2:  python client.py   (client.py 하단 테스트 주석 해제 후)

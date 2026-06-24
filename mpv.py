import os
import tempfile
import subprocess
import json
import socket
import time

class MpvIPC:
    SPEED_MIN, SPEED_MAX, SPEED_STEP = 0.5, 2.0, 0.25

    def __init__(self, media: str):
        self._sock_path = tempfile.mktemp(suffix='.sock')
        self._proc = subprocess.Popen(
            ['mpv', '--no-video', f'--input-ipc-server={self._sock_path}', '--pause', media],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if os.path.exists(self._sock_path):
                break
            time.sleep(0.1)
        self._s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._s.connect(self._sock_path)
        self._s.settimeout(0.3)
        self._buf, self._id = b'', 0
        self.speed = 1.0

    def _cmd(self, cmd: list):
        self._id += 1
        self._s.sendall((json.dumps({'command': cmd, 'request_id': self._id}) + '\n').encode())

    def get_time(self) -> float:
        self._cmd(['get_property', 'time-pos'])
        deadline = time.monotonic() + 0.4
        while time.monotonic() < deadline:
            try:
                self._buf += self._s.recv(4096)
            except (socket.timeout, BlockingIOError):
                pass
            while b'\n' in self._buf:
                line, self._buf = self._buf.split(b'\n', 1)
                try:
                    obj = json.loads(line)
                    if obj.get('request_id') == self._id and 'data' in obj:
                        return float(obj['data'] or 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
        return 0.0

    def play(self):  self._cmd(['set_property', 'pause', False])
    def pause(self): self._cmd(['set_property', 'pause', True])
    def seek(self, t: float): self._cmd(['seek', t, 'absolute'])
    def seek_rel(self, delta: float): self._cmd(['seek', delta, 'relative'])

    def faster(self):
        self.speed = min(self.SPEED_MAX, round(self.speed + self.SPEED_STEP, 2))
        self._cmd(['set_property', 'speed', self.speed])

    def slower(self):
        self.speed = max(self.SPEED_MIN, round(self.speed - self.SPEED_STEP, 2))
        self._cmd(['set_property', 'speed', self.speed])

    def close(self):
        for fn in (self._proc.terminate, self._s.close):
            try:
                fn()
            except Exception as e:
                print('error terminating mpv subprocess')
                print(e)
        try:
            os.unlink(self._sock_path)
        except Exception as e:
            print('error unlinking socket')
            print(e)



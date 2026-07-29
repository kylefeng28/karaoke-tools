from python_mpv_jsonipc import MPV

class MpvIPC:
    SPEED_MIN, SPEED_MAX, SPEED_STEP = 0.5, 2.0, 0.25

    def __init__(self, media: str):
        self.mpv = MPV(mpv_args=['--no-video', '--pause'])
        self.mpv.loadfile(media)
        self.speed = 1.0

    def _cmd(self, cmd: list[str]):
        return self.mpv.command(*cmd)

    def get_time(self) -> float:
        return self._cmd(['get_property', 'time-pos'])

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
        self.mpv.stop()

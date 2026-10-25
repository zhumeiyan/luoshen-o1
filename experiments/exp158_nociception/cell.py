import os, signal, time, random

class Body:
    """真实细胞身体：每个细胞是一个真实子进程。"""
    def __init__(self, n):
        self.cells = {}
        for i in range(n):
            self.cells[i] = self._spawn()
        self.next_id = n
        self.dead_ids = []
        self.births = 0
        self.deaths = 0

    def _spawn(self):
        pid = os.fork()
        if pid == 0:
            try:
                time.sleep(60)
            finally:
                os._exit(0)
        self.births = getattr(self, 'births', 0) + 1
        return pid

    def kill(self, cid):
        """真实损伤：SIGKILL。返回是否真的死了。"""
        pid = self.cells.get(cid)
        if pid is None:
            return False
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            pid2, st = os.waitpid(pid, 0)
            sig = os.WTERMSIG(st) if os.WIFSIGNALED(st) else None
        except ChildProcessError:
            sig = 9
        del self.cells[cid]
        self.deaths += 1
        self.dead_ids.append(cid)
        return sig == 9

    def heal(self, cid):
        """真实修复：fork 一个新细胞。"""
        if cid in self.cells:
            return False
        self.cells[cid] = self._spawn()
        return True

    def alive(self):
        return len(self.cells)

    def reap(self):
        """回收全部，不留僵尸。"""
        for cid, pid in list(self.cells.items()):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        self.cells.clear()

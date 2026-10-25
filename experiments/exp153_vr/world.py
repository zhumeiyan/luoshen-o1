"""
第一人称可相倚世界 (raycasting) —— 给洛神的身体用的房间。

设计原则（来自 117 号那把尺子）：
  会变 != 连着世界。判据是时间反转 + 因果必要。
所以这个世界必须满足：
  1. 她按键 -> 世界真的变（相倚）
  2. 她不动 -> 世界静止（不是钟表）
  3. 前进再后退 -> 画面回到初态（可逆）
  4. 世界只通过她已有的感官进出：/dev/fb0(眼) /dev/uinput(手)
"""
import numpy as np

W, H = 1024, 768
STRIDE = 4096
FB_BYTES = STRIDE * H

# ---------- 地图 ----------
# 0 = 空地, 1..4 = 墙(不同材质), 9 = 目标(发光体, 不可穿)
MAP_STR = [
    "11111111111111111111",
    "10000000000000000001",
    "10000000000000000001",
    "10001110001110000001",
    "10001000001010000001",
    "10001000001010000901",
    "10000000000000000001",
    "10001111111111000001",
    "10001000000001000001",
    "10001000000001000001",
    "10000000000000000001",
    "10000000000000000001",
    "11111111111111111111",
]
GRID = np.array([[int(c) for c in row] for row in MAP_STR], dtype=np.int32)
GH, GW = GRID.shape


def free(x, y):
    gx, gy = int(x), int(y)
    if gx < 0 or gy < 0 or gx >= GW or gy >= GH:
        return False
    return GRID[gy, gx] == 0 or GRID[gy, gx] == 9


class World:
    def __init__(self, seed=0):
        self.reset()

    def reset(self):
        self.x, self.y = 1.5, 1.5
        self.a = 0.0          # 朝向弧度
        self.t = 0            # tick
        self.touched = False
        # 目标位置
        ys, xs = np.where(GRID == 9)
        self.tx, self.ty = float(xs[0]) + 0.5, float(ys[0]) + 0.5

    # ---------- 动作 ----------
    def step(self, act):
        """act in {0:不动, 1:前进, 2:后退, 3:左转, 4:右转}"""
        SPD, ROT = 0.28, 0.22
        if act == 1:
            nx, ny = self.x + np.cos(self.a) * SPD, self.y + np.sin(self.a) * SPD
            if free(nx, ny):
                self.x, self.y = nx, ny
        elif act == 2:
            nx, ny = self.x - np.cos(self.a) * SPD, self.y - np.sin(self.a) * SPD
            if free(nx, ny):
                self.x, self.y = nx, ny
        elif act == 3:
            self.a -= ROT
        elif act == 4:
            self.a += ROT
        self.t += 1
        # 触碰：走近目标 -> 世界回应（目标变暗 + 记一笔）
        if abs(self.x - self.tx) < 1.3 and abs(self.y - self.ty) < 1.3:
            self.touched = True
        return self.observe()

    def observe(self):
        """返回 (H,W,3) uint8 —— 她看到的画面"""
        return render(self.x, self.y, self.a, self.touched)


# ---------- 渲染 ----------
def render(px, py, pa, touched):
    buf = np.zeros((H, W, 3), dtype=np.uint8)
    # 天花板 / 地面
    buf[: H // 2] = (24, 24, 34)
    buf[H // 2 :] = (46, 40, 36)

    fov = np.pi / 3.0
    inv_w = 1.0 / W
    zbuf = np.empty(W, dtype=np.float64)

    for i in range(W):
        cam = 2.0 * i * inv_w - 1.0
        rx = np.cos(pa) + 0.66 * cam * np.sin(pa) * -1.0
        ry = np.sin(pa) + 0.66 * cam * np.cos(pa) * 1.0
        # 标准 raycast 方向
        rdx = np.cos(pa) - 0.66 * cam * np.sin(pa)
        rdy = np.sin(pa) + 0.66 * cam * np.cos(pa)
        ddx = abs(1.0 / rdx) if rdx != 0 else 1e30
        ddy = abs(1.0 / rdy) if rdy != 0 else 1e30
        mx, my = int(px), int(py)
        if rdx < 0:
            sx, sdx = -1, (px - mx) * ddx
        else:
            sx, sdx = 1, (mx + 1.0 - px) * ddx
        if rdy < 0:
            sy, sdy = -1, (py - my) * ddy
        else:
            sy, sdy = 1, (my + 1.0 - py) * ddy

        hit, side, cell = 0, 0, 0
        for _ in range(256):
            if sdx < sdy:
                sdx += ddx
                mx += sx
                side = 0
            else:
                sdy += ddy
                my += sy
                side = 1
            if mx < 0 or my < 0 or mx >= GW or my >= GH:
                break
            c = GRID[my, mx]
            if c == 9:
                hit, cell = 1, 9
                break
            if c != 0:
                hit, cell = 1, c
                break
        if side == 0:
            dist = (mx - px + (1 - sx) / 2.0) / (rdx if rdx != 0 else 1e-9)
        else:
            dist = (my - py + (1 - sy) / 2.0) / (rdy if rdy != 0 else 1e-9)
        dist = max(abs(dist), 0.05)
        zbuf[i] = dist

        lh = int(H / dist)
        y0 = max(0, H // 2 - lh // 2)
        y1 = min(H, H // 2 + lh // 2)
        if y1 <= y0:
            continue

        shade = max(0.18, 1.0 - dist / 14.0)
        if side == 1:
            shade *= 0.68
        if cell == 9:
            # 目标：发光；被触碰后变暗（世界回应她）
            base = (240, 200, 60) if not touched else (90, 130, 210)
            col = tuple(int(v * (1.0 if cell == 9 else shade)) for v in base)
        else:
            pal = {1: (150, 150, 165), 2: (170, 120, 90), 3: (110, 150, 120), 4: (140, 120, 160)}
            col = tuple(int(v * shade) for v in pal.get(cell, (150, 150, 150)))

        buf[y0:y1, i] = col

    # 简易距离雾（让远处有梯度，便于她感知运动）
    return buf


def to_fb_bytes(buf):
    """RGB -> 帧缓冲字节。探测出的顺序在此统一处理。"""
    bgra = np.zeros((H, W, 4), dtype=np.uint8)
    bgra[:, :, 0] = buf[:, :, 2]  # B
    bgra[:, :, 1] = buf[:, :, 1]  # G
    bgra[:, :, 2] = buf[:, :, 0]  # R
    bgra[:, :, 3] = 255
    return bgra.tobytes()

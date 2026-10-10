#!/usr/bin/env python3
"""Frame-accurate reel renderer.

Pulls frames straight from the HDR iPhone sources (HLG -> SDR tone-mapped in float, kept at
16 bit), applies piecewise time remapping (speed ramps with shutter blending, optical-flow
slow motion), per-frame whip bridges / cross-mixes / flashes, per-clip balance + a global look,
then encodes H.264 + AAC for Instagram.

usage: reel.py edl.json out.mp4 [--preview] [--frames a:b]
       reel.py edl.json outdir --stills --at f1,f2,...   (frame indices)
"""
import json, math, subprocess, os, argparse
import numpy as np
import cv2

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOTION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion")
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=pc,format=rgb48le")
FPS = 30


# ----------------------------------------------------------------------------- sources
class Source:
    """Decodes frames of one clip on demand (CFR 30 fps grid identical to the analysis proxies)."""

    def __init__(self, clip, W, H, pre="", chunk=40, keep=150):
        self.clip, self.W, self.H, self.pre, self.chunk, self.keep = clip, W, H, pre, chunk, keep
        self.path = os.path.join(SRC_DIR, f"{clip}.mov")
        self.cache = {}
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", self.path], capture_output=True, text=True).stdout
        self.n = int(math.floor(float(out) * FPS + 1e-6))
        mp = os.path.join(MOTION_DIR, f"{clip}.json")
        self.dx = np.zeros(self.n + 2, np.float32)
        if os.path.exists(mp):
            for r in json.load(open(mp)):
                k = int(round(r[0] * FPS))
                if k < len(self.dx):
                    self.dx[k] = r[1]

    def _decode(self, f0, f1):
        f0, f1 = max(0, f0), min(self.n, f1)
        scale = "" if (self.W, self.H) == (1080, 1920) else f",scale={self.W}:{self.H}:flags=lanczos"
        pre = (self.pre + ",") if self.pre else ""
        # temporal denoisers need a few frames of history: decode a little earlier and drop it
        lead = 4 if self.pre else 0
        g0 = max(0, f0 - lead)
        vf = f"fps={FPS},trim=start_frame={g0}:end_frame={f1},setpts=PTS-STARTPTS,{pre}{TONEMAP}{scale}"
        cmd = ["ffmpeg", "-v", "error", "-i", self.path, "-map", "0:v:0", "-vf", vf,
               "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        fs = self.W * self.H * 3 * 2
        for k in range(len(raw) // fs):
            idx = g0 + k
            if idx < f0 and idx in self.cache:
                continue
            a = np.frombuffer(raw, dtype=np.uint16, count=self.W * self.H * 3, offset=k * fs)
            self.cache[idx] = a.reshape(self.H, self.W, 3)
        if len(self.cache) > self.keep:
            centre = (f0 + f1) / 2
            for key in sorted(self.cache, key=lambda x: abs(x - centre), reverse=True)[: len(self.cache) - self.keep]:
                del self.cache[key]

    def frame16(self, idx):
        idx = int(min(max(idx, 0), self.n - 1))
        if idx not in self.cache:
            self._decode(idx - 1, idx + self.chunk)
        return self.cache[idx]

    def frame(self, idx):
        return self.frame16(idx).astype(np.float32) / 65535.0

    def interp(self, x):
        """optical-flow interpolated frame at fractional frame position x."""
        i0 = math.floor(x); a = x - i0
        if a < 0.04:
            return self.frame(i0)
        if a > 0.96:
            return self.frame(i0 + 1)
        return flow_interp(self.frame(i0), self.frame(i0 + 1), a)

    def motion_dx(self, idx):
        idx = int(min(max(idx, 0), self.n - 1))
        return float(self.dx[idx]) * self.W / 1080


_dis = None
def flow_interp(A, B, a):
    """Bidirectional DIS optical-flow interpolation at fraction a in (0,1)."""
    global _dis
    if _dis is None:
        _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    s = 0.5
    ga = cv2.cvtColor((cv2.resize(A, None, fx=s, fy=s) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor((cv2.resize(B, None, fx=s, fy=s) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    fab = _dis.calc(ga, gb, None); fba = _dis.calc(gb, ga, None)
    H, W = A.shape[:2]
    fab = cv2.resize(fab, (W, H)) / s; fba = cv2.resize(fba, (W, H)) / s
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    wa = cv2.remap(A, gx - a * fab[..., 0], gy - a * fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    wb = cv2.remap(B, gx - (1 - a) * fba[..., 0], gy - (1 - a) * fba[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return (1 - a) * wa + a * wb


# ----------------------------------------------------------------------------- helpers
def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def piecewise(pts, t):
    """linear interpolation through [[t, v], ...]; linear extrapolation at the ends."""
    if t <= pts[0][0]:
        (t0, s0), (t1, s1) = pts[0], pts[1]
    elif t >= pts[-1][0]:
        (t0, s0), (t1, s1) = pts[-2], pts[-1]
    else:
        for k in range(len(pts) - 1):
            if pts[k][0] <= t <= pts[k + 1][0]:
                (t0, s0), (t1, s1) = pts[k], pts[k + 1]
                break
    return s0 + (s1 - s0) * (t - t0) / (t1 - t0)


def hblur(img, k):
    k = int(round(k))
    if k <= 1:
        return img
    return cv2.blur(img, (k, 1), borderType=cv2.BORDER_REFLECT)


def shift_x(img, dx):
    if abs(dx) < 0.5:
        return img
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def zoom(img, s, cx=0.5, cy=0.5):
    if abs(s - 1) < 1e-4:
        return img
    H, W = img.shape[:2]
    M = np.float32([[s, 0, (1 - s) * cx * W], [0, s, (1 - s) * cy * H]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def zoom_at(zk, t):
    """zoom keyframes [[t, scale, cx, cy], ...] with smoothstep easing between keys."""
    if t <= zk[0][0]:
        return zk[0][1:]
    if t >= zk[-1][0]:
        return zk[-1][1:]
    for j in range(len(zk) - 1):
        if zk[j][0] <= t <= zk[j + 1][0]:
            a = smooth((t - zk[j][0]) / (zk[j + 1][0] - zk[j][0]))
            return [zk[j][q] + (zk[j + 1][q] - zk[j][q]) * a for q in (1, 2, 3)]


# ----------------------------------------------------------------------------- grading
def grade(img, g, glob):
    lin = np.power(np.clip(img, 0, 1), 2.2)
    lin = lin * (2 ** g.get("exposure", 0.0)) * np.array(g.get("wb", [1, 1, 1]), np.float32)
    knee = glob.get("knee", 0.82)       # soft highlight roll-off (white walls / transoms)
    lin = np.where(lin > knee, knee + (1 - knee) * np.tanh((lin - knee) / (1 - knee)), lin)
    img = np.power(np.clip(lin, 0, 1), 1 / 2.2)
    c = glob.get("contrast", 0.0) + g.get("contrast", 0.0)
    if c:
        p = glob.get("pivot", 0.45)
        img = np.where(img < p, p * np.power(img / p, 1 + c), 1 - (1 - p) * np.power((1 - img) / (1 - p), 1 + c))
    lift = glob.get("lift", 0.0)
    if lift:
        img = lift + (1 - lift) * img
    luma = img[..., 0:1] * 0.2126 + img[..., 1:2] * 0.7152 + img[..., 2:3] * 0.0722
    sat = glob.get("saturation", 1.0) * g.get("saturation", 1.0)
    if sat != 1.0:
        img = luma + (img - luma) * sat
    hw = np.array(glob.get("high_tint", [0, 0, 0]), np.float32)
    sw = np.array(glob.get("shadow_tint", [0, 0, 0]), np.float32)
    if hw.any() or sw.any():
        wh = np.clip((luma - 0.45) / 0.55, 0, 1); ws = np.clip((0.45 - luma) / 0.45, 0, 1)
        img = img + wh * hw + ws * sw
    return np.clip(img, 0, 1)


def make_vignette(W, H, strength):
    if not strength:
        return None
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (x - W / 2) / (W / 2); ny = (y - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 + ny ** 2 * 0.55)
    v = 1 - strength * np.clip((r - 0.55) / 0.75, 0, 1) ** 2
    return v[..., None].astype(np.float32)


# ----------------------------------------------------------------------------- renderer
class Reel:
    def __init__(self, edl, preview=False):
        self.edl = edl
        self.W, self.H = (540, 960) if preview else (1080, 1920)
        self.N = int(round(edl["duration"] * FPS))
        self.segs = edl["segments"]
        for s in self.segs:
            s["f_in"] = int(round(s["tl_in"] * FPS)); s["f_out"] = int(round(s["tl_out"] * FPS))
        self.fx = {}
        for e in edl.get("frame_fx", []):
            self.fx.setdefault(e["f"], []).append(e)
        self.glob = edl.get("grade", {})
        self.vig = make_vignette(self.W, self.H, self.glob.get("vignette", 0.0))
        self.sources = {}
        self.core_cache = {}

    def seg_of(self, i):
        for k, s in enumerate(self.segs):
            if s["f_in"] <= i < s["f_out"]:
                return k
        return len(self.segs) - 1

    def src(self, seg):
        c = seg["clip"]
        if c not in self.sources:
            self.sources[c] = Source(c, self.W, self.H, pre=seg.get("pre", ""))
        return self.sources[c]

    def layer(self, k, i):
        """graded frame of segment k at output frame i (time-remapped, shutter-blended, zoomed)."""
        s = self.segs[k]; S = self.src(s)
        t = i / FPS
        lo = piecewise(s["map"], t - 0.5 / FPS) * FPS
        hi = piecewise(s["map"], t + 0.5 / FPS) * FPS
        mid = piecewise(s["map"], t) * FPS
        span = hi - lo
        if span > 1.3:                                   # sped up: emulate a longer shutter
            n = max(2, int(round(span)))
            idxs = [round(lo + (j + 0.5) * span / n) for j in range(n)]
            img = sum(S.frame(x) for x in idxs) / n
            streak = abs(np.mean([S.motion_dx(x) for x in idxs])) * (span - 1) * s.get("streak", 0.8)
            img = hblur(img, min(streak, 260 * self.W / 1080))
        elif span < 0.8 and s.get("flow", True):         # slow motion: optical-flow interpolation
            img = S.interp(mid)
        else:
            img = S.frame(round(mid))
        if "zoom" in s:
            zs, cx, cy = zoom_at(s["zoom"], t)
            img = zoom(img, zs, cx, cy)
        return grade(img, s.get("grade", {}), self.glob)

    def core(self, i):
        """frame i after per-frame fx (shift / blur / brightness), before cross-mixing."""
        if i in self.core_cache:
            return self.core_cache[i]
        k = self.seg_of(i)
        img = self.layer(k, i)
        for e in self.fx.get(i, []):
            if e.get("dx"):
                img = shift_x(img, e["dx"] * self.W / 1080)
            if e.get("blur"):
                img = hblur(img, e["blur"] * self.W / 1080)
            if e.get("bright"):
                img = np.clip(img + e["bright"], 0, 1)
        self.core_cache[i] = img
        for key in [x for x in self.core_cache if x < i - 3]:
            del self.core_cache[key]
        return img

    def final(self, i):
        img = self.core(i)
        for e in self.fx.get(i, []):
            if "mix" in e:                                # cross-mix with the neighbouring output frame
                j = i + (1 if e["mix"] == "next" else -1)
                img = img * (1 - e["a"]) + self.core(j) * e["a"]
        if self.vig is not None:
            img = img * self.vig
        sh = self.glob.get("sharpen", 0.0)
        if sh:
            bl = cv2.GaussianBlur(img, (0, 0), 1.2 * self.W / 1080)
            img = np.clip(img + sh * (img - bl), 0, 1)
        return img

    def to8(self, img, rng):
        ga = self.glob.get("grain", 0.0)
        if ga:
            g = rng.standard_normal((self.H // 2, self.W // 2), dtype=np.float32)
            g = cv2.resize(g, (self.W, self.H), interpolation=cv2.INTER_LINEAR)[..., None]
            lum = img.mean(axis=2, keepdims=True)
            img = img + ga * g * (0.35 + 0.65 * (1 - np.abs(2 * lum - 1)))
        return np.clip(img * 255 + rng.uniform(-0.5, 0.5, img.shape).astype(np.float32), 0, 255).astype(np.uint8)

    def free(self, i):
        k = self.seg_of(i)
        active = {self.segs[j]["clip"] for j in range(max(0, k - 1), min(len(self.segs), k + 2))}
        for c in list(self.sources):
            if c not in active:
                del self.sources[c]

    def encoder(self, out, preview):
        aud = self.edl["audio"]; D = self.edl["duration"]
        fo = aud.get("fade_out", 0.06); fi = aud.get("fade_in", 0.02)
        af = (f"atrim=start={aud.get('start', 0)}:duration={D},asetpts=PTS-STARTPTS,"
              f"afade=t=in:d={fi},afade=t=out:st={D - fo:.3f}:d={fo},aresample=48000")
        cmd = ["ffmpeg", "-v", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}", "-r", str(FPS), "-i", "-",
               "-i", aud["file"],
               "-filter_complex", f"[0:v]scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v];[1:a]{af}[a]",
               "-map", "[v]", "-map", "[a]",
               "-c:v", "libx264", "-preset", "medium" if preview else "slower", "-crf", "20" if preview else "16", "-maxrate", "20M", "-bufsize", "40M",
               "-profile:v", "high", "-level", "4.2", "-g", "60", "-bf", "2",
               "-x264-params", "aq-mode=3:deblock=-1,-1",
               "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
               "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart",
               "-t", str(D), out]
        return subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def run(self, out, preview=False, frames=None, stills=None):
        rng = np.random.default_rng(7)
        enc = None if stills is not None else self.encoder(out, preview)
        it = stills if stills is not None else (range(*frames) if frames else range(self.N))
        for i in it:
            img8 = self.to8(self.final(i), rng)
            if stills is not None:
                cv2.imwrite(os.path.join(out, f"f{i:04d}.png"), cv2.cvtColor(img8, cv2.COLOR_RGB2BGR))
            else:
                enc.stdin.write(img8.tobytes())
            if i % 60 == 0:
                print(f"frame {i}/{self.N}  clip {self.segs[self.seg_of(i)]['clip']}", flush=True)
            self.free(i)
        if enc:
            enc.stdin.close(); enc.wait(); print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edl"); ap.add_argument("out")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--frames")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--at", help="comma-separated output frame indices for --stills")
    a = ap.parse_args()
    edl = json.load(open(a.edl))
    r = Reel(edl, preview=a.preview)
    if a.stills:
        os.makedirs(a.out, exist_ok=True)
        r.run(a.out, stills=[int(x) for x in a.at.split(",")])
    else:
        r.run(a.out, preview=a.preview, frames=tuple(int(x) for x in a.frames.split(":")) if a.frames else None)

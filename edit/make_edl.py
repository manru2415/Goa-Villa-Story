#!/usr/bin/env python3
"""EDL v4 - user's corrected sequence (clip 2 removed) synced line-by-line to the lyrics.

Order: 1, 3, 5, 6, 7, 8, 9, 4, 10, 11, 12, 13 (one clip per lyric line).
Lyric timings measured on the isolated vocal stem (UVR MDX-Net) + Whisper + syllable onsets:
  1 tujhko meri zaroorat     0.69-2.0      7 o mannu chadh gaye        12.07-14.1  (chadh 12.72)
  2 aa main tujhko utha loon 2.67-4.2      8 meri soniye aaye          14.20-15.7  (so- 14.71)
    (utha ~3.36-3.6)                       9 roko na                   16.03-16.9
  3 dheere dheere se chalna  4.66-6.2     10 toko na                   17.06-17.7
  4 apni adaa ...            6.52-8.2     11 o mujhko peene de raj ke  18.07-20.6  (over the drum break)
  5 o meri whiskey aaye      8.2-9.45     12 ghul mil ghul mil launda  20.72 ->     (the drop)
    (whis- 8.82)
  6 o meri tharra aaye       9.68-11.8 (thar- 10.72)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 28.0
NIGHT_DN = "hqdn3d=3:3:5:5"
INT_DN = "hqdn3d=1.5:1.5:4:4"


def F(f):
    return f / FPS


def seg(clip, tl_in, tl_out, src_in, pieces, **kw):
    """pieces: [(src_end, speed), ...]; the last piece may use speed=None = fit to tl_out."""
    m = [[tl_in, src_in]]
    t, s = tl_in, src_in
    for k, (se, sp) in enumerate(pieces):
        if sp is None:
            assert k == len(pieces) - 1
            m.append([tl_out, se])
            t, s = tl_out, se
        else:
            t = t + (se - s) / sp
            s = se
            m.append([t, s])
    assert abs(m[-1][0] - tl_out) < 1e-6, (clip, m[-1][0], tl_out)
    d = dict(clip=clip, tl_in=tl_in, tl_out=tl_out, map=m)
    d.update(kw)
    return d


# cut points on the 30 fps grid
C = [0, F(73), F(139), F(194), F(253), F(291), F(351), F(420), F(478), F(508), F(538), F(621), DUR]

segments = [
    # 1  door burst: face in the gap on "tujh" (0.69); slow push-in
    seg(1, C[0], C[1], 6.77, [(6.77 + C[1], 1.0)],
        zoom=[[C[0], 1.0, 0.5, 0.625], [C[1], 1.08, 0.5, 0.625]]),
    # 2  pool lift: meet on "aa" (2.67), lift completes (src 2.50) on "utha" (3.60), grin, 1.9x whip out
    seg(3, C[1], C[2], 2.50 - (3.60 - C[1]), [(3.20, 1.0), (3.84, None)],
        pre=NIGHT_DN, grade=dict(exposure=0.12, wb=[1.04, 1.0, 0.96])),
    # 3  stairs: looks up on "se", arms out on "chal-", laugh at the end of "chalna", 2x whip
    seg(5, C[2], C[3], C[2] - 0.80, [(5.47, 1.0), (5.87, None)], grade=dict(exposure=-0.05)),
    # 4  sofa: plops in, then the pose in 0.5x slow motion on "apni adaa", pan out
    seg(6, C[3], C[4], 3.70, [(4.25, 1.0), (4.80, 0.5), (5.20, None)],
        zoom=[[C[3], 1.0, 0.6, 0.6], [C[3] + 0.55, 1.0, 0.6, 0.6], [C[3] + 1.65, 1.05, 0.6, 0.6], [C[4], 1.05, 0.6, 0.6]]),
    # 5  toast: the CLINK (src 4.03) on "whis-" (8.82), glasses to lens on "aaye", 2x whip
    seg(7, C[4], C[5], C[4] - 4.79, [(4.70, 1.0), (5.12, None)],
        zoom=[[C[4], 1.15, 0.5, 0.484], [C[5], 1.15, 0.5, 0.484]]),
    # 6  three guys: sofa-drop gag (src 1.60) on "thar-" (10.72), arms crossed, whip
    seg(8, C[5], C[6], C[5] - 9.12, [(C[6] - 9.12, 1.0)], pre=INT_DN,
        zoom=[[C[5], 1.06, 0.5, 0.599], [C[6], 1.06, 0.5, 0.599]]),
    # 7  bottle-on-head guy: "o mannu chadh gaye" - stare (src 9.33) on "-ye" (13.28), whip
    seg(9, C[6], C[7], 7.75, [(7.75 + C[7] - C[6], 1.0)],
        zoom=[[C[6], 1.08, 0.444, 0.885], [C[7], 1.08, 0.444, 0.885]],
        grade=dict(exposure=-0.12, wb=[1.02, 1.0, 0.98])),
    # 8  couple: face-to-face on "so-" (14.71), dip on "aaye", whip 1.65x
    seg(4, C[7], C[8], 0.0, [(1.60, 1.0), (2.15, None)], grade=dict(wb=[1.03, 1.0, 0.97])),
    # 9  twirl: "roko na" - spin-out at 1.2x, smile back on "na", 3.4x whip
    seg(10, C[8], C[9], 2.70, [(3.78, 1.2), (4.12, None)], pre=INT_DN, grade=dict(wb=[0.97, 1.0, 1.05])),
    # 10 two girls: "toko na" - 2x landing, smile on "ko-na"
    seg(11, C[9], C[10], 2.45, [(2.95, 2.0), (3.70, None)], grade=dict(exposure=-0.06)),
    # 11 chug: revealed on "o mujhko", funnel swing + chug in 0.5x SLOW MOTION over the drum break, whip into the drop
    seg(12, C[10], C[11], 1.25, [(1.95, 1.0), (2.78, 0.5), (3.30, None)], pre=INT_DN,
        zoom=[[C[10], 1.0, 0.444, 0.469], [C[10] + 0.70, 1.0, 0.444, 0.469], [C[10] + 2.36, 1.07, 0.444, 0.469], [C[11], 1.07, 0.444, 0.469]]),
    # 12 THE DROP - "ghul mil ghul mil launda": group finale
    seg(13, C[11], C[12], 9.0, [(9.0 + C[12] - C[11], 1.0)],
        zoom=[[C[11], 1.08, 0.5, 0.599], [21.19, 1.08, 0.5, 0.599], [23.19, 1.0, 0.5, 0.599],
              [24.69, 1.0, 0.5, 0.62], [DUR, 1.035, 0.5, 0.62]],
        grade=dict(wb=[0.98, 1.0, 1.02])),
]

fx = []
def bridge(frames, dxs, blurs, bright=None):
    for k, f in enumerate(frames):
        e = dict(f=f, dx=dxs[k] if dxs else 0, blur=blurs[k])
        if bright:
            e["bright"] = bright[k]
        fx.append(e)

# 1 -> 3 : synthetic whip (clip 1 has no pan, clip 3 starts static)
bridge([68, 69, 70, 71, 72], [-8, -30, -75, -150, -260], [10, 30, 65, 110, 160])
bridge([73, 74, 75, 76, 77], [260, 150, 75, 30, 8], [160, 110, 65, 30, 8])
fx.append(dict(f=72, mix="next", a=0.3)); fx.append(dict(f=73, mix="prev", a=0.2))
# 3 -> 5 : both in real blur; bridge
bridge([137, 138], None, [40, 70]); bridge([139, 140, 141], [120, 50, 15], [110, 50, 15])
# 5 -> 6 : whip-in on clip 6
bridge([194, 195], [60, 15], [80, 30])
# 6 -> 7 : blur bridge
bridge([250, 251, 252], None, [30, 60, 90]); bridge([253, 254], [40, 10], [60, 25])
# 7 -> 8 : blur bridge
bridge([289, 290, 291, 292], None, [25, 50, 40, 20])
# 8 -> 9 : whip-in, warm night -> daylight cross-mix
bridge([351, 352, 353, 354], [200, 100, 40, 10], [150, 80, 35, 10])
fx.append(dict(f=350, mix="next", a=0.3)); fx.append(dict(f=351, mix="prev", a=0.3))
# 9 -> 4 : whip-in on clip 4, daylight -> warm cross-mix
bridge([420, 421, 422], [120, 50, 12], [100, 50, 15])
fx.append(dict(f=419, mix="next", a=0.3)); fx.append(dict(f=420, mix="prev", a=0.3))
# 4 -> 10 : pre-blur + whip-in
bridge([474, 475, 476, 477], None, [30, 50, 70, 90]); bridge([478, 479, 480], [120, 50, 12], [100, 50, 15])
# 11 -> 12 : blur bridge
bridge([536, 537, 538, 539], None, [30, 55, 45, 20])
# 12 -> 13 : THE DROP - whip-in + small lift
bridge([621, 622, 623, 624], [220, 100, 35, 8], [140, 70, 28, 8], bright=[0.04, 0.04, 0.02, 0.0])

edl = dict(
    fps=FPS, duration=DUR,
    audio=dict(file=os.path.join(HERE, "song_segment.wav"), start=0.0, fade_in=0.015, fade_out=0.06),
    grade=dict(contrast=0.10, pivot=0.45, lift=0.012, saturation=1.06, knee=0.82,
               high_tint=[0.010, 0.003, -0.008], shadow_tint=[-0.004, 0.0, 0.006],
               vignette=0.10, grain=0.004, sharpen=0.22),
    segments=segments, frame_fx=fx,
)
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "edl.json")
json.dump(edl, open(out, "w"), indent=1)
prev = 0.0
for s in segments:
    assert abs(s["tl_in"] - prev) < 1e-9, s
    prev = s["tl_out"]
    print(f"clip {s['clip']:2d}  tl {s['tl_in']:6.3f}-{s['tl_out']:6.3f}  src {s['map'][0][1]:6.3f}-{s['map'][-1][1]:6.3f}  "
          + " ".join(f"[{a:.3f}->{b:.3f}]" for a, b in s["map"]))
assert abs(prev - DUR) < 1e-9
print("ok", out)

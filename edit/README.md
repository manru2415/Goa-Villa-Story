# Goa Villa Reel: edit notes

**Deliverables (repo root)**
- `Goa_Villa_Reel.mp4`: final reel, 1080×1920, 30 fps, 28.0 s, H.264 High + AAC 320k. It carries the "Slow Motion Angreza" segment taken from `Reference Story.MOV`, and all clip audio is muted.
- `Goa_Villa_Reel_no_music.mp4`: the same cut with no audio. Use this if you prefer to add the song from Instagram's music library (song credit, no mute risk). Start the song at **"Tujhko meri zaroorat"**: the door opens on "tujh-", 0.69 s in.
- `Goa_Villa_Reel_cover.jpg`: suggested cover, the group fists-up at 24.2 s.

## Sequence: one clip per lyric line

Clip 2 is dropped. The order is 1, 3, 5, 6, 7, 8, 9, 4, 10, 11, 12, 13. Lyric timings were measured on the isolated vocal track of the song segment.

| # | Clip | Lyric | Reel time | Sync point |
|---|------|-------|-----------|------------|
| 1 | 1 | tujhko meri zaroorat | 0.00–2.43 | Doors open, her face appears on "tujh-" (0.69) |
| 2 | 3 | aa main tujhko utha loon | 2.43–4.63 | They meet on "aa"; the **lift completes on "utha"** (3.60) |
| 3 | 5 | dheere dheere se chalna | 4.63–6.47 | Walks down the stairs; arms out on "chal-"; laughs on "-na" |
| 4 | 6 | apni adaa… | 6.47–8.43 | Plops on the sofa; pose in **0.5× slow motion** with a slow push-in |
| 5 | 7 | o meri whiskey aaye | 8.43–9.70 | **Glasses clink on "whis-"** (8.82) |
| 6 | 8 | o meri tharra aaye | 9.70–11.70 | Sofa-drop gag lands on "thar-" (10.72) |
| 7 | 9 | o mannu chadh gaye | 11.70–14.00 | Bottle-on-head stare on "chadh gaye" |
| 8 | 4 | meri soniye aaye | 14.00–15.93 | Face to face on "so-" (14.71); the dip on "aaye" |
| 9 | 10 | roko na | 15.93–16.93 | Spin-out at 1.2× |
| 10 | 11 | toko na | 16.93–17.93 | Both girls smile into the lens on "toko na" |
| 11 | 12 | o mujhko peene de raj ke | 17.93–20.70 | **Chug in 0.5× slow motion over the drum break** |
| 12 | 13 | ghul mil ghul mil launda → hook | 20.70–28.00 | Whip in **on the drop**; the group bursts into frame |

## Craft notes
- **Transitions:** every cut hides inside a rightward whip pan, either the camera's own or a synthetic one (directional blur plus a push) where a clip had no pan. Day and night joins get a short 2-frame cross-mix inside the blur.
- **Speed:** moments play at natural speed, except the twirl, which runs at a subtle 1.2× to fit "roko na". The 1.5×–2× speed-ups only happen inside pans. Optical-flow slow motion is used on the sofa pose and the chug.
- **Colour:** the iPhone HLG HDR footage is tone-mapped to SDR at 16-bit precision. Each clip gets its own exposure and white-balance match, under one warm look with a gentle S-curve, highlight roll-off and a light vignette. The night clips are denoised.
- **Ending:** the reel ends at 28.0 s on the beat grid, so Instagram's loop keeps the rhythm.

## Re-render
`bash edit/render.sh` needs ffmpeg (with zscale), python3, numpy and opencv-python-headless.

To change a cut, edit `make_edl.py`. Each segment is a clip, its timeline in/out, its source in-point, and its speed pieces. `frame_fx` holds the whip bridges.

"""Render the bespoke hero film for Good News Coffee Shop.

Procedural, perfectly looping 1080p footage: morning light through a window,
rising steam, drifting bokeh. Every animated term uses an integer number of
cycles per loop, so frame N wraps onto frame 0 with no seam and no crossfade.
"""

import argparse
import math
import os
import sys

import numpy as np
from PIL import Image

TAU = 2.0 * math.pi

# Brand palette, linear-ish RGB.
DEEP_ROAST = np.array([0.013, 0.026, 0.031])
MID_ROAST = np.array([0.120, 0.090, 0.062])
CREMA = np.array([1.000, 0.615, 0.245])
CREAM = np.array([0.990, 0.945, 0.870])
EUCALYPT = np.array([0.300, 0.450, 0.400])


def octaves(rng, count, base_freq, drift):
    """Build octave descriptors whose temporal term is an exact integer cycle."""
    bands = []
    amplitude = 1.0
    freq = base_freq
    for _ in range(count):
        fx = freq * rng.uniform(0.6, 1.4)
        fy = freq * rng.uniform(0.7, 1.3)
        cycles = -int(round(fy * drift)) or -1
        cycles += int(rng.integers(-1, 2))
        bands.append((fx, fy, cycles, rng.uniform(0.0, 1.0), amplitude))
        amplitude *= 0.52
        freq *= 2.03
    return bands


def field(bands, u, v, t):
    """Sum of periodic waves: loops exactly because cycles are integers."""
    total = np.zeros_like(u)
    norm = 0.0
    for fx, fy, cycles, phase, amp in bands:
        total += amp * np.sin(TAU * (fx * u + fy * v + cycles * t + phase))
        norm += amp
    return total / norm


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class HeroFilm:
    def __init__(self, width, height, frames, seed=20180401):
        self.width = width
        self.height = height
        self.frames = frames
        rng = np.random.default_rng(seed)
        self.rng = rng

        aspect = width / height
        # Low-frequency fields render at half size, then get resampled up.
        self.fw = width // 2
        self.fh = height // 2
        u = np.linspace(0.0, aspect, self.fw, dtype=np.float32)
        v = np.linspace(0.0, 1.0, self.fh, dtype=np.float32)
        self.u, self.v = np.meshgrid(u, v)

        self.warp_x = octaves(rng, 3, 1.1, 0.22)
        self.warp_y = octaves(rng, 3, 1.3, 0.26)
        self.steam = octaves(rng, 5, 2.4, 0.55)
        self.haze = octaves(rng, 3, 0.9, 0.18)
        self.beam_flicker = octaves(rng, 2, 0.7, 0.12)

        # Bokeh motes on closed Lissajous paths.
        self.motes = []
        for _ in range(18):
            self.motes.append(
                dict(
                    cx=rng.uniform(-0.1, aspect + 0.1),
                    cy=rng.uniform(-0.05, 1.05),
                    ax=rng.uniform(0.01, 0.07),
                    ay=rng.uniform(0.03, 0.14),
                    mx=int(rng.integers(1, 3)),
                    my=int(rng.integers(1, 3)),
                    px=rng.uniform(0.0, 1.0),
                    py=rng.uniform(0.0, 1.0),
                    radius=rng.uniform(0.008, 0.032),
                    gain=rng.uniform(0.10, 0.55),
                    warm=rng.uniform(0.0, 1.0),
                )
            )

        self.rise_center = aspect * 0.60

        fu = np.linspace(0.0, aspect, width, dtype=np.float32)
        fv = np.linspace(0.0, 1.0, height, dtype=np.float32)
        fu, fv = np.meshgrid(fu, fv)
        cx, cy = aspect * 0.5, 0.5
        radial = np.sqrt(((fu - cx) / (aspect * 0.62)) ** 2 + ((fv - cy) / 0.68) ** 2)
        self.vignette = np.clip(1.0 - 0.86 * radial ** 1.9, 0.04, 1.0).astype(np.float32)
        self.counter = smoothstep(0.86, 1.0, fv).astype(np.float32)
        self.aspect = aspect

    def geometry(self, u, v):
        """Window glow, mullion god-rays and the rising-plume mask."""
        glow = np.exp(-(((u - self.aspect * 0.26) ** 2) / 0.42 + ((v - 0.10) ** 2) / 0.22))
        axis = (u - self.aspect * 0.34) * 0.84 - (v - 0.02) * 0.54
        envelope = np.exp(-(axis ** 2) / 0.085)
        bars = 0.5 + 0.5 * np.cos(TAU * axis * 3.1)
        bars = bars ** 2.6
        beam = envelope * (0.30 + 0.70 * bars) * smoothstep(1.20, 0.02, v)
        plume = np.exp(-((u - self.rise_center) ** 2) / 0.24) * smoothstep(1.04, 0.34, v) * smoothstep(-0.02, 0.46, v)
        return glow, beam, plume

    def mote_layer(self, t, u, v):
        layer = np.zeros((self.fh, self.fw), dtype=np.float32)
        warmth = np.zeros_like(layer)
        for m in self.motes:
            x = m["cx"] + m["ax"] * math.sin(TAU * (m["mx"] * t + m["px"]))
            y = m["cy"] + m["ay"] * math.sin(TAU * (m["my"] * t + m["py"])) - 0.16 * 0.0
            d2 = ((u - x) ** 2 + (v - y) ** 2) / (m["radius"] ** 2)
            blob = np.exp(-(d2 ** 1.6)) * m["gain"]
            layer += blob
            warmth += blob * m["warm"]
        return layer, warmth

    def frame(self, index):
        t = index / self.frames
        # Breathing push-in: one full cycle per loop, so it never cuts.
        zoom = 1.0 + 0.045 * (1.0 - math.cos(TAU * t)) * 0.5
        cx, cy = self.aspect * 0.46, 0.46
        u = cx + (self.u - cx) / zoom
        v = cy + (self.v - cy) / zoom

        glow, beam, plume = self.geometry(u, v)

        wx = field(self.warp_x, u, v, t) * 0.16
        wy = field(self.warp_y, u, v, t) * 0.12
        su, sv = u + wx, v + wy

        # Ridged noise reads as filaments of steam rather than soft fog.
        steam = 1.0 - np.abs(field(self.steam, su, sv, t))
        steam = np.clip(steam, 0.0, 1.0) ** 3.4
        steam *= plume

        haze = np.clip(field(self.haze, su, sv, t) * 0.5 + 0.5, 0.0, 1.0)
        flicker = 0.80 + 0.20 * (field(self.beam_flicker, u, v, t) * 0.5 + 0.5)
        beam = beam * flicker * (0.55 + 0.45 * haze)

        motes, warmth = self.mote_layer(t, u, v)

        lit = glow * (0.45 + 0.55 * haze)
        base = (
            DEEP_ROAST[None, None, :]
            + (MID_ROAST - DEEP_ROAST)[None, None, :] * (0.18 + 0.82 * lit)[..., None]
        )
        img = base + CREMA[None, None, :] * (lit * 0.90)[..., None]
        img += CREMA[None, None, :] * (beam * 0.86)[..., None]
        img += CREAM[None, None, :] * (steam * 0.50 * (0.22 + 0.78 * beam + 0.55 * lit))[..., None]
        img += EUCALYPT[None, None, :] * (steam * haze * 0.10)[..., None]
        img += CREAM[None, None, :] * (motes * 0.30)[..., None]
        img += CREMA[None, None, :] * (warmth * 0.75)[..., None]

        img = np.clip(img, 0.0, None)
        img = img / (1.0 + img * 0.55)          # filmic shoulder
        img = np.power(img, 1.0 / 2.2)          # to display gamma
        img = np.clip((img - 0.035) * 1.16, 0.0, 1.0)

        img = np.ascontiguousarray((img * 255.0).astype(np.uint8))
        up = Image.fromarray(img).resize((self.width, self.height), Image.LANCZOS)
        out = np.asarray(up).astype(np.float32) / 255.0

        out *= self.vignette[..., None]
        out *= (1.0 - 0.82 * self.counter)[..., None]   # counter edge holds the frame
        grain = self.rng.normal(0.0, 0.010, size=(self.height, self.width, 1)).astype(np.float32)
        out += grain * (0.30 + 0.70 * (1.0 - out.mean(axis=2, keepdims=True)))
        return (np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--frames", type=int, default=192)
    ap.add_argument("--seed", type=int, default=20180401)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    film = HeroFilm(args.width, args.height, args.frames, args.seed)
    for i in range(args.frames):
        Image.fromarray(film.frame(i)).save(
            os.path.join(args.out, f"f{i:04d}.png"), compress_level=1
        )
        if i % 24 == 0:
            print(f"frame {i}/{args.frames}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    sys.exit(main())

"""Turn a one-way camera move into a seamless hero loop.

The tail of the clip is cross-dissolved onto its own head, so the last frame
lands back on the first and the video can loop with no visible cut.
"""

import argparse
import json
import subprocess
import sys


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def frame_count(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    return int(json.loads(out.stdout)["streams"][0]["nb_read_frames"])


def encode(src, graph, dst):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", src,
         "-filter_complex", graph, "-map", "[out]", "-an",
         "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-crf", "20", "-preset", "slow", "-movflags", "+faststart",
         "-g", "48", dst],
        check=True,
    )


def build_boomerang(src, dst):
    """Play forward then backward. The wrap is exact: no dissolve, no ghosting."""
    n = frame_count(src)
    graph = (
        "[0]split[f][r];"
        f"[r]reverse,trim=start_frame=1:end_frame={n - 1},setpts=PTS-STARTPTS[rv];"
        "[f][rv]concat=n=2:v=1[out]"
    )
    encode(src, graph, dst)
    print(f"{dst}: boomerang of {n} frames -> {2 * n - 2} frames")


def build(src, dst, fade):
    duration = probe_duration(src)
    if fade >= duration / 2:
        raise SystemExit(f"fade {fade}s too long for a {duration:.2f}s clip")
    body = duration - fade
    offset = body - fade

    graph = (
        "[0]split[body][pre];"
        f"[pre]trim=duration={fade},format=yuva420p,"
        f"fade=t=in:st=0:d={fade}:alpha=1,setpts=PTS+{offset}/TB[head];"
        f"[body]trim=start={fade},setpts=PTS-STARTPTS[bd];"
        "[bd][head]overlay=format=auto,format=yuv420p[out]"
    )

    encode(src, graph, dst)
    print(f"{dst}: {body:.3f}s loop from a {duration:.3f}s source")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--fade", type=float, default=1.2)
    ap.add_argument("--mode", choices=("crossfade", "boomerang"), default="crossfade")
    args = ap.parse_args()
    if args.mode == "boomerang":
        build_boomerang(args.src, args.dst)
    else:
        build(args.src, args.dst, args.fade)


if __name__ == "__main__":
    sys.exit(main())

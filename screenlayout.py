#!/usr/bin/python3

import argparse
import sys
import subprocess

from dataclasses import dataclass
from enum import Enum

from Xlib import display as xdisplay
from Xlib.ext import randr


class Orientation(Enum):
    LANDSCAPE = "normal"
    PORTRAIT = "left"


@dataclass
class Screen:
    name: str
    xres: int
    yres: int
    connected: bool

    def size(self, orientation: Orientation) -> (int, int):
        if orientation == Orientation.LANDSCAPE:
            return self.xres, self.yres
        else:
            return self.yres, self.xres


@dataclass
class Layout:
    center: Screen
    left: (Screen, Orientation) = None
    right: (Screen, Orientation) = None
    top: list(Screen) = None
    off: list(Screen) = None


@dataclass
class Position:
    x: int
    y: int


def get_screens() -> list[Screen]:
    d = xdisplay.Display()
    root = d.screen().root
    res = randr.get_screen_resources(root)
    mode_map = {m['id']: (m['width'], m['height']) for m in res.modes}
    screens = []
    for output in res.outputs:
        info = randr.get_output_info(root, output, res.config_timestamp)
        connected = info.connection == 0
        if connected and info.crtc:
            crtc = randr.get_crtc_info(root, info.crtc, res.config_timestamp)
            screens.append(Screen(name=info.name,
                                  xres=crtc.width,
                                  yres=crtc.height,
                                  connected=True))
        elif connected and info.modes:
            w, h = mode_map[info.modes[0]]
            screens.append(Screen(name=info.name,
                                  xres=w,
                                  yres=h,
                                  connected=True))
        else:
            screens.append(Screen(name=info.name,
                                  xres=0,
                                  yres=0,
                                  connected=connected))
    return {s.name: s for s in screens}


def left_of(center: Screen,
            other: Screen,
            orientation: Orientation) -> (Screen, Position, Orientation):
    if not other.connected:
        return (other, Position(x=0, y=0), orientation)
    else:
        w, h = other.size(orientation)
        xoff = -w
        yoff = center.yres-h
        return (other, Position(x=xoff, y=yoff), orientation)


def right_of(center: Screen,
             other: Screen,
             orientation: Orientation) -> (Screen, Position, Orientation):
    if not other.connected:
        return (other, Position(x=0, y=0), orientation)
    else:
        w, h = other.size(orientation)
        xoff = center.xres
        yoff = center.yres-h
        return (other, Position(x=xoff, y=yoff), orientation)


def total_width(screens: list[Screen]) -> int:
    total = 0
    for s in screens:
        if s.connected:
            w, _ = s.size(Orientation.LANDSCAPE)
            total += w
    return total


def above(center: Screen,
          others: list[Screen]) -> list[(Screen, Position, Orientation)]:
    total = total_width(others)
    positions = []
    left_edge = -(total - center.xres) / 2
    print(f"left: {left_edge}")
    for s in others:
        if not s.connected:
            positions.append((s, Position(x=0, y=0), Orientation.LANDSCAPE))
        else:
            w, h = s.size(Orientation.LANDSCAPE)
            positions.append((s,
                              Position(x=int(left_edge), y=-h),
                              Orientation.LANDSCAPE))
            left_edge += w
    return positions


def xrandr_screen_opts(s: Screen, p: Position, o: Orientation) -> list[str]:
    if not s.connected:
        return ["--output", s.name, "--off"]
    else:
        return ["--output", s.name,
                "--mode", f"{s.xres}x{s.yres}",
                "--rotate", o.value,
                "--pos", f"{p.x}x{p.y}"]


def xrandr_command(layout: Layout) -> list[str]:
    cmd = [["--output", layout.center.name,
            "--mode", f"{layout.center.xres}x{layout.center.yres}",
            "--rotate", "normal",
            "--pos", "0x0"]]

    if layout.left:
        s, p, o = left_of(layout.center, *layout.left)
        oc = xrandr_screen_opts(s, p, o)
        cmd.append(oc)

    if layout.right:
        s, p, o = right_of(layout.center, *layout.right)
        oc = xrandr_screen_opts(s, p, o)
        cmd.append(oc)

    if layout.top:
        for s, p, o in above(layout.center, layout.top):
            oc = xrandr_screen_opts(s, p, o)
            cmd.append(oc)

    if layout.off:
        for s in layout.off:
            cmd.append(["--output", s.name, "--off"])
    return cmd


def build_layouts(screens: dict[str, Screen]) -> dict[str, Layout]:
    left = screens["DP-1-1"]
    right = screens["DP-1-2"]
    center = screens["eDP-1"]

    layouts = {
        "pp": Layout(center=center,
                     left=(left, Orientation.PORTRAIT),
                     right=(right, Orientation.PORTRAIT)),
        "lp": Layout(center=center,
                     left=(left, Orientation.LANDSCAPE),
                     right=(right, Orientation.PORTRAIT)),
        "pl": Layout(center=center,
                     left=(left, Orientation.PORTRAIT),
                     right=(right, Orientation.LANDSCAPE)),
        "ll": Layout(center=center,
                     left=(left, Orientation.LANDSCAPE),
                     right=(right, Orientation.LANDSCAPE)),
        "tt": Layout(center=center,
                     top=[left, right]),
        "off": Layout(center=center,
                      off=[left, right])
    }
    return layouts


if __name__ == "__main__":
    screens = get_screens()
    layouts = build_layouts(screens)

    parser = argparse.ArgumentParser(prog="screen layout",
                                     description="configure connected monitors")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-t", "--dry-run", action="store_true")
    parser.add_argument("layout", choices=sorted(layouts.keys()))
    args = parser.parse_args()

    if args.verbose:
        for k, s in screens.items():
            print(s)

    layout = layouts[args.layout]
    opts = xrandr_command(layout)
    if args.verbose:
        for c in opts:
            print("xrandr", *c)

    cmd = ["xrandr"]
    for o in opts:
        cmd.extend(o)

    if args.dry_run:
        sys.exit(0)
    else:
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(r.stdout)

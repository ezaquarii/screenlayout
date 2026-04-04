#!/usr/bin/python3

import argparse
import json
import sys
import subprocess

from dataclasses import dataclass
from enum import Enum

from Xlib import display as xdisplay, X
from Xlib.ext import randr


class Orientation(Enum):
    LANDSCAPE = "normal"
    PORTRAIT = "left"


@dataclass
class Screen:
    name: str
    xres: int = 0
    yres: int = 0
    connected: bool = False
    serial: str = None

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


class Edid:
    def __init__(self, blob=None):
        self.serial = None
        self.name = None
        if not blob:
            return
        for i in range(54, 126, 18):
            block = blob[i:i+18]
            if len(block) < 18:
                continue
            elif block[:4] == b'\x00\x00\x00\xff':
                self.serial = block[5:18].decode(errors="ignore").strip()
            elif block[:4] == b'\x00\x00\x00\xfc':
                self.name = block[5:18].decode(errors="ignore").strip()


class Display:
    def __init__(self, display: xdisplay.Display):
        self._display = display
        self._root = display.screen().root

    def get_output_props(self, output: int) -> dict[str, int]:
        prop_atoms = randr.list_output_properties(self._root,
                                                  output).atoms
        return {
            self._display.get_atom_name(pa): pa for pa in prop_atoms
        }

    def get_output_edid(self, output: int) -> Edid:
        edid_atom = self.get_output_props(output).get("EDID", None)
        if not edid_atom:
            return Edid()
        blob = randr.get_output_property(self._root,
                                         output,
                                         edid_atom,
                                         X.AnyPropertyType,
                                         0,
                                         128,
                                         False,
                                         False).value
        return Edid(bytes(blob))

    @property
    def screens(self):
        res = randr.get_screen_resources(self._root)
        modes = {m['id']: (m['width'], m['height']) for m in res.modes}
        screens = []
        for output in res.outputs:
            info = randr.get_output_info(self._root,
                                         output,
                                         res.config_timestamp)
            connected = info.connection == 0
            xres = 0
            yres = 0
            edid = self.get_output_edid(output)
            if connected and info.crtc:
                crtc = randr.get_crtc_info(self._root,
                                           info.crtc,
                                           res.config_timestamp)
                xres = crtc.width
                yres = crtc.height
                screens.append(Screen(name=info.name,
                                      xres=crtc.width,
                                      yres=crtc.height,
                                      connected=True,
                                      serial=edid.serial))
            elif connected and info.modes:
                xres, yres = modes[info.modes[0]]
                screens.append(Screen(name=info.name,
                                      xres=xres,
                                      yres=yres,
                                      connected=True,
                                      serial=edid.serial))
            else:
                screens.append(Screen(name=info.name,
                                      connected=connected,
                                      serial=edid.serial))
        return screens


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


def load_json(filename) -> dict:
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception:
        return None


def build_layouts(screens: list[Screen],
                  left_serial=None,
                  right_serial=None) -> dict[str, Layout]:
    by_name = {s.name: s for s in screens}
    by_serial = {s.serial: s for s in screens if s.serial is not None}

    if left_serial in by_serial and right_serial in by_serial:
        left = by_serial[left_serial]
        right = by_serial[right_serial]
    else:
        left = by_name["DP-1-1"]
        right = by_name["DP-1-2"]
    center = by_name["eDP-1"]

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


def show_main():
    d = Display(xdisplay.Display())
    screens = d.screens
    for s in screens:
        print(s)


def configure_main(layout_name,
                   left_serial=None,
                   right_serial=None,
                   verbose=False,
                   dry_run=False):
    d = Display(xdisplay.Display())
    layouts = build_layouts(screens=d.screens,
                            left_serial=left_serial,
                            right_serial=right_serial)
    layout = layouts[layout_name]
    opts = xrandr_command(layout)
    if verbose:
        print(f"left: {left_serial or 'none'}")
        print(f"right: {right_serial or 'none'}")
        for c in opts:
            print("xrandr", *c)

    cmd = ["xrandr"]
    for o in opts:
        cmd.extend(o)

    if dry_run:
        sys.exit(0)
    else:
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(r.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="screen layout",
                                     description="configure connected monitors")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest='command', required=True)
    sp = subparsers.add_parser("show",
                               help="Show detected monitors")

    cp = subparsers.add_parser("configure",
                               help="Configure screens")
    cp.add_argument("layout",
                    help="monitor layout",
                    choices=("pp", "lp", "pl", "ll", "tt", "off"))
    cp.add_argument("-t", "--dry-run", action="store_true",
                    help="print xrandr commands, but do not run them")
    cp.add_argument("-l", "--left-serial", type=str, default=None,
                    help="Serial number of left monitor (from EDID)")
    cp.add_argument("-r", "--right-serial", type=str, default=None,
                    help="Serial number of right monitor (from EDID)")

    args = parser.parse_args()

    if args.command == "show":
        show_main()
    elif args.command == "configure":
        configure_main(layout_name=args.layout,
                       left_serial=args.left_serial,
                       right_serial=args.right_serial,
                       verbose=args.verbose,
                       dry_run=args.dry_run)

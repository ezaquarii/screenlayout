# screenlayout

A small script that uses `xrandr` to arrange external monitors into
preconfigured layouts.

Uses `Xlib.randr` to detect `DP` and `HDMI` outputs and calculate
`xrandr --pos` parameters.  Monitor positions are fixed by connector
name — e.g. left is `DP-1-1`, right is `DP-1-2` — but can be
overridden by EDID serial number.

# Why?

[i3](https://i3wm.org/) — that's why.

# Examples

Show detected monitors and their connector names:

```bash
./screenlayout.py show
```

Apply a layout (both externals in portrait mode):

```bash
./screenlayout.py configure pp
```

Preview `xrandr` commands without executing them:

```bash
./screenlayout.py -v configure --dry-run pp
```

Disable external screens:

```bash
./screenlayout.py configure off
```

Select monitors by EDID serial number (useful when connector names
vary between reboots):

```bash
./screenlayout.py configure --left-serial ABC123 --right-serial DEF456 pp
```

# Supported layouts

```
off — laptop only, external screens disabled

    +------------+
    |            |
    |   laptop   |
    +------------+
```

```
pp — portrait | laptop | portrait

+-------+                  +-------+
|       |                  |       |
|       |                  |       |
|  left |                  | right |
|       |  +------------+  |       |
|       |  |            |  |       |
|       |  |   laptop   |  |       |
+-------+  +------------+  +-------+
```

```
ll — landscape | laptop | landscape

+----------------+                  +----------------+
|                |  +------------+  |                |
|                |  |            |  |                |
|      left      |  |   laptop   |  |     right      |
+----------------+  +------------+  +----------------+
```

```
pl — portrait left | laptop | landscape right

+-------+
|       |
|       |
|  left |                  +----------------+
|       |  +------------+  |                |
|       |  |            |  |                |
|       |  |   laptop   |  |     right      |
+-------+  +------------+  +----------------+
```

```
lp — landscape left | laptop | portrait right

                                    +-------+
                                    |       |
                                    | right |
+----------------+                  |       |
|                |  +------------+  |       |
|                |  |            |  |       |
|     left       |  |   laptop   |  |       |
+----------------+  +------------+  +-------+
```

```
tt — both externals above laptop, centered

+----------------+  +----------------+
|                |  |                |
|      left      |  |     right      |
|                |  |                |
+----------------+  +----------------+
            +------------+
            |            |
            |   laptop   |
            +------------+
```

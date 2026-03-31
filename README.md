# screenlayout

This small script uses `xrandr` to arrange external screens to some
preconfigured layouts.

uses `Xlib.randr` to detect `DP` and `HDMI` outputs and calculate
`xrandr --pos` parameters.

Monitor positions are fixed - ex. left is `DP-1-1`, right is `DP-1-2`,
etc.  There is no magic autodetection by ID.

# Why?

[i3](https://i3wm.org/) - that's why.

# How?

Create a keybinding that execs `screenlayout.py pp` to configure both
screens in portrait mode.

Run `screenlayout.py off` to disable them.

Run ``screenlayout.py -v --dry-run pp` to see `xrandr` command without
running any action.

Run `screenlayout.py --help` for halp.

# Supported layouts

```
off - disables externals screens

     +-----+
     | LAP |
 x   |     |  x
     +-----+ 
```

```
pp - portrait / portrait
+----+           +----+
|    |           |    |
|    |  +-----+  |    |
|    |  | LAP |  |    |
|    |  |     |  |    |
+----+  +-----+  +----+
```

```
ll - landscape / landscape
+-------+  +-----+  +-------+
|       |  | LAP |  |       |
|       |  |     |  |       |
+-------+  +-----+  +-------+
```


```
pl - portrait / landscape
+----+ 
|    | 
|    | +-----+  +-------+ 
|    | | LAP |  |       | 
|    | |     |  |       |
+----+ +-----+  +-------+
```

```
lp - landscape / portrait
                   +----+
                   |    |
 +-------+ +-----+ |    | 
 |       | | LAP | |    | 
 |       | |     | |    |
 +-------+ +-----+ +----+
```

```
tt - top / top
+-------++-------+
|       ||       |
|       ||       |
+-------++-------+
     +------+
	 | LAP  |
	 |      |
	 +------+
```

# The port against the original, frame for frame

Measured 2026-10-23 at commit 12ba62e.

The same world-loop frames are run two ways from the same saved game:
the original ACD.EXE's code under the harness's emulator (unicorn), and
the port's engine in the view's headless bench. Both load slot 1 into
the place it was saved in (a Mages Guild, mage7.mif) and run 240 frames
walking forward, turning right one block of 30 frames in four
(view/src/bench.rs). Both end on the same spot: (761h, 23Eh), heading
A9h. So they ran the same frames, not just the same number of them.

## Results

| | per frame | frames a second | against the emulated original |
|---|---|---|---|
| Original under unicorn, the full harness | 145.4 ms | 6.9 | |
| Original under unicorn, lean (no hooks beyond what the frames need) | 122.9 ms | 8.1 | 1× |
| Original under unicorn, unicorn's own time only (cProfile; estimate) | ~110 ms | ~9 | |
| Port: the engine's frame (`engine.frame`, the ported 3D drawing included) | 2.38 ms | ~420 | **~50×** |
| Port: a whole turn (the frame, the redraw, the GPU draw waited for) | 2.73–3.03 ms | ~350 | **~43×** |

The start-up (from the program to the loaded game's world loop) takes
0.25 s in the port and 0.35 s in the lean emulator.

## What is counted

- **The emulator.** The full harness is gen_worldframes.py's arena: a
  Sound Blaster model (`sbdig.SoundArena`, a hook on the timer word and
  on each call into the sound driver), the drawn rows watched
  (`rows_watch`) and the cursor's hook. The lean run drops all of these
  (`screens.ScreenArena`, no sound card). It keeps what the frames can't
  run without: the interrupts (DOS, EMS, BIOS), the ports, and one-address
  hooks at the timer's waits and the frame's top. Under cProfile about
  80% of the lean run is spent inside unicorn's `emu_start`. Most of the
  rest is the interrupts answered in Python, about half of that EMS
  calls (some 35 a frame). The bare emulator is therefore about 110 ms a
  frame: roughly 266,000 basic blocks.
- **The port.** `arena-view ... --load --slot 1 --mute --original
  --bench 240`, with `ARENA_PROFILE=1` for the breakdown. A turn is the
  engine's step (its copy for the replay included, 0.26 ms), the frame
  (2.38 ms), the CPU's part of the redraw (0.34 ms) and the GPU's draw to
  an offscreen 640×400 target, waited for (0.51 ms).
- **The 3D view.** It is drawn in both. The port runs the ported
  software renderer as part of the engine's frame, and the emulator runs
  the original's.

## Machine

Intel Core i7-4820K at 3.70 GHz, 30 GB of memory, Linux 7.0. rustc
1.87.0-nightly, a release build. Python 3.14.4, unicorn 2.1.4.

## Reproducing

    cargo build --release -p arena-view
    target/release/arena-view GAME_DIR START.MIF --load --save-dir SAVES --slot 1 --mute --original --bench 240
    LEAN=1 python tools/emu_bench.py harness re/ACD_unpacked.EXE GAME_DIR SAVES 240

(START.MIF is only the level the load replaces. Copy the save to SAVES
first, since `--save-dir` is where the view's own saves go.)

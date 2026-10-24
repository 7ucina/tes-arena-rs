"""Time the original's world loop under unicorn, for docs/benchmark.md:
the saved game loaded (or the guild left, or gen_dungeonscreens.py's
dungeon entered), then N frames walking forward, turning right one block
of 30 in four, as the view's `--bench` (view/src/bench.rs) does.

Usage: emu_bench.py HARNESS_DIR ACD_unpacked.EXE GAME_DIR SAVE_DIR N [loaded|street|dungeon]

LEAN=1: no sound card (screens.py's ScreenArena, not sbdig's SoundArena)
and none of gen_worldframes.py's watches, leaving only the hooks the
frames need (the interrupts, the ports, the timer's waits, the frame's
top). COUNT=1: the basic blocks run counted too (a block hook: slow).
Run it with the harness venv's python."""
import os, sys, time
H = sys.argv[1]
sys.path.insert(0, H)
import gen_worldframes as gw
from sbdig import SoundArena
from unicorn import UC_HOOK_CODE

EXE, GAME, SAVE, N = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
place = sys.argv[6] if len(sys.argv) > 6 else 'loaded'
t = time.perf_counter()
LEAN = os.environ.get('LEAN')
if LEAN:
    from screens import ScreenArena
    a = ScreenArena(EXE, GAME, SAVE)
else:
    a = SoundArena(EXE, GAME, SAVE)
    gw.rows_watch(a)
a.start()
base = a.snapshot()
print(f'start-up (load to world loop): {time.perf_counter()-t:.2f} s', flush=True)
at = {'loaded': lambda: base, 'street': lambda: gw.street(a, base), 'dungeon': lambda: gw.gd.dungeon(a, base)}[place]()
a.restore(at)
for k in ('rows_drawn',):
    setattr(a, k, [])
a.waits, a.script, a.clicks, a.mouse, a.buttons = set(), [], [], (160, 100), 0
a.menu_loaded, a.checkpoints, a.levelling, a.letting_go, a.letting_go4 = False, {}, None, False, False
cursor = None if LEAN else a.mu.hook_add(UC_HOOK_CODE, lambda *_: a.w16(0x7A48, 0xFFFF), None, a.lin(gw.LOAD_SEG, gw.CURSOR_DRAW), a.lin(gw.LOAD_SEG, gw.CURSOR_DRAW))
# Instruction count: one block hook adding block sizes is too slow to leave
# on, so time first, count separately with COUNT=1.
icount = [0]
if os.environ.get('COUNT'):
    from unicorn import UC_HOOK_BLOCK
    def blk(mu, addr, size, _):
        icount[0] += 1
    a.mu.hook_add(UC_HOOK_BLOCK, blk)
RIGHT = 0x4D
a.keys_held((gw.UP,))
done, t0, why = 0, time.perf_counter(), None
per = []
while done < N:
    turn = (done // 30) % 4 == 3
    n = min(30 - done % 30, N - done)
    a.keys_held((RIGHT,), down=turn)
    s = time.perf_counter()
    why, ran = a.world_frames(n)
    per.append((n, time.perf_counter() - s))
    if why != ('frames',):
        print('stopped:', why, 'after', done + ran); break
    done += n
total = time.perf_counter() - t0
print("end at", hex(a.r16(0xC3D0)), hex(a.r16(0xC3D4)), "heading", hex(a.r16(0xC3DA)))
print(f'{done} frames in {total:.2f} s ({total*1e3/max(done,1):.1f} ms a frame, {done/total:.1f} fps)')
if icount[0]:
    print(f'basic blocks executed: {icount[0]} ({icount[0]/done:.0f} a frame)')

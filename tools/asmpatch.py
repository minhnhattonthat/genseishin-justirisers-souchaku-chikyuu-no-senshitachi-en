"""asmpatch.py: code patches for the English text (hand-assembled Thumb, each checked against the original bytes).

Patches (docs/re/text.md §English font):
- **Glyph column copy** (0x08008384, called after every glyph with the x before and after it): the original skips
  the copy when the advance is <= 7 px and copies ceil(advance / 8) tiles from the tile holding the old x, so with
  glyphs narrower than 12 px a tile column is sometimes never copied to VRAM (the right half of a glyph missing).
  The hook aligns the old x down to its tile first: copy every tile from floor(x_old / 8) to ceil(x_new / 8), and
  skip only when nothing advanced.

Hook code lives at HOOKS, the start of the original script block (free once tools/insert.py relocates the block).
"""
import struct

HOOKS = 0x1E90C0   # old script block start (4-aligned); the relocated build no longer reads anything here


def thumb_bl(src, dst):
    """BL from ROM offset src to ROM offset dst (both Thumb, within +-4 MiB) -> 4 bytes."""
    off = dst - (src + 4)
    assert -0x400000 <= off < 0x400000 and off % 2 == 0, (hex(src), hex(dst))
    return struct.pack("<HH", 0xF000 | (off >> 12) & 0x7FF, 0xF800 | (off >> 1) & 0x7FF)


def h(*halfwords):
    return struct.pack(f"<{len(halfwords)}H", *halfwords)


COPY_HOOK = HOOKS
PATCHES = [
    # hook: r7 = x_old, ip = x_new -> r7 = x_old & ~7, r0 = x_new - r7 (flags from subs)
    (COPY_HOOK, None, h(0x2007,     # movs r0, #7
                        0x4387,     # bics r7, r0
                        0x4660,     # mov  r0, ip
                        0x1BC0,     # subs r0, r0, r7
                        0x4770)),   # bx   lr
    # 0x080083C4: mov r0,ip / subs r0,r0,r7 / mov ip,r0 / cmp r0,#7 / ble  ->  bl hook / mov ip,r0 / cmp r0,#0 / ble
    (0x83C4, bytes.fromhex("6046c01b84460728"), thumb_bl(0x83C4, COPY_HOOK) + h(0x4684, 0x2800)),
]


def apply(rom):
    """-> written ranges. Raises if the original bytes at a patch site are not the expected ones."""
    ranges = []
    for addr, orig, new in PATCHES:
        if orig is not None and bytes(rom[addr:addr + len(orig)]) != orig:
            raise SystemExit(f"asmpatch: bytes at {addr:X} are {bytes(rom[addr:addr + len(orig)]).hex()}, "
                             f"expected {orig.hex()}")
        rom[addr:addr + len(new)] = new
        ranges.append((addr, addr + len(new)))
    return ranges

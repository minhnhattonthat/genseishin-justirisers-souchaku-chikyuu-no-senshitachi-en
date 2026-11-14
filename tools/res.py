"""res.py: the game's resource table and its custom decompressor (recon, phase 1).

    python -X utf8 tools/res.py list ROM [--group G]          one line per resource: group, index, ROM offset, size, lz
    python -X utf8 tools/res.py unpack ROM OUTDIR [--group G]  write each resource (raw, and .lz.bin when it decompresses)

Resource table: ROM 0xD226AC, u32 pointers (0x08xxxxxx) to 23 groups (1..23); each group is an array of u32
self-relative offsets (entry at A -> A + value); its length is the first entry's offset / 4. Loader 0x080202E8
(r0 = id: bits 8-13 group, 0-7 index, upper bits = flags incl. "decompress"). See docs/re/graphics.md.

Decompressor 0x08001CD4 (r0 = dst, r1 = src): a Konami flag-bit LZ. It is run here under unicorn on the ROM's own
code, so it is exact; a resource "is lz" when the run returns within the step limit and consumes within 16 bytes of
the resource's size.
"""
import argparse
import os
import struct

TABLE, GROUPS = 0xD226AC, range(1, 24)
DECOMP = 0x08001CD4
ROM_BASE = 0x08000000


def groups(d):
    out = {}
    for g in GROUPS:
        base = struct.unpack_from("<I", d, TABLE + 4 * g)[0] - ROM_BASE
        n = struct.unpack_from("<I", d, base)[0] // 4
        if n < 0x1000:
            offs = [(base + 4 * i + struct.unpack_from("<I", d, base + 4 * i)[0]) & 0xFFFFFFFF for i in range(n)]
        else:   # group 8: u16 self-relative entries
            n = struct.unpack_from("<H", d, base)[0] // 2
            offs = [base + 2 * i + struct.unpack_from("<H", d, base + 2 * i)[0] for i in range(n)]
        out[g] = (base, offs)
    return out


def resources(d):
    """[(group, index, offset, size)] with size = distance to the next distinct resource start anywhere."""
    gs = groups(d)
    starts = sorted({o for _, offs in gs.values() for o in offs} | {b for b, _ in gs.values()})
    nxt = {s: (starts[i + 1] if i + 1 < len(starts) else len(d)) for i, s in enumerate(starts)}
    return [(g, i, o, nxt[o] - o) for g, (_, offs) in gs.items() for i, o in enumerate(offs)]


class Decomp:
    def __init__(self, d):
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_MEM_READ
        from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC
        self.R0, self.R1, self.LR, self.SP = UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP
        self.PC = UC_ARM_REG_PC
        self.mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.mu.mem_map(ROM_BASE, 0x1000000)
        self.mu.mem_write(ROM_BASE, d)
        self.mu.mem_map(0x02000000, 0x100000)   # EWRAM, oversized so big outputs don't fault
        self.mu.mem_map(0x03000000, 0x10000)
        self.hi = 0
        self.mu.hook_add(UC_HOOK_MEM_READ, self._rd, begin=ROM_BASE, end=ROM_BASE + 0xFFFFFF)

    def _rd(self, mu, access, addr, size, value, user):
        if addr + size > self.hi:
            self.hi = addr + size

    def run(self, off, limit=4_000_000):
        """-> (bytes, consumed) or None when it doesn't return in time or faults."""
        mu, dst = self.mu, 0x02000000
        mu.mem_write(dst, b"\xAA" * 0x100000)
        mu.reg_write(self.R0, dst)
        mu.reg_write(self.R1, ROM_BASE + off)
        mu.reg_write(self.SP, 0x03007F00)
        mu.reg_write(self.LR, 0x03000001)
        self.hi = ROM_BASE + off
        try:
            mu.emu_start(DECOMP | 1, 0x03000000, count=limit)
        except Exception:
            return None
        if mu.reg_read(self.PC) & ~1 != 0x03000000:
            return None
        out = bytes(mu.mem_read(dst, 0x100000))
        n = len(out.rstrip(b"\xAA"))
        return out[:n], self.hi - ROM_BASE - off


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "unpack"])
    ap.add_argument("rom")
    ap.add_argument("outdir", nargs="?")
    ap.add_argument("--group", type=int)
    ap.add_argument("--no-lz", action="store_true", help="skip the decompression test")
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    dc = None if a.no_lz else Decomp(d)
    seen = {}
    for g, i, o, size in resources(d):
        if a.group is not None and g != a.group:
            continue
        if o in seen:
            if a.cmd == "list":
                print(f"{g}\t{i}\t{o:07X}\t{size}\tdup:{seen[o]}")
            continue
        seen[o] = f"{g}.{i}"
        lz = dc.run(o) if dc and size >= 4 else None
        ok = lz is not None and abs(lz[1] - size) <= 16 and len(lz[0]) > size
        if a.cmd == "list":
            print(f"{g}\t{i}\t{o:07X}\t{size}\t" + (f"lz:{len(lz[0])}" if ok else "raw"))
        else:
            os.makedirs(a.outdir, exist_ok=True)
            name = os.path.join(a.outdir, f"g{g:02d}_{i:04d}_{o:07X}")
            with open(name + ".bin", "wb") as f:
                f.write(d[o:o + size])
            if ok:
                with open(name + ".lz.bin", "wb") as f:
                    f.write(lz[0])


if __name__ == "__main__":
    main()

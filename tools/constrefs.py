"""Find Thumb code that loads given constants (literal-pool `ldr rX, =imm` or `movs rX, #imm`).

    python -X utf8 tools/constrefs.py ROM 0x275 648-651 ... [--scenes]

Use it to tie a resource index (e.g. a BG screen sNNNN of docs/re/graphics.md = r1 of the loader) to the code,
and with --scenes to the scene whose handler sits closest below (a guess: helpers sit between handlers).
"""
import argparse
import struct

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs

TABLE = 0xD22CA0


def parse(vals):
    out = set()
    for v in vals:
        if '-' in v:
            a, b = v.split('-')
            out.update(range(int(a, 0), int(b, 0) + 1))
        else:
            out.add(int(v, 0))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rom')
    ap.add_argument('vals', nargs='+')
    ap.add_argument('--end', type=lambda x: int(x, 0), default=0x40000, help='code end (file offset)')
    a = ap.parse_args()
    want = parse(a.vals)
    rom = open(a.rom, 'rb').read()
    handlers = sorted((struct.unpack_from('<I', rom, TABLE + 4 * i)[0] & ~1, i) for i in range(256)
                      if struct.unpack_from('<I', rom, TABLE + 4 * i)[0])
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.skipdata = True
    for ins in md.disasm(rom[:a.end], 0x08000000):
        v = None
        if ins.mnemonic == 'ldr' and '[pc, #' in ins.op_str:
            off = int(ins.op_str.split('#')[1].rstrip(']'), 0)
            lit = ((ins.address + 4) & ~3) + off - 0x08000000
            if lit + 4 <= len(rom):
                v = struct.unpack_from('<I', rom, lit)[0]
        elif ins.mnemonic == 'movs' and ', #' in ins.op_str:
            v = int(ins.op_str.split('#')[1], 0)
        if v in want:
            own = max((h for h in handlers if h[0] <= ins.address), default=(0, -1))[1]
            print('%08X  %-5s %-28s = %d (0x%X)  near scene %d' % (ins.address, ins.mnemonic, ins.op_str, v, v, own))


if __name__ == '__main__':
    main()

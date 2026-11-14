"""List every scene transition in the ROM: BL calls to the scene-machine helpers with a constant target.

    python -X utf8 tools/scenecalls.py ROM [--scene N]

Helpers (docs/re/scenes.md): 0x08026794 goto (scene<<8|sub, returns 0x82), 0x080267A8 call (push, returns 0x83),
0x080267BC call and advance own sub, 0x080267DC call with explicit return point. The target is r0, built just
before the BL by `movs r0,#imm` [+ `lsls r0,#n`] [+ `adds r0,#imm`] or `ldr r0,=imm`; non-constant targets print '?'.
The caller's scene is the dispatcher-table entry (0x08D22CA0) whose handler is the closest one at or below it
(a guess for shared code: helper functions sit between handlers).
"""
import argparse
import struct

from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs

HELPERS = {0x08026794: 'goto', 0x080267A8: 'call', 0x080267BC: 'call+', 0x080267DC: 'call@'}
TABLE = 0xD22CA0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rom')
    ap.add_argument('--scene', type=int)
    a = ap.parse_args()
    rom = open(a.rom, 'rb').read()
    handlers = sorted((struct.unpack_from('<I', rom, TABLE + 4 * i)[0] & ~1, i) for i in range(256)
                      if struct.unpack_from('<I', rom, TABLE + 4 * i)[0])
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.skipdata = True
    code = rom[:0x40000]  # all game code sits below 0x08040000
    insns = list(md.disasm(code, 0x08000000))
    for k, ins in enumerate(insns):
        if ins.mnemonic not in ('bl',):
            continue
        try:
            tgt = int(ins.op_str.lstrip('#'), 16)
        except ValueError:
            continue
        if tgt not in HELPERS:
            continue
        val = None
        for j in range(k - 1, max(k - 8, 0), -1):
            p = insns[j]
            if p.mnemonic in ('movs',) and p.op_str.startswith('r0, #'):
                val = int(p.op_str[5:], 0)
                for q in insns[j + 1:k]:
                    if q.op_str.startswith('r0, r0, #') and q.mnemonic == 'lsls':
                        val <<= int(q.op_str[9:], 0)
                    elif q.op_str.startswith('r0, #') and q.mnemonic == 'adds':
                        val += int(q.op_str[5:], 0)
                break
            if p.mnemonic == 'ldr' and p.op_str.startswith('r0, [pc, #'):
                off = int(p.op_str[10:-1], 0)
                lit = ((p.address + 4) & ~3) + off
                val = struct.unpack_from('<I', rom, lit - 0x08000000)[0]
                break
            if p.op_str.startswith('r0,') and p.mnemonic not in ('lsls', 'adds', 'cmp'):
                break
        own = max((h for h in handlers if h[0] <= ins.address), default=(0, -1))[1]
        sc = None if val is None else (val >> 8) & 0xFF
        if a.scene is not None and sc != a.scene:
            continue
        tv = '?' if val is None else 'scene %d sub %d' % (sc, val & 0xFF)
        print('%08X  from scene %3d  %-6s %s' % (ins.address, own, HELPERS[tgt], tv))


if __name__ == '__main__':
    main()

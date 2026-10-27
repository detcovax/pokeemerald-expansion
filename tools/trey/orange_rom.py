"""TREY (6c, TREY_PLAN.md D39): read the Orange Islands ROM hack (applied to FireRed 1.0, BPRE rev 0).

Shared by tools/trey/import_orange.py. Everything comes from the ROM file; the hack is a plain FireRed hack:
  gMapGroups      0x3526A8 (FireRed 1.0), banks back to back, map headers 0x1C bytes (layout pointer valid)
  location names  0x3F1CAC, one pointer per MAPSEC from 0x58 (KANTO_MAPSEC_START)
  tileset structs 0x2D4A94 + 0x18 * i, in pokefirered's src/data/tilesets/headers.h order
                  {u8 isCompressed, u8 isSecondary, u16 pad, tiles*, palettes*, metatiles*, callback*, attributes*}
"""
import collections
import re
import struct

GMAPGROUPS = 0x3526A8
NAMES = 0x3F1CAC
TILESETS = 0x2D4A94
ROM_BASE = 0x08000000

# Charmap subset (FireRed), enough for location names and sign/NPC text decoding.
CHARS = {0x00: " ", 0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-", 0xB0: "...", 0xB1: "“", 0xB2: "”",
         0xB3: "‘", 0xB4: "'", 0xB5: "♂", 0xB6: "♀", 0xB8: ",", 0xBA: "/", 0x1B: "é"}
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    CHARS[0xBB + _i] = _c
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    CHARS[0xD5 + _i] = _c
for _i, _c in enumerate("0123456789"):
    CHARS[0xA1 + _i] = _c


class Rom:
    def __init__(self, path):
        self.d = open(path, "rb").read()
        if self.d[0xAC:0xB0] != b"BPRE":
            raise SystemExit(f"{path}: not a FireRed ROM (game code {self.d[0xAC:0xB0]!r})")

    def u8(self, o): return self.d[o]
    def u16(self, o): return struct.unpack_from("<H", self.d, o)[0]
    def u32(self, o): return struct.unpack_from("<I", self.d, o)[0]

    def isptr(self, v):
        return ROM_BASE <= v < ROM_BASE + len(self.d) - 0x20

    def off(self, ptr):
        return ptr - ROM_BASE

    def lz77(self, ptr):
        d, o = self.d, self.off(ptr)
        if d[o] != 0x10:
            raise ValueError(f"no LZ77 data at {ptr:#x}")
        size = d[o + 1] | d[o + 2] << 8 | d[o + 3] << 16
        o += 4
        out = bytearray()
        while len(out) < size:
            flags = d[o]; o += 1
            for bit in range(8):
                if len(out) >= size:
                    break
                if flags & (0x80 >> bit):
                    b1, b2 = d[o], d[o + 1]; o += 2
                    n, disp = (b1 >> 4) + 3, ((b1 & 0xF) << 8 | b2) + 1
                    for _ in range(n):
                        out.append(out[-disp])
                else:
                    out.append(d[o]); o += 1
        return bytes(out)

    # ---------------- maps ----------------
    def maps(self):
        """(group, num) -> header pointer, for every group whose bank pointer is valid."""
        banks = []
        for g in range(64):
            b = self.u32(GMAPGROUPS + 4 * g)
            if not self.isptr(b):
                break
            banks.append(b)
        starts = set(banks)
        out = {}
        for g, b in enumerate(banks):
            n = 0
            while n < 256:
                if n and (b + 4 * n) in starts:
                    break
                h = self.u32(self.off(b) + 4 * n)
                if not self.isptr(h) or not (self.isptr(self.u32(self.off(h))) and self.isptr(self.u32(self.off(h) + 4))):
                    break
                out[(g, n)] = h
                n += 1
        return out

    def header(self, h):
        o = self.off(h)
        lay, ev, scr, con = struct.unpack_from("<IIII", self.d, o)
        music, layout_id = struct.unpack_from("<HH", self.d, o + 0x10)
        return {"layout": lay, "events": ev, "scripts": scr, "connections": con, "music": music,
                "layout_id": layout_id, "mapsec": self.d[o + 0x14], "cave": self.d[o + 0x15],
                "weather": self.d[o + 0x16], "map_type": self.d[o + 0x17], "flags": self.d[o + 0x19],
                "battle_scene": self.d[o + 0x1B]}

    def layout(self, ptr):
        o = self.off(ptr)
        w, h, border, blocks, t1, t2 = struct.unpack_from("<IIIIII", self.d, o)
        bw, bh = self.d[o + 24], self.d[o + 25]
        return {"width": w, "height": h, "border": border, "blocks": blocks, "primary": t1, "secondary": t2,
                "border_w": bw or 2, "border_h": bh or 2}

    def text(self, ptr, maxlen=600):
        o, s = self.off(ptr), ""
        for i in range(maxlen):
            b = self.d[o + i]
            if b == 0xFF:
                break
            s += CHARS.get(b, f"{{{b:02X}}}")
        return s

    def location_name(self, mapsec):
        if mapsec < 0x58:
            return None
        p = self.u32(NAMES + 4 * (mapsec - 0x58))
        return self.text(p, 40) if self.isptr(p) else None

    # ---------------- tilesets ----------------
    def tileset(self, ptr):
        o = self.off(ptr)
        tiles, pals, mts, cb, attr = struct.unpack_from("<IIIII", self.d, o + 4)
        return {"compressed": self.d[o], "secondary": self.d[o + 1], "tiles": tiles, "palettes": pals,
                "metatiles": mts, "callback": cb, "attributes": attr}

    def tileset_tiles(self, ts):
        if ts["compressed"]:
            return self.lz77(ts["tiles"])
        n = 384 if ts["secondary"] else 640
        o = self.off(ts["tiles"])
        return self.d[o:o + n * 32]

    def tileset_palettes(self, ts):
        o = self.off(ts["palettes"])
        return [[((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)
                 for c in struct.unpack_from("<16H", self.d, o + 32 * i)] for i in range(16)]


def fr_tileset_names(pokefirered_headers):
    """Index -> FireRed tileset name (gTileset_X), in headers.h order (= struct order in the ROM)."""
    return re.findall(r"^const struct Tileset (gTileset_\w+)", open(pokefirered_headers, encoding="utf-8").read(), re.M)

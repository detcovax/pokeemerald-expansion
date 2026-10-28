"""TREY (6c-4b, TREY_PLAN.md D39-D42): the Orange Islands maps and their harmless events, from the ROM hack.

Run `python3 tools/trey/import_orange.py maps` from the project root (after a build: pokeemerald.map is used to
check the TREY labels the scripts call). Reads the hack (FireRed 1.0 base, tools/trey/orange_rom.py) and
../pokefirered for FireRed's constant names. Writes:
  data/maps/<Name>/map.json + scripts.inc      every valid Orange map (FRLG layouts, D31)
  data/layouts/<Name>/{map,border}.bin          one layout per hack layout, layouts.json entries ("frlg")
  data/maps/map_groups.json                     gMapGroup_Orange_{Outdoor,Dungeon,Underwater,Indoor_West,Indoor_East}
  data/scripts/trey_orange_maps.inc             includes the scripts (+ the "(Not built yet.)" sign)
  include/constants/trey_orange_flags.h         item ball / hidden item flags (TREY_FLAG_ORANGE_ITEMS block)
  include/constants/trey_orange_fly.h           Fly/Teleport list (towns with a Pokemon Center)
  src/data/heal_locations.json                  one heal location per Pokemon Center
  docs/trey/orange_import_report.txt            what was kept and dropped on every map

Kept (D39/D42): talkers whose script never branches (text, cries), signs, item balls, hidden items, nurses, cable
club attendants, Mart clerks (the hack's lists), Cut trees / Rock Smash rocks (TREY's scripts and sprites).
Dropped: trainers, branching talkers, triggers, story scripts, objects the hack hides on a new game.
"""
import collections
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orange_rom import Rom  # noqa: E402

FR_INIT_FLAGS_SCRIPT = 0x081A6481     # the hack's new-game "hide these objects" script (FireRed's address)
FR_NURSE = 0x081A6578
FR_CABLE_CLUB = {0x081BBA04: "Common_EventScript_UnionRoomAttendant",
                 0x081BBB6A: "Common_EventScript_WirelessClubAttendant",
                 0x081BBB9C: "Common_EventScript_DirectCornerAttendant"}
ITEM_FLAG_SLOTS = 256
NOT_BUILT = "TreyOrange_EventScript_NotBuiltYet"
MSGBOX = {2: "MSGBOX_NPC", 3: "MSGBOX_SIGN", 4: "MSGBOX_DEFAULT", 5: "MSGBOX_DEFAULT", 6: "MSGBOX_AUTOCLOSE"}
DIRECTIONS = {1: "down", 2: "up", 3: "left", 4: "right", 5: "dive", 6: "emerge"}
OUTDOOR_TYPES = {0, 1, 2, 3, 6}
GROUP_ORDER = ["gMapGroup_Orange_Outdoor", "gMapGroup_Orange_Dungeon", "gMapGroup_Orange_Underwater",
               "gMapGroup_Orange_Indoor_West", "gMapGroup_Orange_Indoor_Central", "gMapGroup_Orange_Indoor_East"]
FERRY = {"map": (22, 0), "sailor": (6, 8)}   # D43: Hamlin Harbor's own sailor runs the S.S. Tidal (TRANSIT_STOP_HAMLIN)
INDOOR_SPLIT_X = (8, 15)   # region map columns: Indoor_West / _Central / _East (check_maps: 126 maps per group)
# FireRed's script commands that are safe to copy 1:1 into a talker (anything else makes it "story").
LINEAR_OK = {"lock", "lockall", "faceplayer", "release", "releaseall", "end", "loadword", "callstd", "message",
             "waitmessage", "waitbuttonpress", "closemessage", "playmoncry", "waitmoncry", "textcolor", "waitse",
             "playse", "delay", "nop", "nop1", "pokemart"}
TILESET_ROLE = {"PokemonCenter": "PokemonCenter", "Mart": "Mart", "House1": "House", "House2": "House",
                "GymHall": "Hall", "Gym": "Gym", "MikanGym": "Gym", "TrovitaGym": "Gym", "FireGym": "Gym",
                "Lab": "Lab", "Harbor": "Harbor", "Hotel": "Hotel", "Museum": "Museum", "School": "School",
                "Shop": "Shop", "Daycare": "Daycare", "GameCorner": "GameCorner", "HallOfFame": "HallOfFame",
                "League": "League", "PowerPlant": "PowerPlant", "Showboat": "Deck", "OldSilph": "Floor",
                "TrovitoDept": "Floor", "Butwal": "Tower", "CableClub": "CableClub", "MikanHouse": "House",
                "NewIsland": "Lab", "LeagueGate": "Gate", "ShamoutiPath": "Path", "Sewers": "Sewers"}


def die(msg):
    sys.exit(f"import_orange.py maps: {msg}")


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def const_name(name):
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z][a-z])", "_", name).upper()


def camel(mapsec):
    return "".join(w.capitalize() for w in mapsec[len("MAPSEC_"):].split("_"))


# ---------------------------------------------------------------------------------------------------
# FireRed constants (names by value) and TREY constants (sets of names)
# ---------------------------------------------------------------------------------------------------
def fr_defines(path, prefix):
    out = {}
    for name, val in re.findall(r"#define\s+(" + prefix + r"\w+)\s+(0x[0-9A-Fa-f]+|\d+)\b", open(path, encoding="utf-8").read()):
        out.setdefault(int(val, 0), name)
    return out


def names_in(path, prefix):
    return set(re.findall(r"\b(" + prefix + r"[A-Z0-9_]+)\b", open(path, encoding="utf-8").read()))


class Consts:
    def __init__(self, pokefirered):
        inc = os.path.join(pokefirered, "include/constants")
        self.fr_species = fr_defines(f"{inc}/species.h", "SPECIES_")
        self.fr_items = fr_defines(f"{inc}/items.h", "ITEM_")
        self.fr_songs = fr_defines(f"{inc}/songs.h", "(?:MUS|SE)_")
        self.fr_moves = fr_defines(f"{inc}/event_object_movement.h", "MOVEMENT_TYPE_")
        self.fr_weather = fr_defines(f"{inc}/weather.h", "WEATHER_")
        self.fr_scene = fr_defines(f"{inc}/map_types.h", "MAP_BATTLE_SCENE_")
        self.species = names_in("include/constants/species.h", "SPECIES_")
        self.items = names_in("include/constants/items.h", "ITEM_")
        self.songs = names_in("include/constants/songs.h", "(?:MUS|SE)_")
        self.moves = names_in("include/constants/event_object_movement.h", "MOVEMENT_TYPE_")
        self.weather = names_in("include/constants/weather.h", "WEATHER_")
        self.scene = names_in("include/constants/map_types.h", "MAP_BATTLE_SCENE_")
        self.missing = collections.Counter()

    def species_name(self, v):
        n = self.fr_species.get(v)
        return n if n in self.species else None

    def item_name(self, v):
        n = self.fr_items.get(v)
        if n in self.items:
            return n
        if n:
            self.missing[n] += 1
        return None

    def song_name(self, v):
        n = self.fr_songs.get(v)
        if n is None:
            return None
        for cand in (n.replace("MUS_", "MUS_RG_", 1), n.replace("SE_", "SE_RG_", 1), n):
            if cand in self.songs:
                return cand
        self.missing[n] += 1
        return None

    def movement(self, v):
        n = self.fr_moves.get(v, "MOVEMENT_TYPE_FACE_DOWN")
        return n if n in self.moves else "MOVEMENT_TYPE_FACE_DOWN"

    def weather_name(self, v):
        n = self.fr_weather.get(v, "WEATHER_NONE")
        return n if n in self.weather else "WEATHER_NONE"

    def scene_name(self, v):
        n = self.fr_scene.get(v, "MAP_BATTLE_SCENE_NORMAL")
        return n if n in self.scene else "MAP_BATTLE_SCENE_NORMAL"


# ---------------------------------------------------------------------------------------------------
# Text: FireRed charmap -> TREY .string lines
# ---------------------------------------------------------------------------------------------------
class Charmap:
    FC_ARGS = {1: 1, 2: 1, 3: 1, 4: 3, 5: 1, 6: 1, 7: 0, 8: 1, 9: 0, 10: 0, 11: 2, 12: 1, 13: 1, 14: 1, 15: 0,
               16: 2, 17: 1, 18: 1, 19: 1, 20: 1, 21: 0, 22: 0, 23: 0, 24: 0}

    def __init__(self, fr_path, trey_path):
        self.single, self.fd = {}, {}
        for line in open(fr_path, encoding="utf-8"):
            line = line.split("@")[0].strip()
            m = re.match(r"^'(.+)'\s*=\s*([0-9A-F]{2})$", line)
            if m:
                ch = m.group(1)
                if ch not in ("\\n", "\\p", "\\l") and int(m.group(2), 16) not in self.single:
                    self.single[int(m.group(2), 16)] = ch
                continue
            m = re.match(r"^([A-Z_0-9]+)\s*=\s*FD ([0-9A-F]{2})$", line)
            if m and int(m.group(2), 16) not in self.fd:
                self.fd[int(m.group(2), 16)] = m.group(1)
        trey = open(trey_path, encoding="utf-8").read()
        self.trey_chars = set(re.findall(r"^'(.+)'\s*=", trey, re.M))
        self.trey_names = set(re.findall(r"^([A-Z_0-9]+)\s*=", trey, re.M))
        self.bad = collections.Counter()

    def decode(self, d, o, limit=1000):
        """-> list of lines (each ends with \\n, \\l, \\p or $)."""
        lines, cur = [], ""
        for _ in range(limit):
            b = d[o]
            o += 1
            if b == 0xFF:
                lines.append(cur + "$")
                return lines
            if b in (0xFE, 0xFA, 0xFB):
                lines.append(cur + {0xFE: "\\n", 0xFA: "\\l", 0xFB: "\\p"}[b])
                cur = ""
            elif b == 0xFD:
                name = self.fd.get(d[o])
                o += 1
                if name in self.trey_names:
                    cur += "{" + name + "}"
                else:
                    self.bad[f"FD {name}"] += 1
            elif b == 0xFC:
                o += self.FC_ARGS.get(d[o], 0) + 1
            else:
                ch = self.single.get(b)
                if ch is None or (ch not in self.trey_chars):
                    self.bad[f"{b:02X}"] += 1
                    ch = "?"
                cur += '\\"' if ch == '"' else ch
        lines.append(cur + "$")
        return lines


# ---------------------------------------------------------------------------------------------------
# Script decoding (FireRed command table from pokefirered)
# ---------------------------------------------------------------------------------------------------
def script_table(pokefirered):
    names = re.findall(r"ScrCmd_(\w+)", open(os.path.join(pokefirered, "data/script_cmd_table.inc")).read())
    src = open(os.path.join(pokefirered, "asm/macros/event.inc"), encoding="utf-8").read()
    src += open(os.path.join(pokefirered, "asm/macros/map.inc"), encoding="utf-8").read()   # "map" (group, num)
    bodies = {m.group(1): m.group(2) for m in re.finditer(r"\.macro (\w+)[^\n]*\n(.*?)\.endm", src, re.S)}
    memo = {}

    def expand(name, depth=0):
        """Byte sizes a macro emits (first branch of .if/.else), nested macros (map, formatwarp, ...) expanded."""
        if name in memo:
            return memo[name]
        out, skip = [], 0
        for line in bodies.get(name, "").split("\n"):
            line = line.split("@")[0].strip()
            if line.startswith(".if"):
                skip = skip * 2      # stays 0 on the first branch
                continue
            if line.startswith(".else"):
                skip = 1
                continue
            if line.startswith(".endif"):
                skip = 0
                continue
            if skip or not line:
                continue
            dm = re.match(r"\.(byte|2byte|4byte)\s+(.*)", line)
            if dm:
                out.append(({"byte": 1, "2byte": 2, "4byte": 4}[dm.group(1)], dm.group(2)))
            elif depth < 4:
                word = line.split()[0]
                if word in bodies and word != name:
                    out += expand(word, depth + 1)
        memo[name] = out
        return out

    sizes = {}
    for op, n in enumerate(names):
        cands = [k for k in bodies if (lambda v: v and v[0][1].lower() in (f"0x{op:02x}", f"{op:#x}", str(op)))(expand(k))]
        best = n if n in cands else (cands[0] if cands else None)
        if best:
            sizes[op] = [sz for sz, _ in expand(best)[1:]]
    sizes.update({0x50: [2, 4, 1, 1], 0x52: [2, 1, 1], 0x54: [2, 1, 1], 0x56: [2, 1, 1]})
    return names, sizes


class Script:
    """One linear decode of a script: list of (name, args); 'branch' set when control flow appears."""
    END = {"end", "return", "goto", "gotostd", "returnram", "endram"}

    def __init__(self, rom, names, sizes, ptr, limit=80):
        self.cmds, self.branch, self.bad = [], False, False
        if not rom.isptr(ptr):
            return
        d, o = rom.d, rom.off(ptr)
        for _ in range(limit):
            op = d[o]
            if op >= len(names) or op not in sizes or op == 0x5C:
                self.bad = op != 0x5C
                self.cmds.append(("trainerbattle" if op == 0x5C else f"op{op:02x}", []))
                return
            n = names[op]
            o += 1
            args = []
            for s in sizes[op]:
                args.append(int.from_bytes(d[o:o + s], "little"))
                o += s
            self.cmds.append((n, args))
            if n in ("goto_if", "call_if", "call", "goto", "gotostd_if", "callstd_if", "compare_var_to_value",
                     "compare_var_to_var", "checkflag", "specialvar", "random", "multichoice", "yesnobox"):
                self.branch = True
            if n in self.END:
                return

    def names(self):
        return [c[0] for c in self.cmds]


# ---------------------------------------------------------------------------------------------------
# The ROM's maps
# ---------------------------------------------------------------------------------------------------
def valid_maps(rom):
    """(group, num) -> (header ptr, header, layout): Orange locations with a sane layout (group 42 is junk past 0)."""
    out = {}
    for k, hp in sorted(rom.maps().items()):
        h = rom.header(hp)
        if not (0x58 <= h["mapsec"] <= 0xC4) or not rom.isptr(h["layout"]):
            continue
        lay = rom.layout(h["layout"])
        if not (1 <= lay["width"] <= 256 and 1 <= lay["height"] <= 256) or not rom.isptr(lay["blocks"]):
            continue
        if rom.isptr(h["events"]) and rom.d[rom.off(h["events"])] > 64:
            continue
        h["biking"] = rom.d[rom.off(hp) + 0x18]
        h["floor"] = struct.unpack_from("<b", rom.d, rom.off(hp) + 0x1A)[0]
        out[k] = (hp, h, lay)
    return out


def events_of(rom, h):
    d = rom.d
    if not rom.isptr(h["events"]):
        return [], [], [], []
    o = rom.off(h["events"])
    no, nw, nc, nb = d[o:o + 4]
    po, pw, pc, pb = struct.unpack_from("<IIII", d, o + 4)
    objs, warps, bgs = [], [], []
    for i in range(no if rom.isptr(po) else 0):
        q = rom.off(po) + 24 * i
        rng = struct.unpack_from("<H", d, q + 10)[0]
        objs.append({"local_id": d[q], "gfx": d[q + 1], "kind": d[q + 2], "x": struct.unpack_from("<h", d, q + 4)[0],
                     "y": struct.unpack_from("<h", d, q + 6)[0], "elevation": d[q + 8], "movement": d[q + 9],
                     "range_x": rng & 15, "range_y": (rng >> 4) & 15, "trainer_type": struct.unpack_from("<H", d, q + 12)[0],
                     "script": struct.unpack_from("<I", d, q + 16)[0], "flag": struct.unpack_from("<H", d, q + 20)[0]})
    for i in range(nw if rom.isptr(pw) else 0):
        q = rom.off(pw) + 8 * i
        warps.append({"x": struct.unpack_from("<h", d, q)[0], "y": struct.unpack_from("<h", d, q + 2)[0],
                      "elevation": d[q + 4], "warp_id": d[q + 5], "map": (d[q + 7], d[q + 6])})
    for i in range(nb if rom.isptr(pb) else 0):
        q = rom.off(pb) + 12 * i
        bgs.append({"x": struct.unpack_from("<h", d, q)[0], "y": struct.unpack_from("<h", d, q + 2)[0],
                    "elevation": d[q + 4], "kind": d[q + 5], "data": struct.unpack_from("<I", d, q + 8)[0]})
    return objs, warps, nc, bgs


def connections_of(rom, h):
    if not rom.isptr(h["connections"]):
        return []
    o = rom.off(h["connections"])
    n, p = struct.unpack_from("<iI", rom.d, o)
    if not rom.isptr(p) or not 0 <= n <= 8:
        return []
    out = []
    for i in range(n):
        q = rom.off(p) + 12 * i
        out.append({"direction": rom.d[q], "offset": struct.unpack_from("<i", rom.d, q + 4)[0],
                    "map": (rom.d[q + 8], rom.d[q + 9])})
    return out


def init_hidden_flags(rom, names, sizes, maps):
    """Flags of objects that are hidden on a new game: the hack's new-game script's setflags, plus every flag some
    map script clears (an object that appears later). Temp flags (< 0x20) reset on every map load."""
    d = rom.d
    hidden = {a[0] for n, a in Script(rom, names, sizes, FR_INIT_FLAGS_SCRIPT, limit=400).cmds if n == "setflag"}
    roots = []
    for _, h, _ in maps.values():
        objs, _, nc, bgs = events_of(rom, h)
        roots += [o["script"] for o in objs] + [b["data"] for b in bgs if b["kind"] <= 4]
        if rom.isptr(h["events"]):
            pc = struct.unpack_from("<I", d, rom.off(h["events"]) + 12)[0]
            for i in range(nc if rom.isptr(pc) else 0):
                roots.append(struct.unpack_from("<I", d, rom.off(pc) + 16 * i + 12)[0])
        if rom.isptr(h["scripts"]):
            o = rom.off(h["scripts"])
            while d[o]:
                t, p = d[o], struct.unpack_from("<I", d, o + 1)[0]
                o += 5
                if t in (2, 4) and rom.isptr(p):
                    q = rom.off(p)
                    while struct.unpack_from("<H", d, q)[0]:
                        roots.append(struct.unpack_from("<I", d, q + 4)[0])
                        q += 8
                else:
                    roots.append(p)
    seen, todo = set(), list(roots)
    tb_ptrs = {0: 2, 1: 3, 2: 3, 3: 1, 4: 3, 5: 2, 6: 4, 7: 3, 8: 4, 9: 2}
    while todo:
        p = todo.pop()
        if not rom.isptr(p) or p in seen:
            continue
        seen.add(p)
        o = rom.off(p)
        for _ in range(300):
            op = d[o]
            if op >= len(names) or op not in sizes:
                break
            if op == 0x5C:
                t = d[o + 1]
                o += 6
                ps = [struct.unpack_from("<I", d, o + 4 * i)[0] for i in range(tb_ptrs.get(t, 0))]
                o += 4 * len(ps)
                if t in (1, 2, 6, 8):
                    todo.append(ps[-1])
                continue
            n = names[op]
            o += 1
            args = []
            for sz in sizes[op]:
                args.append(int.from_bytes(d[o:o + sz], "little"))
                o += sz
            if n in ("call", "goto"):
                todo.append(args[0])
            elif n in ("goto_if", "call_if"):
                todo.append(args[1])
            elif n == "clearflag":
                hidden.add(args[0])
            if n in Script.END:
                break
    return {f for f in hidden if f >= 0x20}


# ---------------------------------------------------------------------------------------------------
# Main step
# ---------------------------------------------------------------------------------------------------
def step_maps(a):
    rom = Rom(a.rom)
    if not os.path.exists("pokeemerald.map"):
        die("build the ROM once first (pokeemerald.map lists the labels TREY has)")
    labels = set(re.findall(r"^\s+0x[0-9a-f]+\s+(\w+)$", open("pokeemerald.map", encoding="utf-8", errors="replace").read(), re.M))
    for need in ("Common_EventScript_PkmnCenterNurse", "Common_EventScript_FindItem", "EventScript_CutTree",
                 "EventScript_RockSmash", "EventScript_StrengthBoulder", *FR_CABLE_CLUB.values()):
        if need not in labels:
            die(f"{need} not found in pokeemerald.map")
    groups = jload("data/maps/map_groups.json")
    if any(g.startswith("gMapGroup_Orange_") for g in groups["group_order"]):
        die("Orange maps are already imported (remove the gMapGroup_Orange_* groups to re-import)")
    C = Consts(a.pokefirered)
    cm = Charmap(os.path.join(a.pokefirered, "charmap.txt"), "charmap.txt")
    names, sizes = script_table(a.pokefirered)
    mapsecs = jload("docs/trey/orange_mapsecs.json")
    tilesets = jload("docs/trey/orange_tilesets.json")
    sprites = {int(k): v for k, v in jload("docs/trey/orange_sprites.json").items()}
    gfx_names = open("include/constants/event_objects.h", encoding="utf-8").read()
    sections = {s["id"]: s for s in jload("src/data/region_map/region_map_sections.json")["map_sections"]}
    VM = valid_maps(rom)
    hidden_at_start = init_hidden_flags(rom, names, sizes, VM)
    ev = {k: events_of(rom, v[1]) for k, v in VM.items()}
    conns = {k: connections_of(rom, v[1]) for k, v in VM.items()}

    # 1. locations: the hack's own, or (D41) the location of the nearest named map it connects to
    loc = {}
    for k, (_, h, _) in VM.items():
        sid = mapsecs.get(f"{h['mapsec']:#04x}", "parent")
        if sid != "parent":
            loc[k] = sid
    nbrs = collections.defaultdict(set)
    for k in VM:
        for w in ev[k][1]:
            if w["map"] in VM:
                nbrs[k].add(w["map"])
                nbrs[w["map"]].add(k)
        for c in conns[k]:
            if c["map"] in VM:
                nbrs[k].add(c["map"])
                nbrs[c["map"]].add(k)
    for _ in range(10):
        for k in VM:
            if k not in loc:
                named = sorted(loc[n] for n in nbrs[k] if n in loc)
                if named:
                    loc[k] = collections.Counter(named).most_common(1)[0][0]
    unresolved = [k for k in VM if k not in loc]   # leftover scraps nothing leads to (D39: skipped)
    for k in unresolved:
        del VM[k]

    # 2. names: outdoor maps take the place's name; interiors <Place>_<Role><n>
    def role(k):
        _, h, lay = VM[k]
        ts = tilesets.get(hex(lay["secondary"]), "")
        r = TILESET_ROLE.get(ts.replace("gTileset_Orange", "").replace("gTileset_", ""))
        if r == "PokemonCenter":
            has_nurse = any(n == "call" and a and a[0] == FR_NURSE
                            for o in ev[k][0] for n, a in Script(rom, names, sizes, o["script"]).cmds)
            return "PokemonCenter_1F" if has_nurse else "PokemonCenter_2F"
        if r:
            return r
        return {4: "Cave", 5: "Underwater", 8: "Room"}.get(h["map_type"], "Area")
    by_loc = collections.defaultdict(list)
    for k in VM:
        by_loc[loc[k]].append(k)
    name_of = {}
    existing = set(os.listdir("data/maps"))
    for sid, ks in by_loc.items():
        place = camel(sid)
        outdoor = sorted((k for k in ks if VM[k][1]["map_type"] in OUTDOOR_TYPES),
                         key=lambda k: -VM[k][2]["width"] * VM[k][2]["height"])   # the biggest is the place itself
        for i, k in enumerate(outdoor):
            name_of[k] = place if i == 0 else f"{place}_{i + 1}"
        roles = collections.defaultdict(list)
        for k in ks:
            if k not in name_of:
                roles[role(k)].append(k)
        for r, rk in roles.items():
            for i, k in enumerate(rk):
                if place.endswith(r):   # OrangeSewers1, not OrangeSewers_Sewers1
                    name_of[k] = place if len(rk) == 1 and place not in name_of.values() else f"{place}{i + 1}"
                else:
                    name_of[k] = f"{place}_{r}" if len(rk) == 1 else f"{place}_{r}{i + 1}"
    for k, n in name_of.items():
        if n in existing:   # a folder from an earlier run of this step may be overwritten; anything else may not
            sp = f"data/maps/{n}/scripts.inc"
            if not (os.path.exists(sp) and open(sp, encoding="utf-8").read(40).startswith("@ TREY (6c-4b")):
                die(f"{n} already exists in data/maps")
    if len(set(name_of.values())) != len(name_of):
        die("duplicate map names")
    map_id = {k: "MAP_" + const_name(n) for k, n in name_of.items()}

    # 3. layouts: one per hack layout
    layout_users = collections.defaultdict(list)
    for k, (_, h, _) in VM.items():
        layout_users[h["layout"]].append(k)
    layout_name = {}
    for lp, ks in layout_users.items():
        ks = sorted(ks)
        layout_name[lp] = name_of[ks[0]] if len(ks) == 1 else "Orange" + role(ks[0]).replace("_", "") + f"_{lp & 0xFFFFFF:06X}"
    layout_json = jload("data/layouts/layouts.json")
    have_layouts = {l["id"] for l in layout_json["layouts"] if l}

    # 4. events
    ctx_flags = collections.OrderedDict()
    report, out = [], collections.OrderedDict()
    heal, fly = [], []
    for k in sorted(VM, key=lambda k: (GROUP_ORDER.index(group_of(VM[k][1], sections[loc[k]])), name_of[k])):
        hp, h, lay = VM[k]
        name, cname = name_of[k], const_name(name_of[k])
        notes = collections.Counter()
        objs, warps, ncoord, bgs = ev[k]
        if ncoord:
            notes["trigger dropped"] += ncoord
        text_blocks, scripts = [], []
        tcount = collections.Counter()

        def text_label(ptr):
            if not rom.isptr(ptr):
                return None
            tcount["t"] += 1
            lab = f"{name}_Text_{tcount['t']}"
            body = "".join(f"\t.string \"{ln}\"\n" for ln in cm.decode(rom.d, rom.off(ptr)))
            text_blocks.append(f"{lab}:\n{body}")
            return lab

        def linear(s, kind):
            """FireRed linear script -> TREY lines, or None."""
            if s.branch or s.bad or not s.cmds or any(n not in LINEAR_OK for n in s.names()):
                return None
            lines, pend, said = [], None, False
            for n, args in s.cmds:
                if n == "loadword":
                    pend = args[1] if args[0] == 0 else None
                elif n == "callstd":
                    if args[0] not in MSGBOX or pend is None:
                        return None
                    lab = text_label(pend)
                    if lab is None:
                        return None
                    lines.append(f"\tmsgbox {lab}, {MSGBOX[args[0]]}")
                    pend, said = None, True
                elif n == "message":
                    lab = text_label(args[0])
                    if lab is None:
                        return None
                    lines.append(f"\tmessage {lab}")
                    said = True
                elif n == "playmoncry":
                    sp = C.species_name(args[0])
                    if sp is None:
                        return None
                    lines.append(f"\tplaymoncry {sp}, CRY_MODE_NORMAL")
                elif n in ("playse",):
                    se = C.song_name(args[0])
                    if se:
                        lines.append(f"\tplayse {se}")
                elif n == "delay":
                    lines.append(f"\tdelay {args[0]}")
                elif n == "pokemart":
                    if kind != "mart":
                        return None
                    items, o = [], rom.off(args[0]) if rom.isptr(args[0]) else None
                    if o is None:
                        return None
                    while True:
                        v = struct.unpack_from("<H", rom.d, o)[0]
                        o += 2
                        if v == 0 or len(items) > 60:
                            break
                        it = C.item_name(v)
                        if it:
                            items.append(it)
                    lab = f"{name}_Mart{tcount['mart'] + 1}"
                    tcount["mart"] += 1
                    text_blocks.append(f"\t.align 2\n{lab}:\n" + "".join(f"\t.2byte {i}\n" for i in items) + "\tpokemartlistend\n")
                    lines.append(f"\tpokemart {lab}")
                elif n in ("textcolor", "nop", "nop1"):
                    continue
                else:
                    lines.append(f"\t{n}")
            if not said:
                return None
            if lines[-1] != "\tend":
                lines.append("\tend")
            return lines

        def new_script(base, lines):
            tcount[base] += 1
            lab = f"{name}_EventScript_{base}{tcount[base]}"
            scripts.append(f"{lab}::\n" + "\n".join(lines) + "\n")
            return lab

        # objects
        jobjs, nurse_lid = [], None
        for o in objs:
            if o["kind"] != 0:
                notes["clone object dropped"] += 1
                continue
            if o["flag"] and o["flag"] in hidden_at_start:
                notes["hidden on a new game, dropped"] += 1
                continue
            s = Script(rom, names, sizes, o["script"])
            cn = s.names()
            gfx = sprites.get(o["gfx"])
            entry = {"type": "object", "graphics_id": gfx, "x": o["x"], "y": o["y"], "elevation": o["elevation"],
                     "movement_type": C.movement(o["movement"]), "movement_range_x": o["range_x"],
                     "movement_range_y": o["range_y"], "trainer_type": "TRAINER_TYPE_NONE",
                     "trainer_sight_or_berry_tree_id": "0", "script": "0x0", "flag": "0"}
            if k == FERRY["map"] and (o["x"], o["y"]) == FERRY["sailor"]:
                lid = f"LOCALID_{cname}_FERRY_SAILOR"
                entry.update(local_id=lid, graphics_id="OBJ_EVENT_GFX_SAILOR_FRLG", script=f"{name}_TreyEventScript_FerrySailor")
                scripts.append(
                    f"@ TREY (6c-4b, D43): Hamlin Harbor's transit stop (data/scripts/trey_transit.inc), the S.S. Tidal (D30).\n"
                    f"{name}_TreyEventScript_FerrySailor::\n\tlock\n\tfaceplayer\n\tsetvar VAR_0x8004, TRANSIT_SHIP\n"
                    f"\tsetvar VAR_0x8005, TRANSIT_STOP_HAMLIN\n\tsetvar VAR_0x8007, 0\n\tcall TreyTransit_EventScript_ChooseDestination\n"
                    f"\tgoto_if_eq VAR_0x8006, TRANSIT_STOP_NONE, {name}_TreyEventScript_FerryEnd\n\tspecial TreyTransit_Board\n"
                    f"\tmsgbox {name}_TreyText_AllAboard, MSGBOX_DEFAULT\n\tclosemessage\n"
                    f"\tplayse SE_EXIT\n\tfadescreen FADE_TO_BLACK\n\twarp MAP_SS_TIDAL_CORRIDOR, 1, 10\n\twaitstate\n\trelease\n\tend\n\n"
                    f"{name}_TreyEventScript_FerryEnd:\n\trelease\n\tend\n\n"
                    f"{name}_TreyText_AllAboard:\n\t.string \"All aboard! Please head to your\\n\"\n"
                    f"\t.string \"cabin and enjoy the voyage.$\"\n")
                notes["ferry sailor (D43)"] += 1
                jobjs.append(entry)
                continue
            if "trainerbattle" in cn:
                notes["trainer dropped"] += 1
                continue
            # nurse / cable club
            if any(n == "call" and a[0] == FR_NURSE for n, a in s.cmds):
                nurse_lid = f"LOCALID_{cname}_NURSE"
                entry.update(local_id=nurse_lid, graphics_id="OBJ_EVENT_GFX_NURSE_FRLG",
                             script=f"{name}_TreyEventScript_Nurse")
                scripts.append(f"{name}_TreyEventScript_Nurse::\n\tsetvar VAR_0x800B, {nurse_lid}\n"
                               "\tcall Common_EventScript_PkmnCenterNurse\n\twaitmessage\n\twaitbuttonpress\n\trelease\n\tend\n")
                notes["nurse"] += 1
                jobjs.append(entry)
                continue
            if s.cmds and s.cmds[0][0] == "call" and s.cmds[0][1][0] in FR_CABLE_CLUB:
                entry.update(graphics_id="OBJ_EVENT_GFX_CABLE_CLUB_RECEPTIONIST", script=FR_CABLE_CLUB[s.cmds[0][1][0]])
                notes["cable club attendant"] += 1
                jobjs.append(entry)
                continue
            # obstacles (D42): TREY's scripts and sprites
            if gfx and ("CUT_TREE" in gfx or "ROCK_SMASH" in gfx or "BOULDER" in gfx):
                if "CUT_TREE" in gfx:
                    entry.update(graphics_id="OBJ_EVENT_GFX_CUTTABLE_TREE_FRLG", script="EventScript_CutTree")
                elif "ROCK_SMASH" in gfx:
                    entry.update(graphics_id="OBJ_EVENT_GFX_BREAKABLE_ROCK_FRLG", script="EventScript_RockSmash")
                else:
                    entry.update(graphics_id="OBJ_EVENT_GFX_PUSHABLE_BOULDER_FRLG", script="EventScript_StrengthBoulder")
                entry["movement_type"] = "MOVEMENT_TYPE_FACE_DOWN"
                notes["obstacle"] += 1
                jobjs.append(entry)
                continue
            # item ball
            if cn[:4] == ["setorcopyvar", "setorcopyvar", "callstd", "end"] and s.cmds[2][1][0] == 1 \
                    and s.cmds[0][1][0] == 0x8000:
                it = C.item_name(s.cmds[0][1][1])
                if it is None:
                    notes["item ball dropped (item not in TREY)"] += 1
                    continue
                flag = f"FLAG_ORANGE_ITEM_{cname}_{it[len('ITEM_'):]}"
                while flag in ctx_flags:
                    flag += "_2"
                ctx_flags[flag] = len(ctx_flags)
                entry.update(graphics_id="OBJ_EVENT_GFX_ITEM_BALL", script="Common_EventScript_FindItem",
                             trainer_sight_or_berry_tree_id=it, flag=flag, movement_type="MOVEMENT_TYPE_LOOK_AROUND")
                if s.cmds[1][1][1] > 1:
                    notes["item ball quantity > 1 (gives 1)"] += 1
                notes["item ball"] += 1
                jobjs.append(entry)
                continue
            if not s.cmds:
                if o["flag"] == 0 and gfx and re.search(r"\b" + re.escape(gfx) + r"\b", gfx_names):
                    jobjs.append(entry)
                    notes["object without script"] += 1
                else:
                    notes["object without script dropped"] += 1
                continue
            kind = "mart" if "pokemart" in cn else "talk"
            lines = linear(s, kind)
            if lines is None:
                notes["story/branching script dropped"] += 1
                continue
            if gfx is None or not re.search(r"\b" + re.escape(gfx) + r"\b", gfx_names):
                notes["unknown sprite, dropped"] += 1
                continue
            cry = next((a[0] for n, a in s.cmds if n == "playmoncry"), None)
            if cry is not None:
                sp = C.species_name(cry)
                if sp and ("_ORANGE_" in gfx or not gfx.endswith("_FRLG")):   # the hack's sprites (names guessed in 6c-2)
                    entry["graphics_id"] = f"OBJ_EVENT_GFX_SPECIES({sp[len('SPECIES_'):]})"
                    notes["Pokemon (follower sprite)"] += 1
            entry["script"] = new_script("Mart" if kind == "mart" else "Talk", lines)
            notes["mart clerk" if kind == "mart" else "talker"] += 1
            jobjs.append(entry)

        # warps
        jwarps, closed = [], []
        for w in warps:
            if w["map"] == (127, 127):
                jwarps.append({"x": w["x"], "y": w["y"], "elevation": w["elevation"], "dest_map": "MAP_DYNAMIC",
                               "dest_warp_id": "WARP_ID_DYNAMIC"})
            elif w["map"] in VM and ev[w["map"]][1]:   # a map with no warps of its own can't be arrived at by warp id
                jwarps.append({"x": w["x"], "y": w["y"], "elevation": w["elevation"], "dest_map": map_id[w["map"]],
                               "dest_warp_id": str(w["warp_id"])})
            else:
                closed.append(w)
                jwarps.append({"x": w["x"], "y": w["y"], "elevation": w["elevation"], "dest_map": "MAP_DYNAMIC",
                               "dest_warp_id": "WARP_ID_DYNAMIC", "_closed": True})
        # signs and hidden items
        jbgs = []
        for b in bgs:
            if b["kind"] == 7:
                v = b["data"]
                it = C.item_name(v & 0xFFFF)
                if it is None:
                    notes["hidden item dropped (item not in TREY)"] += 1
                    continue
                flag = f"FLAG_ORANGE_HIDDEN_{cname}_{it[len('ITEM_'):]}"
                while flag in ctx_flags:
                    flag += "_2"
                ctx_flags[flag] = len(ctx_flags)
                jbgs.append({"type": "hidden_item", "x": b["x"], "y": b["y"], "elevation": b["elevation"], "item": it,
                             "flag": flag, "quantity": max(1, (v >> 24) & 0x7F), "underfoot": bool(v >> 31)})
                notes["hidden item"] += 1
            elif b["kind"] <= 4:
                lines = linear(Script(rom, names, sizes, b["data"]), "sign")
                if lines is None:
                    notes["sign script dropped"] += 1
                    continue
                facing = ["BG_EVENT_PLAYER_FACING_ANY", "BG_EVENT_PLAYER_FACING_NORTH", "BG_EVENT_PLAYER_FACING_SOUTH",
                          "BG_EVENT_PLAYER_FACING_EAST", "BG_EVENT_PLAYER_FACING_WEST"][b["kind"]]
                jbgs.append({"type": "sign", "x": b["x"], "y": b["y"], "elevation": b["elevation"],
                             "player_facing_dir": facing, "script": new_script("Sign", lines)})
                notes["sign"] += 1
            else:
                notes[f"bg event kind {b['kind']} dropped"] += 1
        for w in closed:
            jbgs.append({"type": "sign", "x": w["x"], "y": w["y"], "elevation": 0,
                         "player_facing_dir": "BG_EVENT_PLAYER_FACING_ANY", "script": NOT_BUILT})
            notes["closed door (map not in the hack)"] += 1
        jwarps = [w for w in jwarps if not w.get("_closed")]
        # TREY renumbers nothing: closed warps are removed, so later warp ids into this map must shift
        # (handled after all maps are built, below).

        jconns = [{"map": map_id[c["map"]], "offset": c["offset"], "direction": DIRECTIONS[c["direction"]]}
                  for c in conns[k] if c["map"] in VM and c["direction"] in DIRECTIONS]
        music = C.song_name(h["music"]) or "MUS_RG_ROUTE1"
        j = {"id": map_id[k], "name": name, "layout": "LAYOUT_" + const_name(layout_name[h["layout"]]), "music": music,
             "region": "REGION_ORANGE", "region_map_section": loc[k], "requires_flash": bool(h["cave"]),
             "weather": C.weather_name(h["weather"]), "map_type": fr_map_type(h["map_type"]),
             "allow_cycling": bool(h["biking"]), "allow_escaping": bool(h["flags"] & 1),
             "allow_running": bool(h["flags"] & 2), "show_map_name": bool(h["flags"] & 4),
             "floor_number": h["floor"], "battle_scene": C.scene_name(h["battle_scene"]),
             "connections": jconns or None, "object_events": jobjs, "warp_events": jwarps, "coord_events": [],
             "bg_events": jbgs}
        head = (f"@ TREY (6c-4b, D42): generated by tools/trey/import_orange.py (maps) from the Orange Islands hack\n"
                f"@ (map {k[0]}.{k[1]}). Story scripts, trainers and triggers were removed; write TREY's story here by hand.\n\n")
        out[k] = {"j": j, "head": head, "heal": None, "scripts": scripts, "texts": text_blocks,
                  "nurse": nurse_lid, "closed": closed, "group": group_of(h, sections[loc[k]])}
        report.append((name, k, notes))

    # 5. warp ids: removed (closed) warps shift the ids of later warps on that map
    shift = {}
    for k in VM:
        idx, n = {}, 0
        for i, w in enumerate(ev[k][1]):
            if w["map"] == (127, 127) or (w["map"] in VM and ev[w["map"]][1]):
                idx[i] = n
                n += 1
        shift[map_id[k]] = idx
    for v in out.values():
        for w in v["j"]["warp_events"]:
            if w["dest_map"] in shift:
                w["dest_warp_id"] = str(shift[w["dest_map"]].get(int(w["dest_warp_id"]), 0))

    # 6. heal locations: one per Pokemon Center 1F, in front of its door on the map it opens onto
    our_heal = {x["id"] for x in jload("src/data/heal_locations.json")["heal_locations"]}
    for k, v in out.items():
        if not v["nurse"]:
            continue
        door = next(((w, ev[k][1]) for w in ev[k][1] if w["map"] in VM and VM[w["map"]][1]["map_type"] in OUTDOOR_TYPES), None)
        if door is None:
            continue
        w = door[0]
        outside = w["map"]
        dw = ev[outside][1][w["warp_id"]] if w["warp_id"] < len(ev[outside][1]) else None
        if dw is None:
            continue
        hid = "HEAL_LOCATION_" + loc[outside][len("MAPSEC_"):]
        while hid in our_heal or any(x["id"] == hid for x in heal):
            hid += "_2"
        heal.append({"id": hid, "map": map_id[outside], "x": dw["x"], "y": dw["y"] + 1,
                     "respawn_map": map_id[k], "respawn_npc": v["nurse"]})
        v["heal"] = hid
        sec = loc[outside]
        if sec not in [f[0] for f in fly]:
            fly.append((sec, map_id[outside], hid))

    if len(ctx_flags) > ITEM_FLAG_SLOTS:
        die(f"{len(ctx_flags)} item flags, but only {ITEM_FLAG_SLOTS} slots")
    gcount = collections.Counter(v["group"] for v in out.values())
    for g, n in gcount.items():
        if n > 126:
            die(f"{g} would hold {n} maps (check_maps.py allows 126)")
    for v in out.values():
        for o in v["j"]["object_events"]:
            gid = o["graphics_id"]
            if not gid.startswith("OBJ_EVENT_GFX_SPECIES(") and not re.search(r"\b" + re.escape(gid) + r"\b", gfx_names):
                die(f"{v['j']['name']}: unknown graphics {gid}")
    totals = collections.Counter()
    for _, _, n in report:
        totals.update(n)
    print(f"import_orange.py maps: {len(out)} maps, {len(layout_users)} layouts, {len(heal)} heal locations, "
          f"{len(ctx_flags)} item flags; groups " + ", ".join(f"{g[len('gMapGroup_'):]} {gcount[g]}" for g in GROUP_ORDER))
    print("  " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
    if unresolved:
        print(f"  {len(unresolved)} unreachable leftover maps skipped: {unresolved}")
    if cm.bad:
        print("  text bytes TREY can't show (as '?'):", dict(cm.bad.most_common(10)))
    if C.missing:
        print("  FireRed names TREY lacks:", dict(C.missing.most_common(12)))
    if a.dry:
        return out, heal, fly, name_of

    # 7. write
    for k, v in out.items():
        name = v["j"]["name"]
        os.makedirs(f"data/maps/{name}", exist_ok=True)
        jsave(f"data/maps/{name}/map.json", v["j"])
        with open(f"data/maps/{name}/scripts.inc", "w", encoding="utf-8", newline="\n") as f:
            ms = f"{name}_MapScripts::\n"
            if v["heal"]:
                ms += (f"\tmap_script MAP_SCRIPT_ON_TRANSITION, {name}_TreyOnTransition\n\t.byte 0\n\n"
                       f"{name}_TreyOnTransition:\n\tsetrespawn {v['heal']}\n\tend\n")
            else:
                ms += "\t.byte 0\n"
            f.write(v["head"] + ms + "\n" + "\n".join(v["scripts"]) + ("\n" if v["scripts"] else "")
                    + "\n".join(v["texts"]))
    for lp, ks in layout_users.items():
        lid = "LAYOUT_" + const_name(layout_name[lp])
        if lid in have_layouts:
            die(f"{lid} already exists in layouts.json")
        _, h, lay = VM[sorted(ks)[0]]
        folder = f"data/layouts/{layout_name[lp]}"
        os.makedirs(folder, exist_ok=True)
        w, hh = lay["width"], lay["height"]
        blocks = list(struct.unpack_from(f"<{w * hh}H", rom.d, rom.off(lay["blocks"])))
        for k in ks:   # closed doors: impassable
            for cw in out[k]["closed"]:
                i = cw["y"] * w + cw["x"]
                if 0 <= i < len(blocks):
                    blocks[i] = (blocks[i] & ~0x0C00) | 0x0400
        with open(f"{folder}/map.bin", "wb") as f:
            f.write(struct.pack(f"<{len(blocks)}H", *blocks))
        bw, bh = lay["border_w"], lay["border_h"]
        with open(f"{folder}/border.bin", "wb") as f:
            f.write(rom.d[rom.off(lay["border"]):rom.off(lay["border"]) + 2 * bw * bh])
        for t in (lay["primary"], lay["secondary"]):
            if hex(t) not in tilesets:
                die(f"layout {layout_name[lp]}: tileset {t:#x} was not imported in 6c-1")
        layout_json["layouts"].append({
            "id": lid, "name": f"{layout_name[lp]}_Layout", "width": w, "height": hh, "border_width": bw,
            "border_height": bh, "primary_tileset": tilesets[hex(lay["primary"])],
            "secondary_tileset": tilesets[hex(lay["secondary"])], "border_filepath": f"{folder}/border.bin",
            "blockdata_filepath": f"{folder}/map.bin", "layout_version": "frlg"})
    jsave("data/layouts/layouts.json", layout_json)
    for g in GROUP_ORDER:
        groups["group_order"].append(g)
        groups[g] = [v["j"]["name"] for v in out.values() if v["group"] == g]
    jsave("data/maps/map_groups.json", groups)
    hj = jload("src/data/heal_locations.json")
    hj["heal_locations"] += heal
    jsave("src/data/heal_locations.json", hj)
    with open("data/scripts/trey_orange_maps.inc", "w", encoding="utf-8", newline="\n") as f:
        f.write("@ TREY (6c-4b): generated by tools/trey/import_orange.py (maps). Script files of the Orange maps.\n\n"
                f"@ D37: doors whose map the hack doesn't have.\n{NOT_BUILT}::\n"
                "\tmsgbox TreyOrange_Text_NotBuiltYet, MSGBOX_SIGN\n\tend\n\n"
                "TreyOrange_Text_NotBuiltYet:\n\t.string \"(Not built yet.)$\"\n\n")
        for v in out.values():
            f.write(f"\t.include \"data/maps/{v['j']['name']}/scripts.inc\"\n")
    with open("include/constants/trey_orange_flags.h", "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY (6c-4b): generated by tools/trey/import_orange.py (maps). Item ball and hidden item flags of the\n"
                "// Orange maps, in TREY's flag space. Never reorder: saves use them.\n"
                "#ifndef GUARD_CONSTANTS_TREY_ORANGE_FLAGS_H\n#define GUARD_CONSTANTS_TREY_ORANGE_FLAGS_H\n\n")
        for flag, n in ctx_flags.items():
            f.write(f"#define {flag:<64} (TREY_FLAG_ORANGE_ITEMS_START + {n})\n")
        f.write(f"\n#define TREY_ORANGE_ITEM_FLAGS_USED {len(ctx_flags)}\n\n// Fly/Teleport destinations (trey_orange_fly.h order).\n")
        for i, (s, _, _) in enumerate(fly):
            f.write(f"#define FLAG_WORLD_MAP_ORANGE_{s[len('MAPSEC_'):]:<40} (TREY_FLAG_WORLD_MAP_ORANGE_START + {i})\n")
        f.write("\n#endif // GUARD_CONSTANTS_TREY_ORANGE_FLAGS_H\n")
    with open("include/constants/trey_orange_fly.h", "w", encoding="utf-8", newline="\n") as f:
        f.write("#ifndef GUARD_CONSTANTS_TREY_ORANGE_FLY_H\n#define GUARD_CONSTANTS_TREY_ORANGE_FLY_H\n\n"
                "// TREY (6c-4b): Orange's Fly/Teleport destinations: every place with a Pokemon Center (generated by\n"
                "// tools/trey/import_orange.py maps). F(location, map, heal location), names without the MAPSEC_/MAP_/\n"
                "// HEAL_LOCATION_ prefix. Entering the map sets FLAG_WORLD_MAP_ORANGE_<location> (src/trey_regions.c).\n"
                "#define TREY_ORANGE_FLY(F)" + "".join(
                    f" \\\n    F({s[len('MAPSEC_'):]}, {m[len('MAP_'):]}, {hh[len('HEAL_LOCATION_'):]})" for s, m, hh in fly)
                + "\n\n#endif // GUARD_CONSTANTS_TREY_ORANGE_FLY_H\n")
    os.makedirs("docs/trey", exist_ok=True)
    with open("docs/trey/orange_import_report.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("TREY (6c-4b): what tools/trey/import_orange.py (maps) kept and dropped on each Orange map.\n\n")
        for name, k, notes in report:
            f.write(f"{name} (hack map {k[0]}.{k[1]}): " + ", ".join(f"{a} {b}" for a, b in sorted(notes.items())) + "\n")
        f.write("\nTOTAL: " + ", ".join(f"{a} {b}" for a, b in sorted(totals.items())) + "\n")
    return out, heal, fly, name_of


def fr_map_type(t):
    return {0: "MAP_TYPE_NONE", 1: "MAP_TYPE_TOWN", 2: "MAP_TYPE_CITY", 3: "MAP_TYPE_ROUTE", 4: "MAP_TYPE_UNDERGROUND",
            5: "MAP_TYPE_UNDERWATER", 6: "MAP_TYPE_OCEAN_ROUTE", 8: "MAP_TYPE_INDOOR"}.get(t, "MAP_TYPE_INDOOR")


def group_of(h, section):
    t = h["map_type"]
    if t in OUTDOOR_TYPES:
        return "gMapGroup_Orange_Outdoor"
    if t == 4:
        return "gMapGroup_Orange_Dungeon"
    if t == 5:
        return "gMapGroup_Orange_Underwater"
    x = section.get("x", 0)
    if x < INDOOR_SPLIT_X[0]:
        return "gMapGroup_Orange_Indoor_West"
    return "gMapGroup_Orange_Indoor_Central" if x < INDOOR_SPLIT_X[1] else "gMapGroup_Orange_Indoor_East"

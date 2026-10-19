#!/usr/bin/env python3
"""TREY (5a, TREY_PLAN.md D25): import the FRLG Kanto/Sevii maps into the TREY (Emerald) build.

Upstream's FRLG maps use FRLG's own flags, variables, trainers and common scripts, which don't exist in an
Emerald build (and FRLG flag numbers overlap Emerald's). This tool rewrites each data/maps/*_Frlg map so it
builds in TREY:

  kept      warps, signs, talk-only NPCs (with their FRLG text), Poke Mart clerks, nurses, item balls,
            hidden items, decoration objects (no script), and objects the engine refers to by local ID
            (nurses for heal locations, etc.). Unsafe ones of the last kind get a placeholder line.
  rewritten nurses use Emerald's Common_EventScript_PkmnCenterNurse; clerks get a plain mart script;
            item ball and hidden item flags move into the TREY FRLG item flag block
            (FLAG_FRLG_*, include/constants/trey_frlg_flags.h).
  removed   trainers, coord (trigger) events, map scripts other than setrespawn, and any object or
            sign whose script reads FRLG story flags/vars or uses a command outside the safe list.

A script counts as "safe" when every command it can reach is on SAFE_CMDS, it touches no FLAG_/VAR_
other than VAR_RESULT/VAR_FACING, and every label it uses is either in the same file or exists in the
TREY build (read from pokeemerald.map, so build the ROM once before running this).

Story scripts are written for TREY per map as the story reaches it (Phase 5+); after that, edit the map's
files by hand and don't re-run this tool on that map (use --only to pick maps).

Usage (from the project root):
  python3 tools/trey/import_frlg.py --orig <dir with pristine upstream *_Frlg/map.json + scripts.inc>
         [--map pokeemerald.map] [--only MapName_Frlg ...] [--dry-run]
Writes data/maps/*_Frlg/{map.json,scripts.inc}, data/scripts/trey_frlg_maps.inc,
include/constants/trey_frlg_flags.h and docs/trey/frlg_import_report.txt.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

ITEM_FLAG_SLOTS = 512  # must match TREY_FLAG_FRLG_ITEMS_COUNT in include/constants/flags.h

SAFE_CMDS = {
    "lock", "lockall", "faceplayer", "release", "releaseall", "end", "return",
    "msgbox", "message", "waitmessage", "closemessage", "waitbuttonpress", "textcolor",
    "applymovement", "waitmovement", "turnobject",
    "playse", "waitse", "playmoncry", "waitmoncry", "playfanfare", "waitfanfare",
    "delay", "goto", "call", "pokemart", "braillemsgbox", "braillemessage_wait",
    "goto_if_eq", "goto_if_ne", "call_if_eq", "call_if_ne",
    "bufferspeciesname", "bufferitemname", "bufferstdstring",
}
ALLOWED_VARS = {"VAR_RESULT", "VAR_FACING"}


def strippable(cmd, args):
    """FRLG side effects that are simply removed from otherwise harmless scripts (Fame Checker entries,
    'talked to' story flags, map scene vars)."""
    if cmd == "famechecker":
        return True
    if cmd in ("setflag", "clearflag") and args and args[0].startswith("FLAG_") and not args[0].startswith("FLAG_TEMP"):
        return True
    if cmd == "setvar" and args and args[0].startswith("VAR_MAP_SCENE_"):
        return True
    return False
LABEL_RE = re.compile(r"^(\w+):{1,2}\s*(?:@.*)?$")
TOKEN_RE = re.compile(r"\b[A-Za-z_]\w*\b")


def die(msg):
    sys.exit(f"import_frlg.py: {msg}")


def parse_blocks(text):
    """Return (preamble lines, OrderedDict label -> list of lines). '.align' lines attach to the next label."""
    pre, blocks, cur, pending = [], collections.OrderedDict(), None, []
    for line in text.split("\n"):
        m = LABEL_RE.match(line)
        if m:
            cur = m.group(1)
            blocks[cur] = pending + [line]
            pending = []
            continue
        if line.strip().startswith(".align"):
            pending.append(line)
            continue
        if cur is None:
            pre.append(line)
        else:
            blocks[cur].append(line)
    return pre, blocks


def body(lines):
    out = []
    for l in lines[1:]:
        if LABEL_RE.match(l) or l.strip().startswith(".align"):
            continue
        code = l.split("@", 1)[0].strip()
        if code:
            out.append(code)
    return out


def is_data_block(lines):
    b = body(lines)
    return bool(b) and all(x.startswith(".") for x in b)


def split_cmd(code):
    parts = code.split(None, 1)
    args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
    return parts[0], args


class MapImport:
    def __init__(self, name, mapjson, scripts, ctx):
        self.name, self.j, self.ctx = name, mapjson, ctx
        self.pre, self.blocks = parse_blocks(scripts)
        self.kept_labels = []      # script/data labels to emit, in original order
        self.extra = []            # generated script blocks (list of text)
        self.notes = collections.Counter()
        self.localids = {e.get("local_id") for e in self.j.get("object_events", []) if e.get("local_id")}

    # --- safety analysis -------------------------------------------------------------------------
    def safe(self, label, kept_ids, seen=None):
        """True if the script at label (and everything it reaches) is safe. Collects reached labels."""
        seen = set() if seen is None else seen
        if label in seen:
            return True
        seen.add(label)
        if label not in self.blocks:
            return label in self.ctx.global_labels and not label.endswith("_Frlg")
        lines = self.blocks[label]
        if is_data_block(lines):
            return self.data_safe(lines)
        for code in body(lines):
            cmd, args = split_cmd(code)
            if cmd.startswith("."):
                return False
            if strippable(cmd, args):
                continue
            if cmd not in SAFE_CMDS:
                return False
            if cmd in ("goto_if_eq", "goto_if_ne", "call_if_eq", "call_if_ne") and args and args[0] not in ALLOWED_VARS:
                return False
            for tok in TOKEN_RE.findall(code.split(None, 1)[1] if " " in code or "\t" in code else ""):
                if not self.token_ok(tok, kept_ids, seen):
                    return False
        return True

    def data_safe(self, lines):
        for code in body(lines):
            for tok in TOKEN_RE.findall(code):
                if tok.startswith(("FLAG_", "VAR_", "TRAINER_")):
                    return False
        return True

    def token_ok(self, tok, kept_ids, seen):
        if tok.startswith("FLAG_") or tok.startswith("TRAINER_"):
            return False
        if tok.startswith("VAR_"):
            return tok in ALLOWED_VARS
        if tok.startswith("LOCALID_"):
            return tok == "LOCALID_PLAYER" or tok in kept_ids
        if tok in self.blocks:
            return self.safe(tok, kept_ids, seen)
        if tok[0].isupper() and "_" in tok and tok.isupper():
            return True   # constants (MSGBOX_*, ITEM_*, SE_*, DIR_*, ...)
        if tok in self.ctx.global_labels:
            return not tok.endswith("_Frlg")
        if re.fullmatch(r"\w+_(?:Text|EventScript|Movement|Items)_\w+", tok) or tok.startswith(("gText_", "Common_", "EventScript_", "Text_")):
            return False  # a label that doesn't exist in the TREY build
        return True       # plain words (YES, NO, TRUE, numbers handled by regex)

    def reach(self, label, out):
        """All local labels reachable from label (for emitting)."""
        if label in out or label not in self.blocks:
            return
        out.add(label)
        for code in body(self.blocks[label]):
            for tok in TOKEN_RE.findall(code):
                if tok in self.blocks:
                    self.reach(tok, out)

    # --- script rewrites -------------------------------------------------------------------------
    def reaches_cmd(self, label, cmd_name, arg=None, seen=None):
        seen = set() if seen is None else seen
        if label in seen or label not in self.blocks:
            return None
        seen.add(label)
        for code in body(self.blocks[label]):
            cmd, args = split_cmd(code)
            if cmd == cmd_name and (arg is None or (args and args[0] == arg)):
                return args
            for tok in TOKEN_RE.findall(code):
                if tok in self.blocks:
                    r = self.reaches_cmd(tok, cmd_name, arg, seen)
                    if r is not None:
                        return r
        return None

    def new_label(self, base):
        lab = f"{self.name}_TreyEventScript_{base}"
        n = 2
        while lab in self.blocks or lab in self.ctx.used_new:
            lab = f"{self.name}_TreyEventScript_{base}{n}"
            n += 1
        self.ctx.used_new.add(lab)
        return lab

    def nurse_script(self, localid):
        lab = self.new_label("Nurse")
        self.extra.append(f"{lab}::\n\tsetvar VAR_0x800B, {localid}\n\tcall Common_EventScript_PkmnCenterNurse\n"
                          f"\twaitmessage\n\twaitbuttonpress\n\trelease\n\tend\n")
        return lab

    def clerk_script(self, items_label):
        lab = self.new_label("Clerk")
        self.extra.append(f"{lab}::\n\tlock\n\tfaceplayer\n\tmessage gText_HowMayIServeYou\n\twaitmessage\n"
                          f"\tpokemart {items_label}\n\tmsgbox gText_PleaseComeAgain\n\trelease\n\tend\n")
        return lab

    # --- main ------------------------------------------------------------------------------------
    def run(self):
        objs = self.j.get("object_events", [])
        required = self.ctx.required_localids

        # 1. Decide which objects stay (iterate: a kept script may refer to another object by local ID).
        keep = [None] * len(objs)   # None = undecided, False = drop, or the new script label
        for i, o in enumerate(objs):
            otype = o.get("type", "object")
            if otype == "clone":
                keep[i] = "clone"
            elif o.get("trainer_type", "TRAINER_TYPE_NONE") != "TRAINER_TYPE_NONE":
                keep[i] = False
                self.notes["trainer"] += 1
            elif str(o.get("graphics_id", "")).startswith("OBJ_EVENT_GFX_VAR"):
                keep[i] = False
                self.notes["var graphics"] += 1
        changed = True
        while changed:
            changed = False
            kept_ids = {o.get("local_id") for o, k in zip(objs, keep) if k not in (None, False)}
            kept_ids |= {o.get("local_id") for o, k in zip(objs, keep) if k is None}  # optimistic
            for i, o in enumerate(objs):
                if keep[i] is not None:
                    continue
                decision = self.decide_object(o, kept_ids, required)
                if decision is not None:
                    keep[i] = decision
                    changed = True
            if not changed:
                # everything left undecided depends on others; decide pessimistically
                for i, o in enumerate(objs):
                    if keep[i] is None:
                        keep[i] = self.decide_object(o, {x.get("local_id") for x, k in zip(objs, keep) if k not in (None, False)}, required, final=True)
                        changed = True
                changed = False
        kept_ids = {o.get("local_id") for o, k in zip(objs, keep) if k}

        new_objs = []
        for o, k in zip(objs, keep):
            if not k:
                continue
            o = dict(o)
            if k not in ("clone", "same"):
                o["script"] = k
            if o.get("flag", "0") not in ("0", "", None):
                o["flag"] = self.ctx.item_flag(o["flag"])
            if k not in ("clone",) and o.get("script") not in ("0x0", "NULL", None):
                self.root(o["script"])
            new_objs.append(o)
        self.j["object_events"] = new_objs

        # 2. Background events.
        new_bgs = []
        for b in self.j.get("bg_events", []):
            t = b.get("type")
            if t == "hidden_item":
                b = dict(b)
                b["flag"] = self.ctx.item_flag(b["flag"])
                new_bgs.append(b)
                self.notes["hidden item"] += 1
            elif t == "sign":
                if self.safe(b.get("script", ""), kept_ids):
                    self.root(b["script"])
                    new_bgs.append(b)
                    self.notes["sign kept"] += 1
                else:
                    self.notes["sign dropped"] += 1
            else:
                self.notes[f"bg {t} dropped"] += 1
        self.j["bg_events"] = new_bgs

        # 3. Coord events: all story triggers.
        if self.j.get("coord_events"):
            self.notes["coord dropped"] += len(self.j["coord_events"])
        self.j["coord_events"] = []

        return self.emit_scripts(kept_ids)

    def decide_object(self, o, kept_ids, required, final=False):
        script = o.get("script", "0x0")
        flag = o.get("flag", "0")
        lid = o.get("local_id")
        is_item = o.get("graphics_id") == "OBJ_EVENT_GFX_ITEM_BALL" and script in self.ctx.item_ball_labels
        if is_item:
            self.notes["item ball"] += 1
            return "same"
        # nurse / clerk rewrites (any flag)
        if script in self.blocks and self.reaches_cmd(script, "call", "EventScript_PkmnCenterNurse_Frlg") is not None:
            if not lid:
                lid = f"LOCALID_{self.ctx.const_name(self.name)}_NURSE"
                o["local_id"] = lid
            self.notes["nurse"] += 1
            return self.nurse_script(lid)
        if script in self.blocks:
            args = self.reaches_cmd(script, "pokemart")
            if args and args[0] in self.blocks and self.data_safe(self.blocks[args[0]]):
                self.root(args[0])
                self.notes["clerk"] += 1
                return self.clerk_script(args[0])
        must = lid in required
        if flag not in ("0", "", None) and not must:
            self.notes["story object dropped"] += 1
            return False
        if script in ("0x0", "NULL", "", None):
            self.notes["decoration"] += 1
            return "same"
        if self.safe(script, kept_ids):
            self.notes["npc kept"] += 1
            return "same"
        if not final and any(t.startswith("LOCALID_") for t in self.all_tokens(script)):
            return None  # may become safe once other objects are decided
        if must:
            self.notes["placeholder"] += 1
            if flag not in ("0", "", None):
                o["flag"] = "0"
            return "TreyFrlg_EventScript_Placeholder"
        self.notes["npc dropped"] += 1
        return False

    def all_tokens(self, label, seen=None):
        seen = set() if seen is None else seen
        if label in seen or label not in self.blocks:
            return set()
        seen.add(label)
        out = set()
        for code in body(self.blocks[label]):
            for tok in TOKEN_RE.findall(code):
                out.add(tok)
                out |= self.all_tokens(tok, seen)
        return out

    def root(self, label):
        if label in self.blocks:
            self.reach(label, self.ctx.tmp_reach.setdefault(self.name, set()))

    def emit_scripts(self, kept_ids):
        reached = self.ctx.tmp_reach.get(self.name, set())
        ms_label = f"{self.name}_MapScripts"
        out = [f"@ TREY (5a): generated by tools/trey/import_frlg.py from upstream's {self.name}.",
               "@ FRLG story scripts, trainers and triggers were removed; write TREY's story here by hand.", ""]
        # map scripts: keep setrespawn only
        respawns = []
        if ms_label in self.blocks:
            for code in body(self.blocks[ms_label]):
                cmd, args = split_cmd(code)
                if cmd == "map_script" and len(args) == 2 and args[0] == "MAP_SCRIPT_ON_TRANSITION":
                    for c2 in body(self.blocks.get(args[1], [""])):
                        k, a = split_cmd(c2)
                        if k == "setrespawn" and a and a[0] in self.ctx.heal_ids:
                            respawns.append(a[0])
        if respawns:
            out += [f"{ms_label}::", f"\tmap_script MAP_SCRIPT_ON_TRANSITION, {self.name}_TreyOnTransition", "\t.byte 0", "",
                    f"{self.name}_TreyOnTransition:"]
            out += [f"\tsetrespawn {r}" for r in respawns] + ["\tend", ""]
        else:
            out += [f"{ms_label}::", "\t.byte 0", ""]
        used_tokens = set()
        for label, lines in self.blocks.items():
            if label in reached:
                if not is_data_block(lines):
                    lines = [l for l in lines if not (l.startswith("\t") and strippable(*split_cmd(l.split("@", 1)[0].strip())))]
                text = "\n".join(lines).rstrip()
                out.append(text)
                out.append("")
                used_tokens |= set(TOKEN_RE.findall(text))
        for e in self.extra:
            out.append(e)
        # keep .equ/.set lines the kept code uses
        pre = [l for l in self.pre if l.strip().startswith((".equ", ".set")) and
               TOKEN_RE.findall(l)[1] in used_tokens]
        return "\n".join(pre + ([""] if pre else []) + out).rstrip() + "\n"


class Ctx:
    def __init__(self, global_labels, item_ball_labels, heal_ids, required_localids):
        self.global_labels = global_labels
        self.item_ball_labels = item_ball_labels
        self.heal_ids = heal_ids
        self.required_localids = required_localids
        self.flags = collections.OrderedDict()
        self.used_new = set()
        self.tmp_reach = {}

    def item_flag(self, frlg_flag):
        if frlg_flag.startswith("FLAG_FRLG_"):
            return frlg_flag
        new = "FLAG_FRLG_" + frlg_flag[len("FLAG_"):]
        if new not in self.flags:
            self.flags[new] = len(self.flags)
        return new

    @staticmethod
    def const_name(map_name):
        n = map_name[:-5] if map_name.endswith("_Frlg") else map_name
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", n).upper()


def load_global_labels(map_path):
    labels = set()
    with open(map_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"\s+0x[0-9a-f]+\s+([A-Za-z_]\w*)\s*$", line)
            if m:
                labels.add(m.group(1))
    if len(labels) < 1000:
        die(f"{map_path} has too few symbols; build the ROM first")
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", required=True)
    ap.add_argument("--map", default="pokeemerald.map")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.exists("Makefile"):
        die("run from the project's root folder")

    global_labels = load_global_labels(a.map)
    with open("data/scripts/item_ball_scripts_frlg.inc", encoding="utf-8") as f:
        item_ball_labels = set(re.findall(r"^(\w+)::", f.read(), re.M))
    # FRLG common script files that TREY also builds (data/event_scripts.s, the !IS_FRLG branch)
    for p in ("data/scripts/flavor_text.inc",):
        with open(p, encoding="utf-8") as f:
            global_labels |= set(re.findall(r"^(\w+)::", f.read(), re.M))
    with open("src/data/heal_locations.json", encoding="utf-8") as f:
        heal = json.load(f)
    heal_ids = {h["id"] for h in heal["heal_locations"]}
    required = {h.get("respawn_npc") for h in heal["heal_locations"] if h.get("respawn_npc")}
    # local IDs used by C code / common scripts
    for pattern in ("src/*.c", "src/data/*.h", "include/*.h", "data/scripts/*.inc"):
        for p in glob.glob(pattern):
            if p.endswith("trey_frlg_maps.inc"):
                continue
            with open(p, encoding="utf-8", errors="ignore") as f:
                required |= set(re.findall(r"\bLOCALID_\w+", f.read()))
    ctx = Ctx(global_labels, item_ball_labels, heal_ids, required)

    names = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(a.orig, "*_Frlg", "map.json")))
    if not names:
        die(f"no *_Frlg maps in {a.orig}")
    report = []
    totals = collections.Counter()
    outputs = {}
    for name in names:
        with open(os.path.join(a.orig, name, "map.json"), encoding="utf-8") as f:
            mj = json.load(f)
        sp = os.path.join(a.orig, name, "scripts.inc")
        scripts = open(sp, encoding="utf-8").read() if os.path.exists(sp) else f"{name}_MapScripts::\n\t.byte 0\n"
        imp = MapImport(name, mj, scripts, ctx)
        text = imp.run()
        outputs[name] = (imp.j, text)
        totals.update(imp.notes)
        report.append(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(imp.notes.items())))

    if len(ctx.flags) > ITEM_FLAG_SLOTS:
        die(f"{len(ctx.flags)} item flags, but only {ITEM_FLAG_SLOTS} slots (TREY_FLAG_FRLG_ITEMS_COUNT)")

    if a.dry_run:
        print("\n".join(report))
        print("TOTAL:", dict(totals), "flags:", len(ctx.flags))
        return

    for name, (mj, text) in outputs.items():
        if a.only and name not in a.only:
            continue
        with open(os.path.join("data/maps", name, "map.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(mj, f, indent=2, ensure_ascii=False)
            f.write("\n")
        with open(os.path.join("data/maps", name, "scripts.inc"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    with open("data/scripts/trey_frlg_maps.inc", "w", encoding="utf-8", newline="\n") as f:
        f.write("@ TREY (5a): generated by tools/trey/import_frlg.py. Script files of the FRLG Kanto/Sevii maps.\n\n")
        f.write("TreyFrlg_EventScript_Placeholder::\n\tmsgbox TreyFrlg_Text_Placeholder, MSGBOX_NPC\n\tend\n\n")
        f.write("TreyFrlg_Text_Placeholder::\n\t.string \"…$\"\n\n")
        for name in names:
            f.write(f"\t.include \"data/maps/{name}/scripts.inc\"\n")

    with open("include/constants/trey_frlg_flags.h", "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY (5a): generated by tools/trey/import_frlg.py. Item ball and hidden item flags of the FRLG\n")
        f.write("// Kanto/Sevii maps, renamed FLAG_FRLG_* and moved into TREY's flag space. Never reorder: saves use them.\n")
        f.write("#ifndef GUARD_CONSTANTS_TREY_FRLG_FLAGS_H\n#define GUARD_CONSTANTS_TREY_FRLG_FLAGS_H\n\n")
        for flag, n in ctx.flags.items():
            f.write(f"#define {flag:<56} (TREY_FLAG_FRLG_ITEMS_START + {n})\n")
        f.write(f"\n#define TREY_FRLG_ITEM_FLAGS_USED {len(ctx.flags)}\n\n#endif // GUARD_CONSTANTS_TREY_FRLG_FLAGS_H\n")

    os.makedirs("docs/trey", exist_ok=True)
    with open("docs/trey/frlg_import_report.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("TREY (5a): what tools/trey/import_frlg.py kept and removed on each FRLG map.\n\n")
        f.write("\n".join(report) + "\n\nTOTAL: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) + "\n")
    print(f"import_frlg.py: {len(names)} maps, {len(ctx.flags)} item flags. " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))


if __name__ == "__main__":
    main()

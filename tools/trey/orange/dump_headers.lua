-- TREY (6c-1): mGBA (0.10+) script that makes the Orange Islands hack load EVERY map once and logs the map
-- header the game actually built for it. Layouts, tilesets, events and scripts are then read from the ROM file,
-- so only the group/num -> header step needs the running game (the hack hooks it).
--
-- How to use:
--   1. Open the hack in mGBA, load a save and stand anywhere in the overworld (not in a menu or cutscene).
--   2. Tools > Scripting... > File > Load script... > this file. Leave it alone for the first ~3 seconds
--      (it looks for free memory), then turn on fast-forward.
--   3. When the console says "DONE", send orange_headers.txt (next to this script).
-- Your save file is never written; the script only uses save states in memory.
--
-- v4: the fake script/table go into a 256-byte EWRAM block that stays zero for 2 seconds (v1-v3 used
-- 0x0203FE00, which the hack itself appears to use). The warp is started by an ON_FRAME map script whose test is
-- 1 == 1 (VarGet of a number below the var range returns the number), so no key presses are needed.
-- A hit counts only if the save block location becomes the target map.

local GMAPHEADER = 0x02036DFC
local SB1PTR = 0x03005008
local MAX_GROUP, MAX_NUM, MAX_MISSES, TIMEOUT = 63, 255, 12, 300

local path = (script and script.dir and (script.dir .. "/orange_headers.txt")) or "orange_headers.txt"
local out = io.open(path, "w")
local function log(s) console:log(s); if out then out:write(s .. "\n"); out:flush() end end

local function hex(addr, len)
    local b = emu:readRange(addr, len)
    local t = {}
    for i = 1, #b do t[#t + 1] = string.format("%02x", string.byte(b, i)) end
    return table.concat(t)
end

local function sb1()
    local s = emu:read32(SB1PTR)
    if s < 0x02000000 or s > 0x0203FFFF then return nil end
    return s
end

local function location()
    local s = sb1()
    if not s then return nil, nil end
    return emu:read8(s + 4), emu:read8(s + 5)
end

HEADER_COPIES = {}   -- v5: every RAM copy of the current map header (the engine may not read 0x02036DFC)

local function findHeaderCopies(header)
    local found = {}
    for _, r in ipairs({{0x02000000, 0x40000}, {0x03000000, 0x8000}}) do
        local mem = emu:readRange(r[1], r[2])
        local i = 1
        while true do
            local j = mem:find(header, i, true)
            if not j then break end
            if (j - 1) % 4 == 0 then found[#found + 1] = r[1] + j - 1 end
            i = j + 1
        end
    end
    return found
end

PX, PY = 0, 0
local base = nil
local startGroup, startNum = nil, nil
local FAKE = nil
local group, num, misses, found, attempts = 0, 0, 0, 0, 0
local phase, timer = "scan1", 0
local snap = nil

local function zeroBlocks()
    local mem = emu:readRange(0x02000000, 0x40000)
    local ok = {}
    for blk = 0, 0x40000 / 256 - 1 do
        local i = blk * 256 + 1
        if mem:sub(i, i + 255) == string.rep("\0", 256) then ok[blk] = true end
    end
    return ok
end

local function patch()
    -- warp script: warp <group> <num> 0xFF x=0 y=0 ; end   (FRLG script command 0x39)
    local s = FAKE + 0x40
    emu:write8(s + 0, 0x39); emu:write8(s + 1, group); emu:write8(s + 2, num); emu:write8(s + 3, 0xFF)
    emu:write16(s + 4, 0); emu:write16(s + 6, 0); emu:write8(s + 8, 0x02)
    -- ON_FRAME table: {u16 1, u16 1, u32 script}, then 0
    local t = FAKE + 0x20
    emu:write16(t + 0, 1); emu:write16(t + 2, 1); emu:write32(t + 4, s); emu:write16(t + 8, 0)
    -- map scripts list: {u8 2 = ON_FRAME_TABLE, u32 pointer (unaligned)}, then 0
    emu:write8(FAKE + 0, 2)
    emu:write8(FAKE + 1, t & 0xFF); emu:write8(FAKE + 2, (t >> 8) & 0xFF)
    emu:write8(FAKE + 3, (t >> 16) & 0xFF); emu:write8(FAKE + 4, (t >> 24) & 0xFF)
    emu:write8(FAKE + 5, 0)
    for _, h in ipairs(HEADER_COPIES) do emu:write32(h + 8, FAKE) end   -- v5: every copy of the header
    -- v6: step triggers (coord events) on the 4 tiles around the player; test VarGet(1) == 1 (always true)
    local c = FAKE + 0x80
    local around = {{0, 1}, {0, -1}, {-1, 0}, {1, 0}}
    for k, d in ipairs(around) do
        local e = c + (k - 1) * 16
        emu:write16(e + 0, (PX + d[1]) & 0xFFFF); emu:write16(e + 2, (PY + d[2]) & 0xFFFF)
        emu:write8(e + 4, 0); emu:write8(e + 5, 0)
        emu:write16(e + 6, 1); emu:write16(e + 8, 1); emu:write16(e + 10, 0); emu:write32(e + 12, s)
    end
    local ev = FAKE + 0x60   -- events table: 0 objects, 0 warps, 4 coord events, 0 bg events
    emu:write8(ev + 0, 0); emu:write8(ev + 1, 0); emu:write8(ev + 2, 4); emu:write8(ev + 3, 0)
    emu:write32(ev + 4, 0); emu:write32(ev + 8, 0); emu:write32(ev + 12, c); emu:write32(ev + 16, 0)
    for _, h in ipairs(HEADER_COPIES) do emu:write32(h + 4, ev) end
end

-- v6: hold one direction at a time (Down, Up, Left, Right; 30 frames each), both setKeys and addKey styles
local DIRS = {7, 6, 5, 4}   -- GBA key bits: Down, Up, Left, Right
local function press(timer)
    local k = math.floor((timer - 1) / 30) + 1
    for _, b in ipairs(DIRS) do pcall(function() emu:clearKey(b) end) end
    if timer <= 120 then
        local bit = DIRS[k]
        pcall(function() emu:setKeys(1 << bit) end)
        pcall(function() emu:addKey(bit) end)
    else
        pcall(function() emu:setKeys(0) end)
    end
end

local function advance(hit)
    if hit then misses = 0 else misses = misses + 1 end
    num = num + 1
    if num > MAX_NUM or misses >= MAX_MISSES then group, num, misses = group + 1, 0, 0 end
    if group > MAX_GROUP then
        log(string.format("DONE: %d maps found", found))
        emu:loadStateBuffer(base)
        if out then out:close(); out = nil end
        phase = "done"
        return
    end
    phase = "setup"
end

callbacks:add("frame", function()
    if phase == "done" then return end
    timer = timer + 1
    if phase == "scan1" then
        if timer == 1 then
            base = emu:saveStateBuffer()
            startGroup, startNum = location()
            PX, PY = emu:read16(sb1()), emu:read16(sb1() + 2)
            log(string.format("TREY dump v6 start: map %s %s, header %s", tostring(startGroup), tostring(startNum),
                hex(GMAPHEADER, 0x1C)))
            snap = zeroBlocks()
        elseif timer == 120 then
            local now = zeroBlocks()
            local s = sb1() or 0
            for blk = 0x40000 / 256 - 1, 0, -1 do
                local addr = 0x02000000 + blk * 256
                local nearSave = addr >= s - 0x4000 and addr <= s + 0x4000
                if snap[blk] and now[blk] and not nearSave and addr < 0x0203F000 then FAKE = addr; break end
            end
            if not FAKE then log("ERROR: no free 256-byte block found in EWRAM"); phase = "done"; return end
            log(string.format("using free EWRAM at %08x", FAKE))
            HEADER_COPIES = findHeaderCopies(emu:readRange(GMAPHEADER, 0x1C))
            local list = {}
            for _, h in ipairs(HEADER_COPIES) do list[#list + 1] = string.format("%08x", h) end
            log("header copies in RAM: " .. table.concat(list, " "))
            -- also any 4-aligned word holding Valencia's map scripts pointer (in case only that field is cached)
            local ms = emu:readRange(GMAPHEADER + 8, 4)
            local hits = {}
            for _, r in ipairs({{0x02000000, 0x40000}, {0x03000000, 0x8000}}) do
                local mem = emu:readRange(r[1], r[2])
                local i = 1
                while true do
                    local j = mem:find(ms, i, true)
                    if not j then break end
                    if (j - 1) % 4 == 0 then hits[#hits + 1] = string.format("%08x", r[1] + j - 1) end
                    i = j + 1
                end
            end
            log("words holding the map scripts pointer: " .. table.concat(hits, " "))
            phase = "setup"
        end
        return
    end
    if phase == "setup" then
        emu:loadStateBuffer(base); timer = 0; phase = "wait"; attempts = attempts + 1
        if num % 16 == 0 then
            console:log(string.format("trying group %d, map %d ... (%d found so far)", group, num, found))
        end
        return
    end
    -- phase "wait"
    local g, n = location()
    if timer <= 130 and g == startGroup and n == startNum then patch() end
    press(timer)
    if attempts <= 2 and (timer % 15 == 0) and timer <= 150 then
        local s = sb1()
        log(string.format("  [check %d frame %d] pos=%s,%s location=%s,%s keys=%s", attempts, timer,
            s and emu:read16(s) or "?", s and emu:read16(s + 2) or "?", tostring(g), tostring(n),
            tostring(select(2, pcall(function() return emu:getKeys() end)))))
    end
    if g == group and n == num and not (g == startGroup and n == startNum) and timer > 40 then
        found = found + 1
        log(string.format("map %d %d %s", group, num, hex(GMAPHEADER, 0x1C)))
        advance(true)
    elseif timer > TIMEOUT then
        advance(false)
    end
end)

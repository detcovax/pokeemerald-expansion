-- TREY (6c survey): mGBA (0.10 or newer) probe for the Orange Islands ROM hack.
--
-- How to use: open the Orange Islands .gba in mGBA, load a save (or start a game) and get into the overworld,
-- then Tools > Scripting... > File > Load script... and pick this file. Walk into 5-6 different maps
-- (a town, a house, a route, a cave, another island). Every time the map changes, one block is logged.
-- The log goes to orange_probe.txt next to this script (and to the scripting console). Send that file back.
--
-- What it reads (FireRed Rev 1 addresses; the hack kept these): gMapHeader at 0x02036DFC (the header the game
-- actually loaded), the layout it points to, both tilesets, the events table, and the save block location.

local GMAPHEADER = 0x02036DFC
local SB1_PTRS = {0x03005008, 0x030063EC}   -- FireRed's gSaveBlock1Ptr, and the address the hack's code uses

local out = nil
local path = (script and script.dir and (script.dir .. "/orange_probe.txt")) or "orange_probe.txt"
pcall(function() out = io.open(path, "a") end)

local function log(s)
    console:log(s)
    if out then out:write(s .. "\n"); out:flush() end
end

local function hex(addr, len)
    local ok, bytes = pcall(function() return emu:readRange(addr, len) end)
    if not ok or bytes == nil then return "?" end
    local t = {}
    for i = 1, #bytes do t[#t + 1] = string.format("%02x", string.byte(bytes, i)) end
    return table.concat(t)
end

local function r32(addr)
    local ok, v = pcall(function() return emu:read32(addr) end)
    if ok then return v end
    return 0
end

local last = nil
local count = 0

local function dump()
    local header = hex(GMAPHEADER, 0x1C)
    if header == last or header == "?" then return end
    last = header
    count = count + 1
    log(string.format("=== map %d (frame %d)", count, emu:currentFrame()))
    log("header " .. header)
    for _, p in ipairs(SB1_PTRS) do
        local sb1 = r32(p)
        log(string.format("sb1ptr@%08x = %08x  pos+location: %s", p, sb1, hex(sb1, 16)))
    end
    local layout = r32(GMAPHEADER)
    local events = r32(GMAPHEADER + 4)
    log(string.format("layout @%08x: %s", layout, hex(layout, 24)))
    local w, h = r32(layout), r32(layout + 4)
    local border, map = r32(layout + 8), r32(layout + 12)
    local ts1, ts2 = r32(layout + 16), r32(layout + 20)
    log(string.format("  border @%08x: %s", border, hex(border, 16)))
    log(string.format("  map    @%08x: %s", map, hex(map, 64)))
    log(string.format("  tileset1 @%08x: %s", ts1, hex(ts1, 28)))
    log(string.format("  tileset2 @%08x: %s", ts2, hex(ts2, 28)))
    log(string.format("events @%08x: %s", events, hex(events, 20)))
    log(string.format("  size %dx%d", w, h))
end

callbacks:add("frame", dump)
log("TREY probe loaded: walk into a few different maps. Log file: " .. path)

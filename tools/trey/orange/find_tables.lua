-- TREY (6c-1, v7): read-only mGBA scan for the Orange Islands hack's map group table in RAM.
-- The probe showed the hack resolving maps through banks at 0x08352078 (group 1), 0x08352264 (2), 0x08352354 (3),
-- 0x088963D0 (4) and 0x0885DD88 (5); no table holding those exists in the ROM, so it is probably built in RAM.
-- This script only reads memory: load a save, stand in the overworld, load this script, and send
-- orange_tables.txt (next to this script). No warps, no key presses, nothing is written.

local path = (script and script.dir and (script.dir .. "/orange_tables.txt")) or "orange_tables.txt"
local out = io.open(path, "w")
local function log(s) console:log(s); if out then out:write(s .. "\n"); out:flush() end end

local function le32(v) return string.char(v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF) end
local function hex(addr, len)
    local b = emu:readRange(addr, len)
    local t = {}
    for i = 1, #b do t[#t + 1] = string.format("%02x", string.byte(b, i)) end
    return table.concat(t)
end

local REGIONS = {{"EWRAM", 0x02000000, 0x40000}, {"IWRAM", 0x03000000, 0x8000}}
local NEEDLES = {0x08352078, 0x08352264, 0x08352354, 0x088963D0, 0x0885DD88, 0x088963EC, 0x08352718, 0x083526A8}

local done = false
callbacks:add("frame", function()
    if done then return end
    done = true
    log("TREY find_tables v7")
    for _, r in ipairs(REGIONS) do
        local mem = emu:readRange(r[2], r[3])
        for _, v in ipairs(NEEDLES) do
            local i, hits = 1, {}
            while true do
                local j = mem:find(le32(v), i, true)
                if not j then break end
                if (j - 1) % 4 == 0 then hits[#hits + 1] = r[2] + j - 1 end
                i = j + 1
            end
            for _, a in ipairs(hits) do
                log(string.format("%s %08x found at %08x: %s", r[1], v, a, hex(a - 32, 96)))
            end
        end
    end
    -- IWRAM words the hack's layout loader may use (its literal is 0x038963EC = IWRAM mirror of 0x030063EC)
    log("iwram 030063e0: " .. hex(0x030063E0, 48))
    log("DONE")
    if out then out:close() end
end)

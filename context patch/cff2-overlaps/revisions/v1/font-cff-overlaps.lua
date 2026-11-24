-- Somerville CFF2 -> CFF1 overlap conversion support. No font source is modified.
-- Loaded only by the accompanying, narrowly scoped font-cff/font-shp patch.
local M = { cachetag = "cff2-overlaps-v1" }
local report = logs.reporter("otf reader", "cff2 overlaps")
local source = debug.getinfo(1,"S").source
local directory = source:sub(1,1) == "@" and file.dirname(source:sub(2)) or "."
local detected = { }

local function uint(s,p,n)
    if not s or #s < p+n-1 then return nil end
    local v = 0
    for i=p,p+n-1 do v = v * 256 + s:byte(i) end
    return v
end

-- Read only sfnt directory records. TTC subfonts use ConTeXt's one-based index.
function M.iscff2(filename,sub,size,mtime)
    local key = filename .. ":" .. tostring(sub or 0) .. ":" .. tostring(size) .. ":" .. tostring(mtime)
    if detected[key] ~= nil then return detected[key] end
    local f = io.open(filename,"rb")
    if not f then return false end
    local h = f:read(12)
    local offset = 0
    if h and h:sub(1,4) == "ttcf" then
        local n = uint(h,9,4)
        local index = tonumber(sub) or 1
        if index < 1 or not n or index > n then f:close(); return false end
        f:seek("set",12+4*(index-1))
        offset = uint(f:read(4),1,4)
        if not offset then f:close(); return false end
        f:seek("set",offset)
        h = f:read(12)
    end
    local n = uint(h,5,2)
    local signature = h and h:sub(1,4)
    local found = false
    if n and (signature == "OTTO" or signature == "true" or signature == "\0\1\0\0") then
        for i=1,n do
            local record = f:read(16)
            if not record or #record ~= 16 then break end
            if record:sub(1,4) == "CFF2" then found = true; break end
        end
    end
    f:close()
    detected[key] = found
    return found
end

local function shellquote(s)
    assert(type(s)=="string" and not s:find("\0",1,true),"invalid helper argument")
    return "'" .. s:gsub("'", "'\\''") .. "'"
end

local function finite(n)
    return type(n)=="number" and n==n and n~=math.huge and n~=-math.huge
end

function M.convert(glyphs)
    if #glyphs == 0 then return { } end
    if not utilities.json then require("util-jsn") end
    local json = utilities.json
    local configdata = io.loaddata(directory .. "/font-cff-overlaps-config.json")
    local config = configdata and json.tolua(configdata)
    local python = os.getenv("CONTEXT_CFF2_OVERLAPS_PYTHON") or config and config.python
    assert(type(python)=="string" and python~="", "CFF2 overlap helper Python is not configured")
    local helper = directory .. "/font-cff-overlaps.py"
    local reserved = os.tmpname()
    local input, output, errfile = reserved..".in.json", reserved..".out.json", reserved..".stderr"
    local ok, response = pcall(function()
        -- ConTeXt's JSON encoder represents an empty Lua table as {}, whereas
        -- this protocol requires [] for a glyph with no contours (e.g. space).
        local requests = { }
        for i=1,#glyphs do
            local g = glyphs[i]
            local segments = #g.segments==0 and "[]" or json.tojson(g.segments)
            requests[i] = '{"id":'..tostring(g.id)..',"segments":'..segments..'}'
        end
        local request = '{"protocol":1,"glyphs":['..table.concat(requests,",")..']}'
        assert(io.savedata(input,request),"cannot write CFF2 overlap input")
        local command = shellquote(python).." "..shellquote(helper).." "..shellquote(input).." "..shellquote(output).." 2>"..shellquote(errfile)
        local status = os.execute(command)
        if status ~= true and status ~= 0 then
            error("CFF2 overlap helper failed: " .. (io.loaddata(errfile) or tostring(status)))
        end
        local data = io.loaddata(output)
        assert(data and #data>0,"CFF2 overlap helper produced no output")
        local result = json.tolua(data)
        assert(type(result)=="table" and result.protocol==1 and type(result.glyphs)=="table", "invalid CFF2 overlap response")
        assert(#result.glyphs==#glyphs,"CFF2 overlap response glyph count mismatch")
        local seen = { }
        for i=1,#result.glyphs do
            local g = result.glyphs[i]
            assert(type(g)=="table" and g.id==glyphs[i].id and not seen[g.id] and type(g.changed)=="boolean" and type(g.segments)=="table", "invalid CFF2 overlap response glyph")
            seen[g.id] = true
            for j=1,#g.segments do
                local s = g.segments[j]
                assert(type(s)=="table","invalid CFF2 overlap segment")
                local op = s[#s]
                local count = op=="c" and 7 or (op=="m" or op=="l") and 3
                assert(count and #s==count,"invalid CFF2 overlap segment operator")
                for k=1,#s-1 do assert(finite(s[k]),"invalid CFF2 overlap coordinate") end
            end
        end
        report("resolved %i glyphs (%i changed); helper wall time %s s",#glyphs,result.stats and result.stats.changed or -1,tostring(result.stats and result.stats.seconds or "unknown"))
        return result.glyphs
    end)
    os.remove(input); os.remove(output); os.remove(errfile); os.remove(reserved)
    if not ok then error(response,0) end
    return response
end

return M

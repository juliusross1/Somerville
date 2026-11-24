-- Document-local, contour-aware spacing of integrands and parenthesized math.
-- Requires ConTeXt LMTX. No installed ConTeXt files are changed.
--
-- Profiles are conservative horizontal bands around flattened glyph outlines.
-- Both sides include all their glyphs (including limits/scripts) and math rules.
-- This is an unbreakable, left-to-right mathematical construction, not a global
-- replacement for TeX's spacing. Graphics and transformed arbitrary content are
-- deliberately rejected instead of silently fitting against incomplete ink.

userdata = userdata or { }
local M = { }
userdata.bubbleintegrals = M

local floor, ceil, abs, min, max, sqrt = math.floor, math.ceil, math.abs,
    math.min, math.max, math.sqrt
local sp = 65536
local report = logs.reporter("bubble integrals")
local chars, parameters, shapes = fonts.hashes.characters,
    fonts.hashes.parameters, fonts.hashes.shapes
local nuts = nodes.nuts
local rulecodes = nodes.rulecodes
local noninkingrules = { [rulecodes.empty]=true, [rulecodes.strut]=true,
    [rulecodes.spacing]=true }
local supportedrules = { [rulecodes.normal]=true, [rulecodes.over]=true,
    [rulecodes.under]=true, [rulecodes.fraction]=true, [rulecodes.radical]=true }
local outlinecache = { }
local active

local function line(out, x1,y1,x2,y2)
    if x1 ~= x2 or y1 ~= y2 then
        out[#out+1] = { x1,y1,x2,y2 }
    end
end

local function flatness(x,y, x1,y1,x2,y2)
    local dx,dy = x2-x1,y2-y1
    local length2 = dx*dx+dy*dy
    if length2 == 0 then return sqrt((x-x1)^2+(y-y1)^2) end
    local t = max(0,min(1,((x-x1)*dx+(y-y1)*dy)/length2))
    return sqrt((x-x1-t*dx)^2+(y-y1-t*dy)^2)
end

local function cubic(out, x0,y0,x1,y1,x2,y2,x3,y3, depth)
    if depth >= 16 or max(flatness(x1,y1,x0,y0,x3,y3),
                         flatness(x2,y2,x0,y0,x3,y3)) <= .1 then
        line(out,x0,y0,x3,y3)
        return
    end
    local ax,ay,bx,by,cx,cy = (x0+x1)/2,(y0+y1)/2,
        (x1+x2)/2,(y1+y2)/2,(x2+x3)/2,(y2+y3)/2
    local dx,dy,ex,ey = (ax+bx)/2,(ay+by)/2,(bx+cx)/2,(by+cy)/2
    local fx,fy = (dx+ex)/2,(dy+ey)/2
    cubic(out,x0,y0,ax,ay,dx,dy,fx,fy,depth+1)
    cubic(out,fx,fy,ex,ey,cx,cy,x3,y3,depth+1)
end

local function outline(font, char)
    local cache = outlinecache[font]
    if not cache then cache = { }; outlinecache[font] = cache end
    if cache[char] then return cache[char] end
    local data = chars[font][char]
    local shapedata = shapes[font]
    local glyph = data and shapedata and shapedata.glyphs
        and shapedata.glyphs[data.index]
    if not glyph then
        error(string.format("bubble integrals: missing outline for font %s, U+%X",font,char))
    end
    local lines, x,y, firstx,firsty = { }, 0,0
    local function close()
        if firstx then line(lines,x,y,firstx,firsty) end
    end
    local function segment(op,a,b,c,d,e,f)
        if op == "m" then
            close(); x,y,firstx,firsty = a,b,a,b
        elseif op == "l" then
            line(lines,x,y,a,b); x,y = a,b
        elseif op == "q" then
            cubic(lines,x,y,x+2*(a-x)/3,y+2*(b-y)/3,
                c+2*(a-c)/3,d+2*(b-d)/3,c,d,0)
            x,y = c,d
        elseif op == "c" then
            cubic(lines,x,y,a,b,c,d,e,f,0); x,y = e,f
        else
            error("bubble integrals: unsupported outline command " .. tostring(op))
        end
    end
    if glyph.sequence then
        local seq,i = glyph.sequence,1
        local lengths = { m=3,l=3,q=5,c=7 }
        while i <= #seq do
            local op = seq[i]
            segment(op,seq[i+1],seq[i+2],seq[i+3],seq[i+4],seq[i+5],seq[i+6])
            i = i + assert(lengths[op])
        end
    elseif glyph.segments then
        for _,s in ipairs(glyph.segments) do
            segment(s[#s],s[1],s[2],s[3],s[4],s[5],s[6])
        end
    elseif data.width ~= 0 and (data.height or 0)+(data.depth or 0) > 0 then
        error("bubble integrals: glyph has metrics but no readable outline")
    end
    close()
    cache[char] = lines
    return lines
end

-- Intersect each edge with a whole band, not only its midpoint. This preserves
-- thin fraction bars and extrema that would otherwise fall between samples.
local function addline(p, x1,y1,x2,y2,approximation)
    p.lines[#p.lines+1] = {x1,y1,x2,y2}
    p.approximation = max(p.approximation or 0,approximation or 0)
    local pad,step = p.padding+(approximation or 0),p.step
    local low,high = min(y1,y2),max(y1,y2)
    local first,last = floor((low-pad)/step),floor((high+pad)/step)
    for k=first,last do
        local lo,hi = max(low,k*step-pad),min(high,(k+1)*step+pad)
        if lo <= hi then
            local a,b
            if y1 == y2 then a,b = min(x1,x2),max(x1,x2)
            else
                local u = x1+(x2-x1)*(lo-y1)/(y2-y1)
                local v = x1+(x2-x1)*(hi-y1)/(y2-y1)
                a,b = min(u,v),max(u,v)
            end
            a,b = a-pad,b+pad
            local band = p.bands[k]
            if band then band[1],band[2] = min(band[1],a),max(band[2],b)
            else p.bands[k] = {a,b} end
        end
    end
    p.xmin,p.xmax = min(p.xmin,x1,x2),max(p.xmax,x1,x2)
    p.ymin,p.ymax = min(p.ymin,y1,y2),max(p.ymax,y1,y2)
end

local function rectangle(x,y,w,h)
    if w > 0 and h > 0 then
        y = y-active.depth
        addline(active,x,y,x+w,y)
        addline(active,x+w,y,x+w,y+h)
        addline(active,x+w,y+h,x,y+h)
        addline(active,x,y+h,x,y)
        active.rules = active.rules+1
    end
end

local function character(current,x,y,direction,font,char,data,csx,csy,expansion,ssx,ssy,slant,weight)
    data = data or chars[font][char]
    if data.effect or fonts.hashes.identifiers[font].properties.effect
        or (weight and weight ~= 0) then
        error("bubble integrals: synthetic font effects are not supported")
    end
    local sx,sy
    if current then
        local s,a,b = nuts.getscales(current)
        sx,sy = s*a/1000000,s*b/1000000
        expansion = nuts.getexpansion(current)
    else
        sx,sy = (csx or 1)*(ssx or 1),(csy or 1)*(ssy or 1)
    end
    sx,sy = sx*(data.scale or 1),sy*(data.scale or 1)
    local factor = parameters[font].factor
    local xf,yf = factor*sx*(1+(expansion or 0)/1000000),factor*sy
    x = x + sx*(data.xoffset or 0)
    y = y-active.depth + sy*(data.yoffset or 0)
    -- The driver supplies a dimensionless synthetic shear; INSL is already
    -- present in the instantiated outline and must not be applied again.
    local shear = slant or 0
    local approximation = .1*max(abs(xf)+abs(yf*shear),abs(yf))
    for _,l in ipairs(outline(font,char)) do
        addline(active,x+l[1]*xf+l[2]*yf*shear,y+l[2]*yf,
                       x+l[3]*xf+l[4]*yf*shear,y+l[4]*yf,approximation)
    end
    active.glyphs = active.glyphs+1
    active.fonts[font] = true
end

local function unsupported()
    error("bubble integrals: only left-to-right math glyphs and rules are supported; embedded graphics, transformations, and late Lua are not")
end

local function preflight(head)
    for n in node.traverse(head) do
        local id = n.id
        if id == nodes.nodecodes.hlist or id == nodes.nodecodes.vlist then
            if (n.orientation or 0) ~= 0 or (n.direction or 0) ~= 0 then unsupported() end
            if n.list then preflight(n.list) end
        elseif id == nodes.nodecodes.whatsit then
            -- Do not run late Lua or PDF transformations as a side effect of
            -- measuring a box with the general ConTeXt driver.
            unsupported()
        elseif id == nodes.nodecodes.rule then
            if not noninkingrules[n.subtype] and not supportedrules[n.subtype] then
                unsupported()
            end
        end
    end
end

drivers.install {
    name = "bubbleintegrals",
    actions = { initialize=function() end, finalize=function() end },
    flushers = {
        character = character,
        rule = function(current,x,y,d,w,h,subtype)
            if not noninkingrules[subtype] then rectangle(x,y,w,h) end
        end,
        simplerule = function(x,y,d,w,h) rectangle(x,y,w,h) end,
        specialrule = function(x,y,d,w,h,depth) rectangle(x,y-depth,w,h+depth) end,
        literal = unsupported, latelua = unsupported,
        startmatrix = unsupported, stopmatrix = unsupported,
        setmatrix = unsupported, pushorientation = unsupported,
        poporientation = unsupported,
    },
}

local function profile(boxnumber,step,padding)
    local box = assert(tex.getbox(boxnumber),"bubble integrals: missing box")
    if (box.direction or 0) ~= 0 or (box.orientation or 0) ~= 0 then unsupported() end
    if box.list then preflight(box.list) end
    -- Traverse a disposable copy, keeping the actual output box untouched.
    local copy = nodes.copy(box)
    local p = {bands={ },lines={ },fonts={ },glyphs=0,rules=0,
        step=step,padding=padding,depth=box.depth,width=box.width,
        height=box.height,xmin=math.huge,xmax=-math.huge,
        ymin=math.huge,ymax=-math.huge}
    active = p
    drivers.converters.lmtx(drivers.instances.bubbleintegrals,copy,"box",1)
    nodes.flushlist(copy)
    active = nil
    return p
end

local function separation(left,right,clearance)
    local result,critical = -math.huge
    for k,a in pairs(left.bands) do
        local b = right.bands[k]
        if b then
            local distance = a[2]-b[1]+clearance
            if distance > result then result,critical = distance,k end
        end
    end
    -- No shared occupied band (for example, a completely raised integrand):
    -- retain a sensible positive origin rather than an unconstrained overlap.
    if result == -math.huge then return left.width+clearance,nil end
    return max(0,result),critical
end

function M.fit(leftnumber,rightnumber,clearance,padding,step,method,tracing,ordinarygap,strength)
    assert(step > 0 and clearance >= 0 and padding >= 0,
        "bubble integrals: step must be positive, clearance and padding nonnegative")
    strength = strength or 1
    assert(strength >= 0 and strength <= 1,"bubble integrals: strength must be between 0 and 1")
    local left,right = profile(leftnumber,step,padding),profile(rightnumber,step,padding)
    local origin,critical = separation(left,right,clearance)
    local bboxorigin = left.xmax-right.xmin+clearance+2*padding
        +(left.approximation or 0)+(right.approximation or 0)
    if left.glyphs+left.rules == 0 or right.glyphs+right.rules == 0 then
        origin,bboxorigin = left.width+clearance,left.width+clearance
    end
    if method == "bbox" then origin = max(0,bboxorigin)
    elseif method ~= "profile" then error("bubble integrals: method must be profile or bbox") end
    local targetorigin = origin
    local ordinaryorigin = left.width+(ordinarygap or 0)
    origin = ordinaryorigin+strength*(targetorigin-ordinaryorigin)
    local gap = ceil(origin-left.width)
    -- Positive gaps remain possible: profiles can also expose an ink collision.
    tex.dimen.bubbleintegralgap = gap
    M.last = {left=left,right=right,origin=left.width+gap,gap=gap,
        clearance=clearance,padding=padding,step=step,critical=critical,
        bboxorigin=bboxorigin,method=method,strength=strength,
        targetorigin=targetorigin,ordinaryorigin=ordinaryorigin}
    M.verify()
    M.history = M.history or { }
    M.history[#M.history+1] = {gap=gap,origin=left.width+gap,
        leftwidth=left.width,rightwidth=right.width,
        bboxorigin=bboxorigin,method=method,strength=strength,
        targetorigin=targetorigin,ordinaryorigin=ordinaryorigin}
    if tracing == "yes" then
        report("%s strength %.2f: gap %.3fpt (ordinary %.3fpt); %i+%i glyphs, %i rules",
            method,strength,gap/sp,(ordinarygap or 0)/sp,
            left.glyphs,right.glyphs,left.rules+right.rules)
    end
    return M.last
end

function M.verify()
    local t = assert(M.last,"bubble integrals: no measurement to verify")
    if t.strength < 1 then
        assert(abs(t.origin-(t.ordinaryorigin+t.strength*(t.targetorigin-t.ordinaryorigin))) <= 1,
            "bubble integrals: spacing interpolation failed")
        return true
    end
    for k,a in pairs(t.left.bands) do
        local b = t.right.bands[k]
        if b then
            assert(t.origin+b[1]-a[2] >= t.clearance-1,
                "bubble integrals: calculated spacing violates the requested clearance")
        end
    end
    return true
end

-- A standalone diagram of the latest fit: actual ink in grey, facing padded
-- profiles in red/blue, mathematical baselines in grey. Coordinates use TeX pt.
function M.trace()
    local t = assert(M.last,"bubble integrals: typeset an integral before showing its profiles")
    context.startMPcode()
    context("drawoptions(withpen pencircle scaled .18pt withcolor (.7,.7,.7));")
    for index,p in ipairs({t.left,t.right}) do
        local offset = index == 1 and 0 or t.origin
        for _,l in ipairs(p.lines) do
            context(string.format("draw (%.5fpt,%.5fpt)--(%.5fpt,%.5fpt);",
                (offset+l[1])/sp,l[2]/sp,(offset+l[3])/sp,l[4]/sp))
        end
        context(index == 1 and "drawoptions(withpen pencircle scaled .45pt withcolor (.8,.15,.1));"
            or "drawoptions(withpen pencircle scaled .45pt withcolor (.1,.3,.8));")
        for k,band in pairs(p.bands) do
            local x = (offset+band[index == 1 and 2 or 1])/sp
            context(string.format("draw (%.5fpt,%.5fpt)--(%.5fpt,%.5fpt);",
                x,k*p.step/sp,x,(k+1)*p.step/sp))
        end
        context("drawoptions(withpen pencircle scaled .18pt withcolor (.7,.7,.7));")
    end
    context.stopMPcode()
end

-- Start from a native \left(...\right) formula. Extract the actual finished
-- fence lists rather than guessing a size or reconstructing extensible glyphs.
-- Native edge glue stays in the body, so both ordinary join kerns are zero.
function M.splitparentheses(nativeboxnumber,leftregister,bodyregister,rightregister)
    local native = assert(tex.getbox(nativeboxnumber),"missing native parenthesis box")
    local codes = nodes.nodecodes
    local function content(n)
        local id = n.id
        return id ~= codes.math and id ~= codes.glue and id ~= codes.kern
            and id ~= codes.penalty and id ~= codes.dir and id ~= codes.whatsit
    end
    local first,last
    for n in node.traverse(native.list) do
        if content(n) then first=first or n; last=n end
    end
    assert(first and last and first ~= last,"cannot identify native parentheses")
    assert(first.id == codes.hlist or first.id == codes.vlist,
        "native left parenthesis is not a list")
    assert(last.id == codes.hlist or last.id == codes.vlist,
        "native right parenthesis is not a list")
    local heads,tails,phase = { },{ },1
    for n in node.traverse(native.list) do
        if n == last then phase=3 end
        local c = nodes.copy(n)
        c.next,c.prev=nil,nil
        if tails[phase] then tails[phase].next=c; c.prev=tails[phase]
        else heads[phase]=c end
        tails[phase]=c
        if n == first then phase=2 end
    end
    local left,body,right = nodes.hpack(heads[1]),nodes.hpack(heads[2]),nodes.hpack(heads[3])
    assert(left.width+body.width+right.width == native.width,
        "splitting native parentheses changed the width")
    assert(max(left.height,body.height,right.height)==native.height
        and max(left.depth,body.depth,right.depth)==native.depth,
        "splitting native parentheses changed vertical dimensions")
    tex.setbox(leftregister,left)
    tex.setbox(bodyregister,body)
    tex.setbox(rightregister,right)
end

function M.fitparentheses(leftnumber,bodynumber,rightnumber,clearance,padding,step,method,tracing,strength)
    assert(step > 0 and clearance >= 0 and padding >= 0,
        "bubble parentheses: step must be positive, clearance and padding nonnegative")
    assert(strength >= 0 and strength <= 1,
        "bubble parentheses: strength must be between 0 and 1")
    assert(method == "profile" or method == "bbox",
        "bubble parentheses: method must be profile or bbox")
    local left = profile(leftnumber,step,padding)
    local body = profile(bodynumber,step,padding)
    local right = profile(rightnumber,step,padding)
    local ordinarybody = left.width
    local ordinaryright = left.width+body.width
    local targetbody,targetright
    if body.glyphs+body.rules == 0 then
        -- Invisible struts still control native delimiter size. They do not
        -- acquire a fictitious ink profile or lose their original spacing.
        targetbody,targetright = ordinarybody,ordinaryright
    elseif method == "bbox" then
        targetbody = max(0,left.xmax-body.xmin+clearance+2*padding
            +(left.approximation or 0)+(body.approximation or 0))
        targetright = targetbody+max(0,body.xmax-right.xmin+clearance+2*padding
            +(body.approximation or 0)+(right.approximation or 0))
    else
        targetbody = separation(left,body,clearance)
        targetright = targetbody+separation(body,right,clearance)
    end
    -- Fitting both sides independently must not make the parentheses collide
    -- with one another when the occupied body is very narrow or absent.
    targetright = max(targetright,separation(left,right,clearance))
    local bodyorigin = ceil(ordinarybody+strength*(targetbody-ordinarybody))
    local rightorigin = ceil(ordinaryright+strength*(targetright-ordinaryright))
    -- Rounding the two absolute positions independently may shrink a clearance
    -- by less than one scaled point; the verifier allows exactly that bound.
    local leftgap = bodyorigin-left.width
    local rightgap = rightorigin-bodyorigin-body.width
    tex.dimen.bubbleparenthesisleftgap = leftgap
    tex.dimen.bubbleparenthesisrightgap = rightgap
    M.lastparentheses = {left=left,body=body,right=right,
        bodyorigin=bodyorigin,rightorigin=rightorigin,
        ordinarybody=ordinarybody,ordinaryright=ordinaryright,
        targetbody=targetbody,targetright=targetright,
        leftgap=leftgap,rightgap=rightgap,strength=strength,
        clearance=clearance,padding=padding,step=step,method=method}
    M.verifyparentheses()
    M.parenthesishistory = M.parenthesishistory or { }
    M.parenthesishistory[#M.parenthesishistory+1] = {
        bodyorigin=bodyorigin,rightorigin=rightorigin,
        ordinarybody=ordinarybody,ordinaryright=ordinaryright,
        targetbody=targetbody,targetright=targetright,
        leftgap=leftgap,rightgap=rightgap,strength=strength,
        bodywidth=body.width,leftwidth=left.width,rightwidth=right.width,
        bodyglyphs=body.glyphs,bodyrules=body.rules,
    }
    if tracing == "yes" then
        report("parentheses %s strength %.2f: left gap %.3fpt, right gap %.3fpt; %i body glyphs, %i rules",
            method,strength,leftgap/sp,rightgap/sp,body.glyphs,body.rules)
    end
end

function M.verifyparentheses()
    local t = assert(M.lastparentheses,"bubble parentheses: no measurement to verify")
    if t.strength < 1 then
        assert(abs(t.bodyorigin-(t.ordinarybody+t.strength*(t.targetbody-t.ordinarybody))) <= 1
            and abs(t.rightorigin-(t.ordinaryright+t.strength*(t.targetright-t.ordinaryright))) <= 1,
            "bubble parentheses: spacing interpolation failed")
    else
        local function check(a,b,distance)
            for k,band in pairs(a.bands) do
                local other = b.bands[k]
                if other then
                    assert(distance+other[1]-band[2] >= t.clearance-1,
                        "bubble parentheses: fitted shapes violate the requested clearance")
                end
            end
        end
        check(t.left,t.body,t.bodyorigin)
        check(t.body,t.right,t.rightorigin-t.bodyorigin)
        check(t.left,t.right,t.rightorigin)
    end
    return true
end

function M.traceparentheses()
    local t = assert(M.lastparentheses,"typeset fitted parentheses before showing their profiles")
    context.startMPcode()
    for _,item in ipairs({{t.left,0},{t.body,t.bodyorigin},{t.right,t.rightorigin}}) do
        local p,x = item[1],item[2]
        context("drawoptions(withpen pencircle scaled .18pt withcolor (.7,.7,.7));")
        for _,l in ipairs(p.lines) do
            context(string.format("draw (%.5fpt,%.5fpt)--(%.5fpt,%.5fpt);",
                (x+l[1])/sp,l[2]/sp,(x+l[3])/sp,l[4]/sp))
        end
    end
    local function boundary(p,offset,side,color)
        context("drawoptions(withpen pencircle scaled .45pt withcolor "..color..");")
        for k,band in pairs(p.bands) do
            local x = (offset+band[side])/sp
            context(string.format("draw (%.5fpt,%.5fpt)--(%.5fpt,%.5fpt);",
                x,k*p.step/sp,x,(k+1)*p.step/sp))
        end
    end
    boundary(t.left,0,2,"(.8,.15,.1)")
    boundary(t.body,t.bodyorigin,1,"(.1,.3,.8)")
    boundary(t.body,t.bodyorigin,2,"(.1,.3,.8)")
    boundary(t.right,t.rightorigin,1,"(.8,.15,.1)")
    context.stopMPcode()
end

function M.parenthesismetrics()
    local t = assert(M.lastparentheses,"typeset fitted parentheses before showing their metrics")
    context(string.format("{\\tfxx Last pair: left join %+.3fpt; right join %+.3fpt.}",
        t.leftgap/sp,t.rightgap/sp))
end

function M.selftest()
    -- Equal bounding boxes; different left-facing shapes must fit differently.
    local left={width=10,bands={[0]={0,2},[1]={0,10}}}
    local a={bands={[0]={0,10},[1]={8,10}}}
    local b={bands={[0]={8,10},[1]={0,10}}}
    assert(separation(left,a,1)==3 and separation(left,b,1)==11,
        "bubble integrals: shape-sensitive fit failed")
    local thin={bands={ },lines={ },step=10,padding=0,
        xmin=math.huge,xmax=-math.huge,ymin=math.huge,ymax=-math.huge}
    addline(thin,0,1,20,1)
    assert(thin.bands[0] and thin.bands[0][2]==20,
        "bubble integrals: thin rule disappeared between samples")
    report("geometry self-tests passed (equal boxes/different shapes, sub-band rules)")
end

return M

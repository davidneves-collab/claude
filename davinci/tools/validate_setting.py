import sys,glob,lupa
L=lupa.LuaRuntime()
chk=L.eval('''function(src)
  local stub; stub=setmetatable({}, {__index=function(t,k) return stub end, __call=function(_,a) if a==nil then return setmetatable({}, {__call=function(_,b) return b end}) end return a end})
  local env=setmetatable({}, {__index=function(t,k) return stub end})
  local f,err=load("return "..src, "s", "t", env)
  if not f then return "SYNTAX: "..err end
  local ok,res=pcall(f); if not ok then return "RUN: "..tostring(res) end
  local n=0; for k,v in pairs(res.Tools) do for kk,vv in pairs(v.Tools) do n=n+1 end end
  return "ok tools="..n
end''')
for f in sorted(glob.glob(sys.argv[1]+"/*.setting")):
    print(chk(open(f).read()), f.rsplit("/",1)[1])

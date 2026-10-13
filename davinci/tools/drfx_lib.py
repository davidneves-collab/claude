import sys,os,re,json,zipfile
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from luaparse import top_entries

VENDOR="20 Text Animations"

def layer_info(body):
    ents=top_entries(body); names=[n for n,_,_ in ents]
    out=None; keep=[]; txt_src=None; sample=""
    for n,t,x in ents:
        if t=="MediaOut": out=re.search(r'Input = Input \{ SourceOp = "(\w+)"',x).group(1); continue
        keep.append((n,t,x))
    tmpl=[(n,x) for n,t,x in keep if t=="TextPlus"]
    if tmpl:
        tn,tx=[(n,x) for n,x in tmpl if n=="Template"][0] if any(n=="Template" for n,_ in tmpl) else tmpl[0]
        m=re.search(r'StyledText = Input \{ SourceOp = "(\w+)"',tx)
        if m:
            txt_src=(m.group(1),"Text")
            fx=[x for n,_,x in keep if n==m.group(1)][0]
            mm=re.search(r'Text = Input \{ Value = (?:StyledText \{ Value = )?"([^"]*)"',fx); sample=mm.group(1) if mm else ""
        else:
            txt_src=(tn,"StyledText")
            mm=re.search(r'StyledText = Input \{ Value = "([^"]*)"',tx); sample=mm.group(1) if mm else ""
    else: tn=None
    return keep,names,out,txt_src,tn,sample
def prefix(keep,names,p):
    nameset=set(names); res=[]
    def ren(n): return p+n if n in nameset else n
    for n,t,x in keep:
        x=re.sub(r'^'+re.escape(n)+r'(\s*=)', p+n+r'\1', x)
        x=re.sub(r'SourceOp = "(\w+)"', lambda m:'SourceOp = "%s"'%ren(m.group(1)), x)
        def fixexpr(m):
            s=re.sub(r'\b(\w+)\b', lambda k: ren(k.group(1)) if k.group(1) in nameset else k.group(1), m.group(2))
            return m.group(1)+s+'"'
        x=re.sub(r'(Expression = ")((?:[^"\\]|\\.)*)"', fixexpr, x)
        res.append(x)
    return res
def macro_text(macro, inputs, out, tools):
    return ("{\n\tTools = ordered() {\n\t\t%s = MacroOperator {\n\t\t\tCtrlWZoom = false,\n"
      "\t\t\tInputs = ordered() {\n%s\n\t\t\t},\n"
      "\t\t\tOutputs = {\n\t\t\t\tMainOutput1 = InstanceOutput { SourceOp = \"%s\", Source = \"Output\", }\n\t\t\t},\n"
      "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 }, },\n"
      "\t\t\tTools = ordered() {\n%s\n\t\t\t},\n\t\t},\n\t},\n\tActiveTool = \"%s\"\n}\n") % (
        macro, ",\n".join("\t\t\t\t"+x for x in inputs), out, ",\n".join("\t\t\t\t"+x for x in tools), macro)
def inputs_for(p, txt_src, tn, k, label):
    ins=[]
    if txt_src: ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{txt_src[0]}", Source = "{txt_src[1]}", Name = "{label}", }}'); k+=1
    if tn:
        g=k
        ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{tn}", Source = "Font", Name = "{label} - Font", ControlGroup = {g}, }}'); k+=1
        ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{tn}", Source = "Style", ControlGroup = {g}, }}'); k+=1
        ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{tn}", Source = "Size", Name = "{label} - Size", }}'); k+=1
        g=k
        ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{tn}", Source = "Red1", Name = "{label} - Color", ControlGroup = {g}, }}'); k+=1
        ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{tn}", Source = "Green1", ControlGroup = {g}, }}'); k+=1
        ins.append(f'Input{k} = InstanceInput {{ SourceOp = "{p}{tn}", Source = "Blue1", ControlGroup = {g}, }}'); k+=1
    return ins,k

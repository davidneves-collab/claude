import re
def skip_ws(s,i):
    while i < len(s) and s[i] in " \t\r\n,": i+=1
    return i
def match_brace(s,i):
    # s[i]=='{'; return index after matching '}'
    depth=0; n=len(s)
    while i<n:
        c=s[i]
        if c=='"':
            i+=1
            while s[i]!='"':
                if s[i]=='\\': i+=1
                i+=1
        elif c=='[' and s[i:i+2] in ('[[','[='):
            m=re.match(r'\[(=*)\[', s[i:]); close=']'+m.group(1)+']'
            i=s.index(close,i)+len(close)-1
        elif c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0: return i+1
        i+=1
    raise ValueError("unbalanced")
def top_entries(body):
    """body = '{ A = T { ... }, B = ... }' -> list of (name, type, text)"""
    s=body.strip(); assert s[0]=='{'
    end=match_brace(s,0); inner=s[1:end-1]
    out=[]; i=0
    while True:
        i=skip_ws(inner,i)
        if i>=len(inner): break
        m=re.compile(r'(\[?"?[\w.]+"?\]?)\s*=\s*([\w.]*)\s*').match(inner,i)
        name,typ=m.group(1),m.group(2)
        j=m.end(); assert inner[j]=='{', inner[i:i+80]
        k=match_brace(inner,j)
        out.append((name,typ,inner[i:k])); i=k
    return out

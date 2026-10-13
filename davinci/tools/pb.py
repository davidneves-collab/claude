import struct
def varint(b,i):
    r=s=0
    while True:
        x=b[i]; i+=1; r|=(x&0x7f)<<s; s+=7
        if x<0x80: return r,i
def dec(b):
    i=0; out=[]
    while i<len(b):
        key,i=varint(b,i); f,w=key>>3,key&7
        if w==0: v,i=varint(b,i)
        elif w==1: v=('d',struct.unpack("<d",b[i:i+8])[0]); i+=8
        elif w==5: v=('f',struct.unpack("<f",b[i:i+4])[0]); i+=4
        elif w==2:
            l,i=varint(b,i); v=b[i:i+l]; i+=l
        else: raise ValueError(w)
        if f==0: raise ValueError
        out.append((f,v))
    return out
def tryrec(v):
    if isinstance(v,bytes):
        try: return [(f,tryrec(x)) for f,x in dec(v)]
        except Exception: return v
    return v

"""Codec + builders for DaVinci Resolve PowerGrade (.drx) node tab 1 ("corrector") and tab 9 ("key").

Wire format (validated byte-identically on every tab-1/tab-9 entry of the 6 original + 6 FREE .drx files):

  node.field9.field1  (one per tab, sorted by tab id)  = TabEntry
  TabEntry  = { 1: tabId (varint), 3: 1 (varint), 6: { 2: { 1: 1 (varint), 3: Param* } } }
  Param     = { 1: paramId (varint), 2: Value }          Params are sorted by paramId (unsigned).
  Value     = oneof (always serialised, even 0 / 0.0):
                1: float32 (wire 5)        e.g. pivot, contrast, key gain
                2: varint                  e.g. curve flags, LUT kind (=6)
                5: string                  LUT path (relative to the LUT folder)
                8: Curve                   custom curves and hue-vs curves
               14: Color Warper mesh  16: HDR zone list  24: Color Slice vector list  (kept raw)
  Curve     = { 1: Point* }    Point = { 1: x float32, 2: y float32 }   (proto3: 0.0 coords are omitted,
                                                                         so the point (0,0) is an EMPTY message)
  Custom-curve point list = [(-1024,-1024) sentinel] + [(0, y0) ... (1023, yN)]  in 10-bit code values.

Param ids look like  (flag<<31) | (group<<20) | index ; tab 1 -> group 0x060, tab 9 -> group 0x0C3.

Confidence labels on each builder are documented in PARAMS below.
"""
import struct, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import powergrade_build as B
from pb import varint

enc_varint = B.enc_varint


def key(f, w):
    return enc_varint((f << 3) | w)


def ld(f, payload):
    return key(f, 2) + enc_varint(len(payload)) + payload


def vi(f, n):
    return key(f, 0) + enc_varint(n)


def f32(f, x):
    return key(f, 5) + struct.pack("<f", x)


# ---------------------------------------------------------------- param ids (tab 1 unless noted)
P = dict(
    # --- custom curves (HIGH: structure; MEDIUM: channel identity R,G,B,Y) ---
    CURVE_R=0x86000506, CURVE_G=0x86000507, CURVE_B=0x86000508, CURVE_Y=0x86000509,
    # per-channel custom-curve flags (pairing flag<->curve HIGH, meaning of the int MEDIUM/LOW)
    CFLAG_Y=0x860000BB, CFLAG_R=0x860000BD, CFLAG_G=0x860000BE, CFLAG_B=0x860000BF,
    # --- hue-vs curves (MEDIUM) ---
    HUE_VS_HUE=0x86000400, HUE_VS_SAT=0x86000401, HUE_VS_LUM=0x86000402,
    HFLAG_HUE=0x860000B7, HFLAG_SAT=0x860000B8, HFLAG_LUM=0x860000B9, HCURVES_ON=0x860000CF,
    # --- LUT (HIGH) ---
    LUT_KIND=0x860000A0, LUT_PATH=0x860000A1,
    # --- primaries / log (see confidence in report) ---
    PIVOT=0x860000C0,                       # MEDIUM-HIGH (0.336 = DaVinci Intermediate mid-grey)
    CONTRAST=0x860000C1,                    # MEDIUM
    SHADOW_RGB=(0x860000C2, 0x860000C3, 0x860000C4),    # LOW-MEDIUM: Log-wheel Shadow (or Lift) R,G,B
    MIDTONE_RGB=(0x860000C5, 0x860000C6, 0x860000C7),   # LOW: Log-wheel Midtone (or Gamma) R,G,B
    GAIN_4=(0x0600001D, 0x0600001E, 0x0600001F, 0x06000020),  # MEDIUM: Gain (Y,R,G,B order LOW)
    OFFSET_RGB=(0x0600007D, 0x0600007E, 0x0600007F),    # LOW-MEDIUM: Offset R,G,B
    SATURATION=0x06000005,                  # LOW-MEDIUM: Primaries Saturation? (only node 80 itsjohan = 1.224)
    BLUR_RADIUS_RGB=(0x86000052, 0x86000053, 0x86000054),  # HIGH-ish: Blur radius R,G,B, stored as UI-0.5
    # --- HDR palette (MEDIUM) ---
    HDR_CONTRAST=0x86000301, HDR_ZONES=0x86000305, HDR_MODE=0x86000309,
    # --- saturation used by the 3 'SAT' nodes (HIGH that it is a saturation control; palette = Color Slice
    #     global Sat (MEDIUM-LOW) or Primaries Sat), Color Slice 7-vector list (MEDIUM-LOW) ---
    SLICE_SAT=0x86000602, SLICE_VECTORS=0x86000606,
    UNKNOWN_TONECURVE_0B=0x8600000B,        # float 0.0 in '2383 Tone Curve' only (Lum Mix? LOW)
)
KEY_OUTPUT_GAIN = 0x0C30001D   # tab 9 (Key palette) - MEDIUM-HIGH: node strength / opacity, default 1.0


# ---------------------------------------------------------------- values
def v_float(x):
    return f32(1, x)


def v_int(n):
    return vi(2, n)


def v_str(s):
    return ld(5, s.encode() if isinstance(s, str) else s)


def enc_point(x, y):
    """proto3 point: a coordinate equal to 0.0 is omitted (so (0,0) -> empty message)."""
    b = b""
    if struct.pack("<f", x) != b"\x00\x00\x00\x00":
        b += f32(1, x)
    if struct.pack("<f", y) != b"\x00\x00\x00\x00":
        b += f32(2, y)
    return ld(1, b)


def v_curve_raw(points):
    """points: list of (x, y) already in the stored coordinate space (code values / hue space)."""
    return ld(8, b"".join(enc_point(x, y) for x, y in points))


SENTINEL = (-1024.0, -1024.0)


def custom_curve_points(points01):
    """0..1 points -> stored list: sentinel + code values 0..1023.
    Endpoints x=0 and x=1 are added (as identity) if missing, as DaVinci always stores them."""
    pts = sorted((float(x), float(y)) for x, y in points01)
    if not pts or pts[0][0] > 0.0:
        pts.insert(0, (0.0, 0.0))
    if pts[-1][0] < 1.0:
        pts.append((1.0, 1.0))
    out = [SENTINEL]
    for x, y in pts:
        x = min(max(x, 0.0), 1.0); y = min(max(y, 0.0), 1.0)
        out.append((x * 1023.0, y * 1023.0))
    return out


def v_custom_curve(points01):
    return v_curve_raw(custom_curve_points(points01))


# ---------------------------------------------------------------- params / tab entries
def enc_param(pid, value_bytes):
    return ld(3, vi(1, pid) + ld(2, value_bytes))


def make_tab(tab_id, params):
    """params: dict or list of (paramId, valueBytes). Sorted by id like DaVinci does."""
    items = sorted(params.items() if isinstance(params, dict) else params, key=lambda t: t[0])
    body = vi(1, 1) + b"".join(enc_param(pid, vb) for pid, vb in items)
    return vi(1, tab_id) + vi(3, 1) + ld(6, ld(2, body))


def parse_tab(entry):
    """TabEntry bytes -> (tab_id, [(paramId, valueBytes)]). Raises if the header is unexpected."""
    fs = B.fields(entry)
    assert [f[0] for f in fs] == [1, 3, 6], [f[0] for f in fs]
    tab_id = varint(fs[0][3], 0)[0]
    assert varint(fs[1][3], 0)[0] == 1
    f6 = B.fields(fs[2][3]); assert [f[0] for f in f6] == [2]
    f62 = B.fields(f6[0][3]); assert f62[0][0] == 1 and varint(f62[0][3], 0)[0] == 1
    params = []
    for f, w, ks, p in f62[1:]:
        assert f == 3
        pf = B.fields(p); assert [x[0] for x in pf] == [1, 2]
        params.append((varint(pf[0][3], 0)[0], pf[1][3]))
    return tab_id, params


def decode_value(vb):
    fs = B.fields(vb); assert len(fs) == 1, fs
    f, w, ks, p = fs[0]
    if f == 1 and w == 5: return ("float", struct.unpack("<f", p)[0])
    if f == 2 and w == 0: return ("int", varint(p, 0)[0])
    if f == 5 and w == 2: return ("str", p.decode("utf-8"))
    if f == 8 and w == 2:
        pts = []
        for ff, ww, kk, q in B.fields(p):
            assert ff == 1
            d = {a: struct.unpack("<f", c)[0] for a, wa, ka, c in B.fields(q)}
            pts.append((d.get(1, 0.0), d.get(2, 0.0)))
        return ("curve", pts)
    return ("raw", vb)


def encode_value(kind, v):
    if kind == "float": return v_float(v)
    if kind == "int": return v_int(v)
    if kind == "str": return v_str(v)
    if kind == "curve": return v_curve_raw(v)
    return v


# ---------------------------------------------------------------- high-level builders
FLAG_GANGED = 2   # value seen on all four flags when the 4 curves are identical (HERO/node 80, Resolve 21)
FLAG_EDITED = 4   # value seen on unganged, individually edited channels (SRM 44, F-01)


def curve_params(y=None, r=None, g=None, b=None, ganged=None, flags=None):
    """Custom-curve params for a tab-1 entry.
    - ganged=[pts]  : the same curve on Y,R,G,B, all flags 2  (exactly what Resolve 21 wrote for HERO/node 80)
    - y/r/g/b=[pts] : only the given channels are written; each gets flag 4 (like SRM node 44);
                      channels not given are omitted (= identity), as DaVinci does.
    Points are (x, y) in 0..1. flags={'Y':2,...} overrides."""
    out = {}
    if ganged is not None:
        cv = v_custom_curve(ganged)
        for ch in "RGBY":
            out[P["CURVE_" + ch]] = cv
            out[P["CFLAG_" + ch]] = v_int(FLAG_GANGED)
    else:
        for ch, pts in (("Y", y), ("R", r), ("G", g), ("B", b)):
            if pts is None: continue
            out[P["CURVE_" + ch]] = v_custom_curve(pts)
            out[P["CFLAG_" + ch]] = v_int(FLAG_EDITED)
    for ch, n in (flags or {}).items():
        out[P["CFLAG_" + ch]] = v_int(n)
    return out


def make_curve_tab(points=None, y=None, r=None, g=None, b=None, flags=None, extra=None):
    """Tab-1 entry holding custom curves. `points` -> ganged curve on all channels.
    extra: dict paramId -> valueBytes merged in (e.g. pivot/contrast from primaries_params)."""
    prm = curve_params(y=y, r=r, g=g, b=b, ganged=points, flags=flags)
    if extra: prm.update(extra)
    return make_tab(1, prm)


def primaries_params(pivot=None, contrast=None, saturation=None, gain=None, offset=None,
                     shadow=None, midtone=None):
    """Scalar primary-type params (see confidence labels). gain/offset/shadow/midtone are
    master values written equally to every channel (order-independent, like the real WB/Blacks nodes).
    gain: absolute (1.0 neutral). offset/shadow/midtone: 0.0 neutral."""
    out = {}
    if pivot is not None: out[P["PIVOT"]] = v_float(pivot)
    if contrast is not None: out[P["CONTRAST"]] = v_float(contrast)
    if saturation is not None: out[P["SATURATION"]] = v_float(saturation)
    if gain is not None:
        for pid in P["GAIN_4"]: out[pid] = v_float(gain)
    if offset is not None:
        for pid in P["OFFSET_RGB"]: out[pid] = v_float(offset)
    if shadow is not None:
        for pid in P["SHADOW_RGB"]: out[pid] = v_float(shadow)
    if midtone is not None:
        for pid in P["MIDTONE_RGB"]: out[pid] = v_float(midtone)
    return out


def lut_params(path):
    """LUT in a node (HIGH). path relative to Resolve's LUT folder, '/' separators on macOS."""
    return {P["LUT_KIND"]: v_int(6), P["LUT_PATH"]: v_str(path)}


def make_key_tab(output_gain):
    """Tab-9 entry: Key Output Gain (node strength). 1.0 = full, 0.7 = 70 % etc."""
    return make_tab(9, {KEY_OUTPUT_GAIN: v_float(output_gain)})


# ---------------------------------------------------------------- node surgery
def set_tab(node, entry):
    """Insert/replace a tab entry inside node.field9 keeping DaVinci's order (tab ids ascending,
    then the packed field 2). Returns new node bytes."""
    tid = parse_tab(entry)[0]
    nf = B.fields(node)
    for x in nf:
        if x[0] != 9: continue
        t = B.fields(x[3])
        ents = [e for e in t if e[0] == 1]
        rest = [e for e in t if e[0] != 1]
        ents = [e for e in ents if B.getv(e[3], 1) != tid]
        ents.append([1, 2, key(1, 2), entry])
        ents.sort(key=lambda e: B.getv(e[3], 1))
        x[3] = B.build(ents + rest)
        return B.build(nf)
    raise ValueError("node has no field 9")


def get_tab(node, tid):
    t = B.getv(node, 9)
    if not isinstance(t, bytes): return None
    for f, w, ks, p in B.fields(t):
        if f == 1 and B.getv(p, 1) == tid: return p
    return None


# ---------------------------------------------------------------- HDR palette (itsjohan, Resolve 21)
HDR_MODE_VALUE = 4   # 0x86000309 is 4 in every node that uses the HDR palette (meaning unknown, copy it)


def v_hdr_zones(zones):
    """zones: list of (name, exp, sat) in the order to store, e.g. [('Global', 0.0, 1.05)].
    Zone msg = {1: name, 2: exposure float (omitted when 0), 7: saturation float}."""
    out = b""
    for nm, exp, sat in zones:
        z = ld(1, nm.encode())
        if struct.pack("<f", exp) != b"\x00\x00\x00\x00": z += f32(2, exp)
        z += f32(7, sat)
        out += ld(1, z)
    return ld(16, out)


def hdr_params(zones=None, contrast=None):
    """HDR palette params. zones=[('Global', exp, sat), ('Shadow', exp, 1.0), ...]; contrast = global HDR contrast."""
    out = {P["HDR_MODE"]: v_int(HDR_MODE_VALUE)}
    if contrast is not None: out[P["HDR_CONTRAST"]] = v_float(contrast)
    if zones: out[P["HDR_ZONES"]] = v_hdr_zones(zones)
    return out


def sharpen_params(delta=-0.04):
    """Blur-palette radius R,G,B stored as (UI radius - 0.5): -0.04 == UI 0.46 == mild sharpen."""
    return {pid: v_float(delta) for pid in P["BLUR_RADIUS_RGB"]}


def slice_saturation_params(sat):
    """0x86000602: the only param of the three 'SAT' nodes (F-01/02/03, value 1.2)."""
    return {P["SLICE_SAT"]: v_float(sat)}

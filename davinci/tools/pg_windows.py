"""Window / tool-tab helpers for DaVinci Resolve PowerGrade (.drx) node protobufs.

Byte-exact encoder/decoder for the per-node "tool tabs" (node field 9) and for the
node-level enable flag (node field 10, param 0xC0000001). Validated by re-encoding every
tab entry of the 12 reference .drx files byte-identically (see test_pg_windows.py).

Layout (node field 9):
    repeated 1: TabEntry  = {1: tabId, 3: 1, 6: {2: {1: 1, 3: [Param ...]}}}
             2: packed varints [3, 4, 5, 6, 18]   (window list: Linear, Circle, Polygon, Curve, Gradient)
    Param = {1: paramId (uint32), 2: Value};  params sorted ascending by paramId (unsigned).
    Value = {1: float32} | {2: varint int} | {5: string} | {8: curve} | {10: 3x3 float matrix} | ...
    paramId = [bit31 flag] | group << 20 | index ; group per tab:
        tab 1 (corrector) 0x060, tab 2 (qualifier?) 0x083, tab 3 (Linear) 0x087,
        tab 4 (Circle) 0x085, tab 5 (Polygon) 0x08B, tab 6 (Curve) 0x08D,
        tab 18 (Gradient) 0x08F, tab 9 0x0C3, tab 15 (Noise Reduction, Studio) 0x0C4.

Circle window (tab 4) parameter names below: ENCODING is verified byte-exact; the UI
MEANING of each float is inferred from only two real examples (itsjohan HERO, SRM RADIAL)
and is NOT verified in DaVinci -> treat names as best guesses (see CIRCLE_PARAMS notes).
"""
import os, struct, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import powergrade_build as B
from pb import varint

enc_varint = B.enc_varint

# ---------------------------------------------------------------- constants
TAB_CORRECTOR, TAB_QUALIFIER = 1, 2
TAB_LINEAR, TAB_CIRCLE, TAB_POLYGON, TAB_CURVE, TAB_GRADIENT = 3, 4, 5, 6, 18
TAB_NR = 15
WINDOW_LIST = [3, 4, 5, 6, 18]          # node.9 field 2 (packed) in every corrector node seen
DEFAULT_TABS = [2, 3, 4, 5, 6, 18]      # tabs written for every corrector node (may be omitted)
MATRIX_PID = {2: 0x88300031, 3: 0x8870001E, 4: 0x88500010, 5: 0x88B00012,
              6: 0x88D00014, 18: 0x88F0000D}

# Circle window (tab 4).  name -> (paramId, kind, default-when-created, note)
CIRCLE_PARAMS = {
    "p01_opacity_delta": (0x08500001, "f", 0.0,  "low conf: 0 in HERO, -0.0138 in RADIAL; maybe opacity-1"),
    "p04_rotate_rad":    (0x08500004, "f", 0.0,  "low-med: -0.4037 / 0.1123 (= -23.1 deg / 6.4 deg)"),
    "p05_size":          (0x08500005, "f", 643.0, "med-low: 643 / 114 (pixels of node raster); maybe size, maybe soft"),
    "p06_aspect":        (0x08500006, "f", 1.0,  "med-low: 0.862 / 1.366"),
    "p08_enabled":       (0x88500008, "i", 2,    "med: 2 in both examples (Qt::Checked=2, same as node enable)"),
    "p09_invert":        (0x88500009, "i", 0,    "med: 2 in HERO (darkens outside subject), 0 in RADIAL (brightens inside)"),
    "p11_pan_px":        (0x0850000B, "f", 0.0,  "med: offset from frame centre, px (-111.25 / 397.6)"),
    "p12_tilt_px":       (0x0850000C, "f", 0.0,  "med: offset from frame centre, px (-71.78 / -152.47); sign unverified"),
    "p13_soft_px":       (0x8850000D, "f", 721.0, "med-low: 721 / 671; Soft 1 (or size, see p05)"),
    "p14_inside":        (0x8850000E, "f", 0.0,  "low: 0 in both (UI Inside 50 -> 0?)"),
    "p15_outside":       (0x8850000F, "f", 0.0,  "low: 0 in both (UI Outside 50 -> 0?)"),
}
NODE_ENABLE_PID = 0xC0000001            # node field 10: {2: 2} enabled, {2: 0} disabled (greyed)

# ---------------------------------------------------------------- low level
def _key(f, w): return enc_varint((f << 3) | w)
def _ld(f, payload): return _key(f, 2) + enc_varint(len(payload)) + payload
def _f32(f, x): return _key(f, 5) + struct.pack("<f", x)
def _vi(f, n): return _key(f, 0) + enc_varint(n)

def enc_value(kind, v, style="v21"):
    """kind: 'f' float32, 'i' int, 's' string, 'm' 3x3 matrix (9 floats row-major), 'raw' bytes."""
    if kind == "f": return _f32(1, v)
    if kind == "i": return _vi(2, v)
    if kind == "s": return _ld(5, v.encode() if isinstance(v, str) else v)
    if kind == "m":
        body = b"".join(_f32(i + 1, x) for i, x in enumerate(v) if style == "v21" or x != 0.0)
        return _ld(10, body)
    if kind == "raw": return v
    raise ValueError(kind)

def dec_value(b):
    """-> (kind, value, style) ; style only meaningful for matrices."""
    fs = B.fields(b)
    if len(fs) == 1:
        f, w, ks, p = fs[0]
        if f == 1 and w == 5: return "f", struct.unpack("<f", p)[0], None
        if f == 2 and w == 0: return "i", varint(p, 0)[0], None
        if f == 10 and w == 2:
            m = [0.0] * 9; n = 0
            for ff, ww, kk, pp in B.fields(p):
                m[ff - 1] = struct.unpack("<f", pp)[0]; n += 1
            style = "v21" if n == 9 else "v20"
            if enc_value("m", m, style) == b: return "m", m, style
    return "raw", b, None

def enc_param(pid, value_bytes): return _ld(3, _vi(1, pid) + _ld(2, value_bytes))

def build_tab(tab_id, params):
    """params: list of (pid, value_bytes); sorted by pid as DaVinci does."""
    body = _vi(1, 1) + b"".join(enc_param(p, v) for p, v in sorted(params, key=lambda x: x[0]))
    return _vi(1, tab_id) + _vi(3, 1) + _ld(6, _ld(2, body))

def parse_tab(entry):
    """-> (tab_id, [(pid, value_bytes)]) ; asserts the known wrapper layout."""
    tab_id = B.getv(entry, 1)
    assert [f for f, *_ in B.fields(entry)] == [1, 3, 6] and B.getv(entry, 3) == 1
    e6 = B.getv(entry, 6); assert [f for f, *_ in B.fields(e6)] == [2]
    e62 = B.getv(e6, 2); fs = B.fields(e62)
    assert fs[0][0] == 1 and varint(fs[0][3], 0)[0] == 1
    out = []
    for f, w, ks, p in fs[1:]:
        assert f == 3
        out.append((B.getv(p, 1), B.getv(p, 2)))
    return tab_id, out

# ---------------------------------------------------------------- matrices / default tabs
def matrix(sx=1.0, sy=None):
    sy = sx if sy is None else sy
    return [sx, 0.0, 0.0, 0.0, sy, 0.0, 0.0, 0.0, 1.0]

def default_tab(tab_id, mat=None, style="v21"):
    """Empty window/qualifier tab: only the per-node raster matrix (identity unless given)."""
    return build_tab(tab_id, [(MATRIX_PID[tab_id], enc_value("m", mat or matrix(), style))])

# ---------------------------------------------------------------- circle window
def make_circle_tab(mat=None, style="v21", **kw):
    """Build a Circle window tab (tab 4).  kw keys = CIRCLE_PARAMS names (missing -> default).
    Example (centred soft ellipse, inverted = affects the background):
        make_circle_tab(p11_pan_px=0, p12_tilt_px=0, p05_size=640, p13_soft_px=640,
                        p06_aspect=1.0, p09_invert=2)
    """
    bad = set(kw) - set(CIRCLE_PARAMS)
    if bad: raise KeyError(bad)
    params = []
    for name, (pid, kind, dflt, note) in CIRCLE_PARAMS.items():
        params.append((pid, enc_value(kind, kw.get(name, dflt))))
    params.append((MATRIX_PID[4], enc_value("m", mat or matrix(), style)))
    return build_tab(TAB_CIRCLE, params)

def parse_circle_tab(entry):
    tab_id, params = parse_tab(entry)
    assert tab_id == TAB_CIRCLE
    by_pid = {p: v for p, v in params}
    out = {}
    for name, (pid, kind, dflt, note) in CIRCLE_PARAMS.items():
        if pid in by_pid:
            k, v, _ = dec_value(by_pid[pid]); assert k == kind, (name, k); out[name] = v
    k, m, st = dec_value(by_pid[MATRIX_PID[4]])
    out["mat"], out["style"] = m, st
    return out

# ---------------------------------------------------------------- node-level edits
def node_tabs(node):
    t = B.getv(node, 9)
    return [] if not isinstance(t, bytes) else B.fields(t)

def get_tab(node, tab_id):
    for f, w, ks, p in node_tabs(node):
        if f == 1 and B.getv(p, 1) == tab_id: return p

def set_tab(node, entry):
    """Insert/replace a tab entry in node field 9 (keeps DaVinci's ascending tab-id order,
    keeps the packed window list; creates field 9 + window list if the node had none)."""
    tab_id = B.getv(entry, 1)
    nf = B.fields(node)
    f9 = next((x for x in nf if x[0] == 9), None)
    inner = B.fields(f9[3]) if f9 is not None else []
    tabs = [x for x in inner if x[0] == 1 and B.getv(x[3], 1) != tab_id]
    rest = [x for x in inner if x[0] != 1]
    tabs.append(B.vbytes(1, entry))
    tabs.sort(key=lambda x: B.getv(x[3], 1))
    if not any(x[0] == 2 for x in rest):
        rest.append(B.vbytes(2, b"".join(enc_varint(i) for i in WINDOW_LIST)))
    newf9 = B.build(tabs + rest)
    if f9 is None:
        B.setb(nf, 9, newf9)
        order = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        nf.sort(key=lambda f: order.index(f[0]) if f[0] in order else 99)
    else:
        f9[1], f9[2], f9[3] = 2, B.key(9, 2), newf9
    return B.build(nf)

def set_tab_params(node, tab_id, updates, default_mat=None, style="v21"):
    """Merge {pid: value_bytes or None(delete)} into a tab (creating it if needed)."""
    e = get_tab(node, tab_id)
    if e is None:
        params = [(MATRIX_PID[tab_id], enc_value("m", default_mat or matrix(), style))] if tab_id in MATRIX_PID else []
    else:
        params = parse_tab(e)[1]
    d = dict(params)
    for pid, vb in updates.items():
        if vb is None: d.pop(pid, None)
        else: d[pid] = vb
    return set_tab(node, build_tab(tab_id, list(d.items())))

def node_matrix(node, tab_id=TAB_CIRCLE):
    """Matrix currently stored on the node (falls back to identity/v21)."""
    for t in (tab_id, 2, 3, 4, 5, 6, 18):
        e = get_tab(node, t)
        if e is not None:
            for pid, v in parse_tab(e)[1]:
                if pid == MATRIX_PID[t]:
                    k, m, st = dec_value(v); return m, st
    return matrix(), "v21"

def is_enabled(node):
    f10 = B.getv(node, 10)
    for f, w, ks, p in B.fields(f10 or b""):
        if f == 1 and B.getv(p, 1) == NODE_ENABLE_PID:
            return B.getv(B.getv(p, 2), 2) == 2
    return True

def set_enabled(node, on=True):
    """Node enable flag = node.10 -> {1: 0xC0000001, 2: {2: 2|0}} (2 = on, 0 = off/greyed)."""
    nf = B.fields(node)
    f10 = next(x for x in nf if x[0] == 10)
    entries = B.fields(f10[3])
    for x in entries:
        if x[0] == 1 and B.getv(x[3], 1) == NODE_ENABLE_PID:
            x[3] = _vi(1, NODE_ENABLE_PID) + _ld(2, _vi(2, 2 if on else 0))
            break
    else:
        entries.insert(0, B.vbytes(1, _vi(1, NODE_ENABLE_PID) + _ld(2, _vi(2, 2 if on else 0))))
    f10[3] = B.build(entries)
    return B.build(nf)

# Blur palette lives in TAB 1 (not tab 18): radius R,G,B = deltas from the 0.5 UI neutral.
BLUR_RADIUS_PIDS = (0x86000052, 0x86000053, 0x86000054)   # SHARP nodes store -0.04 (= UI 0.46)

def set_blur_radius(node, ui_radius):
    """ui_radius > 0.5 blurs, < 0.5 sharpens (UI 0..1).  Stored as ui_radius - 0.5."""
    d = ui_radius - 0.5
    return set_tab_params(node, TAB_CORRECTOR, {p: enc_value("f", d) for p in BLUR_RADIUS_PIDS})

# ---------------------------------------------------------------- whole-file editing
def map_nodes(graph, fn):
    """Rebuild a graph (and compound inner graphs, node field 11) applying fn(node)->node."""
    out = []
    for f, w, ks, p in B.fields(graph):
        if f == 7 and w == 2:
            sub = B.getv(p, 11)
            if isinstance(sub, bytes):
                nf = B.fields(p)
                for x in nf:
                    if x[0] == 11: x[3] = map_nodes(sub, fn)
                p = B.build(nf)
            p = fn(p)
        out.append([f, w, ks, p])
    return B.build(out)

def edit_drx(src, dst, fn, new_ids=True, label=None):
    """Apply fn(node)->node to every node of a .drx and write dst (same XML skeleton)."""
    import re, uuid, zstandard, html
    xml = open(src, encoding="utf-8").read()
    m, prefix, d = B.body_of(xml, "pClipFullVer")
    top = B.fields(d)
    for x in top:
        if x[0] == 1: x[3] = map_nodes(x[3], fn)
    nd = B.build(top)
    comp = zstandard.ZstdCompressor(level=19, write_content_size=True).compress(nd)
    xml = xml[:m.start(2)] + (prefix + comp).hex() + xml[m.end(2):]
    if new_ids:
        for old in set(re.findall(r'DbId="([0-9a-f-]{36})"', xml)):
            xml = xml.replace(old, str(uuid.uuid4()))
    if label:
        xml = re.sub(r"<Label>[^<]*</Label>", lambda mm: "<Label>%s</Label>" % html.escape(label, quote=False), xml, count=1)
    open(dst, "w", encoding="utf-8").write(xml)
    return nd

def by_name(name, fn):
    """Wrap fn so it only touches nodes whose label (node field 6) == name."""
    def g(node):
        nm = B.getv(node, 6)
        return fn(node) if isinstance(nm, bytes) and nm.decode(errors="replace") == name else node
    return g

def circle_on_node(**circle):
    """fn(node): put a circle window on the node using the node's own raster matrix/style."""
    def g(node):
        m, st = node_matrix(node)
        return set_tab(node, make_circle_tab(mat=m, style=st, **circle))
    return g

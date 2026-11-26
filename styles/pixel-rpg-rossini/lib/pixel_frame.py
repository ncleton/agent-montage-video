"""Décor pixel art du film : bureau vu du dessus, grand écran style jeu vidéo, portrait expressif.

Sprites du bureau AO (Pixel Agents, MIT ; personnages MetroCity, CC0) copiés dans sources/pixel-office
avec leurs licences. Portraits et bulles : gen_pixel_portraits.py (dessins originaux). Un seul humain,
aucun agent visible. Géométrie commune à toutes les scènes : écran intérieur 1280 × 720 à (320, 168).
"""
import json

SX, SY, SW, SH = 320, 168, 1280, 720
EXPRS = ['neutre', 'perplexe', 'compris', 'content', 'fatigue', 'agace', 'cligne']
EMOTES = ['question', 'exclamation', 'points', 'colere', 'note', 'coeur']
PIX = ' style="image-rendering:pixelated"'


def img(f, x, y, w, h, id=None, op=None):
    a = f' id="{id}"' if id else ''
    o = f' opacity="{op}"' if op is not None else ''
    return f'<image{a}{o} href="assets/pixel/{f}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="none"{PIX}/>'


def sprite(f, sheet_w, sheet_h, sx, sy, sw, sh, x, y, scale, id=None, op=None):
    a = f' id="{id}"' if id else ''
    o = f' opacity="{op}"' if op is not None else ''
    return (f'<g{a}{o}><svg x="{x}" y="{y}" width="{sw * scale}" height="{sh * scale}" viewBox="{sx} {sy} {sw} {sh}" overflow="hidden">'
            f'<image href="assets/pixel/{f}" x="0" y="0" width="{sheet_w}" height="{sheet_h}"{PIX}/></svg></g>')


def rect(x, y, w, h, fill, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{extra}/>'


# ---------------------------------------------------------------- grand écran
def frame_background(k):
    """Ce qui entoure l'ordinateur : fond sombre et bureau en bois sous l'écran."""
    grid = ''.join(rect(x, 0, 2, 1080, '#E3342F', ' opacity=".035"') for x in range(0, 1920, 48))
    grid += ''.join(rect(0, y, 1920, 2, '#E3342F', ' opacity=".035"') for y in range(0, 1080, 48))
    desk = rect(0, 948, 1920, 132, '#241B1C') + rect(0, 948, 1920, 8, '#4A2A2C') + ''.join(rect(x, 960, 4, 120, '#1A1314') for x in range(140, 1920, 260))
    return f'<g id="{k("framebg")}">' + rect(0, 0, 1920, 1080, '#0B0909') + grid + desk + '</g>'


def _notched(x0, y0, x1, y1, u):
    return (f'M{x0 + u} {y0} H{x1 - u} V{y0 + u} H{x1} V{y1 - u} H{x1 - u} V{y1} H{x0 + u} V{y1 - u} H{x0} V{y0 + u} H{x0 + u} Z')


def _hole(x, y, w, h):
    return f'M{x} {y} V{y + h} H{x + w} V{y} Z'


def _ring(outer, hole, fill):
    return f'<path d="{outer} {hole}" fill="{fill}" fill-rule="evenodd"/>'


def bezel(k):
    """Ordinateur dessiné à la façon du sprite PC du bureau AO, agrandi. Creux : il se pose sur le contenu."""
    x0, y0, x1, y1, u = 284, 132, 1636, 924, 12
    O, C1, C2, HI, SH_ = '#3F3740', '#E1E3E9', '#B5BFC7', '#FFFFFF', '#757B7C'
    hole = _hole(SX - 12, SY - 12, SW + 24, SH + 24)
    out = _ring(_notched(x0 - 6, y0 - 6, x1 + 6, y1 + 6, u), hole, O) + _ring(_notched(x0, y0, x1, y1, u), hole, C1)
    out += rect(x0 + u, y0, x1 - x0 - 2 * u, 6, HI) + rect(x0, y0 + u, 6, y1 - y0 - 2 * u, HI)
    out += rect(x0 + u, y1 - 30, x1 - x0 - 2 * u, 30, C2) + rect(x1 - 8, y0 + u, 8, y1 - y0 - 2 * u, C2)
    out += _ring(_hole(SX - 12, SY - 12, SW + 24, SH + 24), _hole(SX - 6, SY - 6, SW + 12, SH + 12), O)
    out += _ring(_hole(SX - 6, SY - 6, SW + 12, SH + 12), _hole(SX, SY, SW, SH), '#4A3A3C')
    out += rect(1560, 900, 18, 10, '#E3342F') + ''.join(rect(330 + i * 18, 902, 10, 6, SH_) for i in range(5))
    out += rect(916, 924, 88, 32, O) + rect(922, 924, 76, 30, C2)
    out += rect(830, 950, 260, 22, O) + rect(836, 950, 248, 16, C1) + rect(836, 962, 248, 4, C2)
    return f'<g id="{k("bezel")}">{out}</g>'


def facecam(k, hidden=False):
    """Portrait style boîte de dialogue, à droite de l'écran, avec ses bulles."""
    x, y = 1652, 548
    box = (rect(x, y, 240, 308, '#1A1A1A') + rect(x + 6, y + 6, 228, 296, '#F8F8F0') + rect(x + 14, y + 14, 212, 212, '#F0DCDA')
           + rect(x + 14, y + 236, 212, 56, '#3A2325')
           + f'<text x="{x + 120}" y="{y + 274}" text-anchor="middle" font-family="Montserrat" font-weight="600" font-size="26" letter-spacing="4" fill="#F8F8F0">VOUS</text>')
    faces = ''.join(img(f'generated/portrait-{e}.png', x + 24, y + 24, 192, 192, id=k(f'fx-{e}'), op=1 if e == 'neutre' else 0) for e in EXPRS)
    em = ''.join(img(f'generated/bulle-{e}.png', x + 150, y - 96, 90, 90, id=k(f'em-{e}'), op=0) for e in EMOTES)
    em += img('generated/goutte.png', x + 190, y + 40, 28, 36, id=k('em-goutte'), op=0)
    return f'<g id="{k("face")}"{" opacity=\"0\"" if hidden else ""}><g id="{k("facebody")}">{box}{faces}</g>{em}</g>'


def face_js(k, expr, when, hold=None):
    """Change d'expression : une seule image visible à la fois, retour éventuel au neutre."""
    js = []
    for e in EXPRS:
        js.append(f'tl.set("#{k("fx-" + e)}",{{opacity:{1 if e == expr else 0}}},{when});')
    js.append(f'tl.fromTo("#{k("facebody")}",{{y:0}},{{keyframes:[{{y:-10,duration:.08}},{{y:0,duration:.18,ease:"bounce.out"}}],immediateRender:false}},{when});')
    if hold:
        js += [f'tl.set("#{k("fx-" + e)}",{{opacity:{1 if e == "neutre" else 0}}},{when}+{hold});' for e in EXPRS]
    return js


def emote_js(k, name, when, d=1.6):
    t = f'#{k("em-" + name)}'
    if name == 'goutte':
        return [f'tl.fromTo("{t}",{{opacity:0,y:0}},{{opacity:1,duration:.15,immediateRender:false}},{when});',
                f'tl.to("{t}",{{y:40,opacity:0,duration:1.2,ease:"power1.in"}},{when}+.4);']
    return [f'tl.fromTo("{t}",{{opacity:0,scale:.3,transformOrigin:"50% 100%"}},{{opacity:1,scale:1,duration:.22,ease:"back.out(2.5)",immediateRender:false}},{when});',
            f'tl.to("{t}",{{opacity:0,duration:.2}},{when}+{d});']


def blink_js(k, dur, start=1.0, base='neutre'):
    js, t = [], start
    while t < dur - .4:
        js.append(f'tl.set("#{k("fx-cligne")}",{{opacity:1}},{t:.2f});tl.set("#{k("fx-cligne")}",{{opacity:0}},{t + .12:.2f});')
        t += 3.1 + (int(t * 7) % 5) * .27
    return js


# ---------------------------------------------------------------- bureau vu du dessus (loft Rossini Energy)
LOFT = dict(steel='#333F42', steel2='#4A5659', wood='#C69964', light='#E1BD87', grain='#AF7D4D', edge='#8A6238', dark='#5A3B22',
            teal='#5A4447', plum='#68495D', mustard='#BC983B', beton='#D3D0C5', beton2='#C4C0B4', wall='#ECEBE6', ink='#1B1F22')


def _wood(x, y, w, h, front=16, legs=True):
    L = LOFT
    o = rect(x + 6, y + 8, w, h + front, '#000', ' opacity=".18"')
    o += rect(x, y, w, h, L['wood']) + rect(x, y, w, 6, L['light'])
    o += ''.join(rect(x + 12, y + 18 + i * 22, w - 24 - (i * 37) % 90, 3, L['grain'], ' opacity=".55"') for i in range(max(1, (h - 24) // 22)))
    o += rect(x, y + h, w, front, L['edge']) + rect(x, y + h + front - 4, w, 4, L['dark'])
    if legs:
        o += rect(x + 10, y + h + front, 14, 30, L['steel']) + rect(x + w - 24, y + h + front, 14, 30, L['steel'])
    return o


def _monitor(x, y, w=118, h=72):
    L = LOFT
    return (rect(x + w / 2 - 8, y + h, 16, 14, L['steel']) + rect(x + w / 2 - 26, y + h + 12, 52, 6, L['steel'])
            + rect(x, y, w, h, L['ink']) + rect(x + 6, y + 6, w - 12, h - 12, '#2A3236') + rect(x + 10, y + 10, w - 40, 6, '#3C474C')
            + rect(x + w / 2 - 34, y + h + 26, 68, 14, '#E8E8E2') + rect(x + w / 2 - 30, y + h + 30, 60, 6, '#BFC3C4'))


def _office_chair(x, y, jacket=False):
    L = LOFT
    o = rect(x + 6, y + 8, 84, 84, '#000', ' opacity=".18"') + rect(x, y, 84, 84, '#22272A') + rect(x + 8, y + 8, 68, 54, '#30383C')
    o += rect(x + 30, y + 84, 24, 12, L['steel'])
    if jacket:
        o += rect(x - 6, y - 6, 96, 64, '#E0452B') + ''.join(rect(x - 6, y + 6 + i * 14, 96, 3, '#B8331F') for i in range(4))
        o += rect(x - 14, y + 4, 14, 46, '#E0452B') + rect(x + 90, y + 4, 14, 46, '#E0452B')
    return o


def _plant(x, y, big=False):
    s = 1.4 if big else 1.0
    o = rect(x, y + 40 * s, 44 * s, 36 * s, '#8E5B3A') + rect(x, y + 40 * s, 44 * s, 6 * s, '#6E4529')
    for i, (dx, dy) in enumerate([(-18, -6), (8, -26), (30, -8), (-6, 10), (22, 12), (40, 18), (-22, 22)]):
        o += rect(x + 22 * s + dx * s - 10 * s, y + 30 * s + dy * s, 22 * s, 14 * s, '#3E8A4E' if i % 2 else '#2F6E3D')
    return o


def _carpet(x0, y0, cols, rows, t=80):
    L = LOFT
    pal = [L['teal'], L['mustard'], L['plum'], None, L['teal'], L['plum'], L['mustard'], None, L['mustard']]
    o = ''
    for r in range(rows):
        for c in range(cols):
            col = pal[(r * 5 + c * 3 + (r * c) % 4) % len(pal)]
            if col:
                o += rect(x0 + c * t, y0 + r * t, t - 2, t - 2, col)
    return o


def _crates(x, y, cols, rows):
    L = LOFT
    o = rect(x + 8, y + 10, cols * 96, rows * 58, '#000', ' opacity=".16"')
    for r in range(rows):
        for c in range(cols):
            bx, by = x + c * 96, y + r * 58
            o += rect(bx, by, 92, 54, L['light']) + rect(bx, by + 46, 92, 8, L['grain'])
            o += ''.join(f'<circle cx="{bx + 20 + i * 26}" cy="{by + 24}" r="8" fill="{L["edge"]}"/>' for i in range(3))
    return o


def _truss(x0, y0, x1, y1):
    """Ferme en bois vue d'en haut : deux entraits, poteaux et contrefiches (au plafond, donc devant)."""
    L, b = LOFT, 22
    beam = lambda x, y, w, h: rect(x, y, w, h, L['dark']) + rect(x + 3, y + 3, w - 6, h - 6, L['light'])
    o = beam(x0, y0, x1 - x0, b) + beam(x0, y1 - b, x1 - x0, b)
    o += beam(x0, y0, b, y1 - y0) + beam(x1 - b, y0, b, y1 - y0)
    c = 62
    for (ax, ay, bx, by) in [(x0 + b, y0 + b, x0 + b + c, y0 + b + c), (x1 - b, y0 + b, x1 - b - c, y0 + b + c),
                             (x0 + b, y1 - b, x0 + b + c, y1 - b - c), (x1 - b, y1 - b, x1 - b - c, y1 - b - c)]:
        o += f'<path d="M{ax} {ay} L{bx} {by}" stroke="{L["dark"]}" stroke-width="18"/><path d="M{ax} {ay} L{bx} {by}" stroke="{L["light"]}" stroke-width="12"/>'
    return o


def _workbench(x, y, w, h):
    L = LOFT
    o = _wood(x, y, w, h, 18)
    for i in range(7):
        bx, by = x + 26 + (i * 71) % (w - 70), y + 22 + (i * 37) % (h - 50)
        o += rect(bx, by, 34, 22, ['#E8E8E2', '#8E1E1A', '#9AA3A6'][i % 3]) + rect(bx + 4, by + 4, 10, 6, '#333F42')
    o += f'<path d="M{x + 40} {y + h - 18} q60 -40 120 0 t120 -6" fill="none" stroke="#F4F2EA" stroke-width="4"/>'
    o += rect(x + w - 110, y + 16, 80, 44, '#C8302C') + rect(x + w - 104, y + 22, 68, 10, '#8E1E1A')
    return o


def _stairs(x, y, w, h):
    L = LOFT
    o = rect(x, y, w, h, L['steel'])
    o += ''.join(rect(x, y + i * 30, w, 8, L['steel2']) for i in range(int(h / 30) + 1))
    o += rect(x - 10, y - 10, 12, h + 10, L['ink']) + rect(x + w - 2, y - 10, 12, h + 10, L['ink'])
    return o


def office(k, stack=3, done=0, agent_desk=False):
    """Loft Rossini Energy vu du dessus, d'après les photos : béton, ferme bois, îlot sur dalles colorées, établi."""
    L = LOFT
    o = rect(-1600, -400, 5120, 2400, L['beton'])
    o += ''.join(rect(x, 300, 3, 780, L['beton2']) for x in range(240, 1920, 240)) + ''.join(rect(0, y, 1920, 3, L['beton2']) for y in range(540, 1080, 240))
    o += ''.join(f'<ellipse cx="{(i * 397) % 1900}" cy="{360 + (i * 211) % 700}" rx="{30 + i * 7 % 40}" ry="{12 + i % 3 * 6}" fill="#C9C5B9" opacity=".6"/>' for i in range(9))
    # mur blanc du fond : verrières noires, tableau, horloge, porte rouge
    o += rect(-1600, -400, 5120, 700, L['wall']) + rect(-1600, 286, 5120, 14, '#B9B6AD')
    for vx, vw in ((40, 520), (1660, 240)):
        o += rect(vx, 140, vw, 146, L['ink']) + ''.join(rect(vx + 8 + c * ((vw - 8) // 4), 148, (vw - 8) // 4 - 8, 130, '#AFC4C6') for c in range(4))
        o += ''.join(rect(vx + 8 + c * ((vw - 8) // 4), 148, 10, 130, '#D9E5E6') for c in range(4))
    o += rect(700, 150, 230, 120, '#FAFAF7') + rect(700, 150, 230, 120, 'none', ' stroke="#9AA3A6" stroke-width="6"')
    o += ''.join(rect(712 + c * 30, 168, 22, 20, '#E3E6E6') for c in range(7)) + ''.join(rect(712 + c * 30, 196, 22, 20, '#E3E6E6') for c in range(7))
    o += rect(712, 228, 120, 8, '#E3342F') + rect(712, 244, 80, 8, '#C8302C')
    o += f'<circle cx="1010" cy="200" r="30" fill="#FAFAF7" stroke="{L["ink"]}" stroke-width="6"/><path d="M1010 200 V182 M1010 200 H1024" stroke="{L["ink"]}" stroke-width="5"/>'
    o += rect(1440, 120, 150, 168, '#8E1E1A') + rect(1448, 128, 134, 160, '#C8302C') + rect(1470, 150, 60, 36, '#FAFAF7') + rect(1556, 210, 12, 22, '#ECEBE6')
    o += _plant(600, 210, True) + _plant(1610, 216)
    # caisses de bois et bornes (stock)
    o += _crates(90, 360, 4, 4)
    o += ''.join(rect(120 + i * 70, 620, 44, 130, L['light']) + rect(120 + i * 70, 620, 44, 16, L['grain']) for i in range(4))
    # îlot sur dalles de moquette, sous la ferme en bois
    o += _carpet(578, 342, 10, 7)
    o += _wood(650, 420, 620, 150, 18)
    o += _monitor(694, 404) + _monitor(1110, 404)
    o += _plant(1020, 460) + rect(860, 520, 26, 24, '#F4F2EA') + rect(864, 524, 18, 6, '#6E4529')
    o += _office_chair(700, 620) + _office_chair(1130, 620, jacket=True)
    o += (img('PC_FRONT_ON_1.png', 912, 384, 96, 192) + img('PC_FRONT_ON_2.png', 912, 384, 96, 192, id=k('pc2'), op=0)
          + img('PC_FRONT_ON_3.png', 912, 384, 96, 192, id=k('pc3'), op=0))
    # bons à traiter (pile) et bons traités, posés sur le plateau
    o += ''.join(f'<g id="{k(f"st{i}")}"{"" if i < stack else " opacity=\"0\""}>' + rect(1032, 534 - i * 8, 70, 12, '#F4F2EA') + rect(1032, 544 - i * 8, 70, 2, '#BDB6AB') + '</g>' for i in range(16))
    o += ''.join(f'<g id="{k(f"dn{i}")}"{"" if i < done else " opacity=\"0\""}>' + rect(820, 534 - i * 8, 70, 12, '#F4F2EA') + rect(820, 544 - i * 8, 70, 2, '#E3342F') + '</g>' for i in range(8))
    # l'humain, assis face à son écran, vu de dos
    s = 6
    o += sprite('char_0.png', 112, 96, 48, 32, 16, 32, 912, 506, s, id=k('back1'))
    o += sprite('char_0.png', 112, 96, 64, 32, 16, 32, 912, 506, s, id=k('back2'), op=0)
    o += sprite('char_0.png', 112, 96, 48, 64, 16, 32, 912, 506, s, id=k('side'), op=0)
    o += sprite('char_0.png', 112, 96, 0, 0, 16, 32, 912, 506, s, id=k('front'), op=0)
    o += img('CUSHIONED_CHAIR_BACK.png', 912, 640, 96, 96)
    # établi d'électronique et bureau de l'agent (vide)
    o += _workbench(1450, 470, 380, 150)
    o += ''.join(rect(1500 + i * 60, 690, 36, 150, L['light']) + rect(1500 + i * 60, 690, 36, 14, L['grain']) for i in range(3))
    if agent_desk:
        o += _wood(1440, 870, 400, 110, 16, legs=False) + _office_chair(1600, 1010)
        o += (f'<g id="{k("aplate")}">' + rect(1470, 886, 92, 46, '#1A1314') + f'<path d="M1492 898 l10 6 v12 l-10 6 l-10 -6 v-12 Z" fill="none" stroke="#E3342F" stroke-width="3"/>'
              + f'<text x="1514" y="918" font-family="Montserrat" font-weight="600" font-size="20" fill="#E3342F">IA</text></g>')
        o += ''.join(f'<g id="{k(f"ap{i}")}" opacity="0">' + rect(1660 - (i * 7) % 11, 950 - i * 9, 92, 12, '#F4F2EA' if i else '#F6D2CF') + rect(1660 - (i * 7) % 11, 960 - i * 9, 92, 2, '#E3342F' if i == 0 else '#BDB6AB') + '</g>' for i in range(40))
    o += _truss(556, 318, 1384, 924)
    o += _stairs(40, 820, 300, 260)
    o += ''.join(img(f'generated/bulle-{e}.png', 1000, 418, 90, 90, id=k(f'oe-{e}'), op=0) for e in EMOTES)
    o += img('generated/goutte.png', 1010, 520, 28, 36, id=k('oe-goutte'), op=0)
    return f'<g id="{k("office")}">{o}</g>'



def office_emote_js(k, name, when, d=1.6):
    t = f'#{k("oe-" + name)}'
    if name == 'goutte':
        return [f'tl.fromTo("{t}",{{opacity:0,y:0}},{{opacity:1,duration:.15,immediateRender:false}},{when});',
                f'tl.to("{t}",{{y:36,opacity:0,duration:1.1,ease:"power1.in"}},{when}+.35);']
    return [f'tl.fromTo("{t}",{{opacity:0,scale:.3,transformOrigin:"50% 100%"}},{{opacity:1,scale:1,duration:.22,ease:"back.out(2.5)",immediateRender:false}},{when});',
            f'tl.to("{t}",{{opacity:0,duration:.2}},{when}+{d});']


def pose_js(k, pose, when):
    return [f'tl.set("#{k(p)}",{{opacity:{1 if p == pose else 0}}},{when});' for p in ('back1', 'back2', 'side', 'front')]


def office_idle_js(k, dur):
    n = max(1, int(dur / .9))
    n += (n + 1) % 2
    return [f'tl.to("#{k("pc2")}",{{opacity:1,duration:.01,yoyo:true,repeat:{n},repeatDelay:.44}},0);']


def tr(s, ox, oy, dx=0.0, dy=0.0):
    """Mise à l'échelle autour de (ox, oy), écrite directement dans l'attribut transform."""
    return f'translate({ox * (1 - s) + dx:.3f} {oy * (1 - s) + dy:.3f}) scale({s:.5f})'


def tw_attr(target, value, when, d=None, ease='power3.in'):
    if d is None:
        return f'tl.set("{target}",{{attr:{{transform:"{value}"}}}},{when});'
    return f'tl.to("{target}",{{attr:{{transform:"{value}"}},duration:{d},ease:"{ease}"}},{when});'


MON_SMALL = tr(.0562, 960, 528, 0, -105)
OFFICE_BIG = tr(17.8, 960, 423)
IDENT = tr(1, 0, 0)


def zoom_in_js(k, when, d=1.3, init_office=True):
    mon, off = f'#{k("mon")}', f'#{k("office")}'
    return ([tw_attr(off, IDENT, 0)] if init_office else []) + [tw_attr(mon, MON_SMALL, 0), f'tl.set("{mon}",{{opacity:0}},0);', f'tl.set("{mon}",{{opacity:1}},{when});',
            tw_attr(mon, IDENT, when, d), tw_attr(off, OFFICE_BIG, when, d),
            f'tl.to("{off}",{{opacity:0,duration:.3}},{when}+{d - .3:.2f});',
            f'tl.fromTo("#{k("framebg")}",{{opacity:0}},{{opacity:1,duration:.35,immediateRender:false}},{when}+{d - .35:.2f});',
            f'tl.fromTo("#{k("face")}",{{opacity:0,x:60}},{{opacity:1,x:0,duration:.4,ease:"power2.out",immediateRender:false}},{when}+{d:.2f});']


def zoom_out_js(k, when, d=1.3):
    mon, off = f'#{k("mon")}', f'#{k("office")}'
    return [tw_attr(mon, IDENT, 0), tw_attr(off, OFFICE_BIG, 0), f'tl.set("{off}",{{opacity:0}},0);',
            f'tl.to("#{k("face")}",{{opacity:0,x:60,duration:.3}},{when});',
            f'tl.to("#{k("framebg")}",{{opacity:0,duration:.35}},{when});',
            f'tl.set("{off}",{{opacity:1}},{when});',
            tw_attr(off, IDENT, when, d, 'power3.out'), tw_attr(mon, MON_SMALL, when, d, 'power3.out'),
            f'tl.to("{mon}",{{opacity:0,duration:.25}},{when}+{d - .25:.2f});']


# ---------------------------------------------------------------- habillage des autres scènes
TAG_FACE = {'PROBLÈME': ('perplexe', 'question'), 'SOLUTION': ('compris', 'exclamation'), 'COMPRENDRE': ('neutre', 'points'),
            'AVANT': ('fatigue', 'goutte'), 'EN PRATIQUE': ('compris', 'exclamation'), 'À RETENIR': ('content', 'note'),
            'TUTORIEL': ('compris', 'exclamation')}


def wrap_scene(sid, tag, duration):
    """SVG (fond, ordinateur, portrait) et animation du portrait pour une scène expliquée dans l'écran."""
    k = lambda x: f'{sid}-px-{x}'
    expr, em = TAG_FACE.get(tag, ('content', 'coeur' if sid == 'S31' else 'note'))
    under = f'<svg class="pxframe" viewBox="0 0 1920 1080">{frame_background(k)}</svg>'
    over = f'<svg class="pxframe" viewBox="0 0 1920 1080">{bezel(k)}{facecam(k)}</svg>'
    js = blink_js(k, duration, 3.6) + face_js(k, expr, .5, hold=2.6) + (emote_js(k, em, .5) if em else [])
    if tag == 'PROBLÈME':
        js += face_js(k, 'agace', max(1.0, duration * .55), hold=2.0)
    return under, over, '\n'.join(js)

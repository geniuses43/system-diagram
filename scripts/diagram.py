"""Мини-библиотека для схем систем: блоки, стрелки, шины, зоны и самопроверка.

Подключение в генераторе схемы:
    import sys; sys.path.insert(0, '<путь к scripts>')
    from diagram import Diagram

Всё рисуется в координатах SVG (px). Линии — ломаные из горизонтальных и
вертикальных отрезков. save() собирает HTML-страницу и печатает предупреждения:
пересечения линий, линии сквозь блоки, наложения, вылезающий текст, «·».
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = os.path.join(HERE, '..', 'assets', 'head.html')

# Примерная ширина символа (Inter): заголовок 12.5px semibold, подпись 10.5px, подпись стрелки 10px
CW_TITLE, CW_SUB, CW_EDGE = 7.4, 6.1, 5.8


class Box:
    def __init__(self, x, y, w, h, title, sub=None, kind='box'):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.title, self.sub, self.kind = title, sub, kind

    l = property(lambda s: s.x)
    r = property(lambda s: s.x + s.w)
    t = property(lambda s: s.y)
    b = property(lambda s: s.y + s.h)
    cx = property(lambda s: s.x + s.w / 2)
    cy = property(lambda s: s.y + s.h / 2)

    # Точки на сторонах блока; d — сдвиг от середины стороны
    def left(self, d=0): return (self.l, self.cy + d)
    def right(self, d=0): return (self.r, self.cy + d)
    def top(self, d=0): return (self.cx + d, self.t)
    def bottom(self, d=0): return (self.cx + d, self.b)


class Diagram:
    BOX_KINDS = ('box', 'ext', 'data', 'plan', 'role', 'key')
    ZONE_KINDS = ('server', 'group', 'data')
    LINE_KINDS = ('fg', 'acc', 'plan')

    def __init__(self, width, height, aria):
        self.W, self.H, self.aria = width, height, aria
        self.z, self.o = [], []          # зоны рисуются под всем остальным
        self.boxes, self.segs, self.labels, self.texts, self.zones, self.ends = [], [], [], [], [], []
        self._net = 0

    # ---------- примитивы
    def _text(self, x, y, t, cls, anchor='start', out=None):
        self.texts.append(t)
        (out if out is not None else self.o).append(
            f'<text class="{cls}" x="{x:g}" y="{y:g}" text-anchor="{anchor}">{html.escape(t)}</text>')

    def text(self, x, y, t, cls='t', anchor='start'):
        self._text(x, y, t, cls, anchor)

    def zone(self, x, y, w, h, label=None, kind='group', label_at='top'):
        """Рамка-область: server (сплошная), group (пунктир), data (заливка хранилища)."""
        assert kind in self.ZONE_KINDS, kind
        self.zones.append((x, y, x + w, y + h))
        self.z.append(f'<rect class="z-{kind}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10"/>')
        if label:
            ly = y + 20 if label_at == 'top' else y + h - 12
            cls = {'server': 'hdr', 'group': 'zone', 'data': 'dh'}[kind]
            self._text(x + 14, ly, label, cls, out=self.z)

    def box(self, x, y, w, h, title, sub=None, kind='box', center=False):
        """Блок: заголовок и максимум одна короткая строка под ним."""
        assert kind in self.BOX_KINDS, kind
        b = Box(x, y, w, h, title, sub, kind)
        self.boxes.append(b)
        self.o.append(f'<rect class="k-{kind}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="6"/>')
        tx, an = (x + w / 2, 'middle') if center else (x + 12, 'start')
        if sub:
            self._text(tx, y + h / 2 - 3, title, 'b', an)
            self._text(tx, y + h / 2 + 13, sub, 's', an)
        else:
            self._text(tx, y + h / 2 + 4, title, 'b', an)
        return b

    def line(self, pts, kind='fg', label=None, at=None, anchor='middle', both=False, arrow=True):
        """Стрелка по точкам. label — 1–3 слова; at — (x, y) подписи, иначе у самого длинного отрезка."""
        assert kind in self.LINE_KINDS, kind
        self._net += 1
        self._segs(pts, self._net)
        self.tips = getattr(self, 'tips', {}); self.tips[self._net] = (pts[0], pts[-1])
        self.ends += [(pts[0], self._net), (pts[-1], self._net)]
        p = ' '.join(f'{x:g},{y:g}' for x, y in pts)
        mk = ''
        if arrow: mk += f' marker-end="url(#me-{kind})"'
        if both: mk += f' marker-start="url(#ms-{kind})"'
        self.o.append(f'<polyline class="ln {kind}" points="{p}"{mk}/>')
        if kind != 'plan':
            self.o.append(f'<polyline class="flow {kind}" points="{p}"/>')
        if label:
            if at is None:
                (x1, y1), (x2, y2) = max(zip(pts, pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
                at, anchor = (((x1 + x2) / 2, y1 - 6), 'middle') if y1 == y2 else ((x1 + 8, (y1 + y2) / 2 + 4), 'start')
            self.edge_label(at[0], at[1], label, anchor)

    def bus(self, pts, kind='fg'):
        """Общая шина без стрелки: несколько потоков сходятся в одну линию."""
        self._net += 1
        self._segs(pts, ('bus', self._net))
        p = ' '.join(f'{x:g},{y:g}' for x, y in pts)
        self.o.append(f'<polyline class="ln {kind}" points="{p}"/>')
        self.o.append(f'<polyline class="flow {kind}" points="{p}"/>')

    def edge_label(self, x, y, t, anchor='middle'):
        w = len(t) * CW_EDGE
        x0 = x - w / 2 if anchor == 'middle' else (x - w if anchor == 'end' else x)
        self.labels.append((t, x0, y - 9, x0 + w, y + 2))
        self._text(x, y, t, 'e', anchor)

    def _segs(self, pts, net):
        for a, b in zip(pts, pts[1:]):
            self.segs.append((a, b, net))

    # ---------- самопроверка
    def check(self):
        warn = []
        for t in self.texts:
            if '·' in t:
                warn.append(f'«·» в тексте: {t!r} — замените запятой или словами')
        for b in self.boxes:
            need = max(len(b.title) * CW_TITLE, len(b.sub or '') * CW_SUB) + 24
            if need > b.w:
                warn.append(f'текст не влезает в «{b.title}»: нужно ~{need:.0f}px, ширина {b.w}')
            if b.l < 0 or b.t < 0 or b.r > self.W or b.b > self.H:
                warn.append(f'«{b.title}» за краем холста')
        for i, a in enumerate(self.boxes):
            for b in self.boxes[i + 1:]:
                if a.l < b.r and b.l < a.r and a.t < b.b and b.t < a.b:
                    warn.append(f'блоки накладываются: «{a.title}» и «{b.title}»')
        for (p, q, net) in self.segs:
            for b in self.boxes:
                if _seg_hits_rect(p, q, b.l + 1, b.t + 1, b.r - 1, b.b - 1):
                    warn.append(f'линия проходит сквозь «{b.title}»: {p}→{q}')
        rects = [(b.l, b.t, b.r, b.b) for b in self.boxes] + self.zones
        for e, net in self.ends:
            if not any(_on_edge(e, r) for r in rects) and not any(_on_seg(e, p, q) for p, q, n in self.segs if n != net):
                warn.append(f'конец линии висит в воздухе: {e} — приведите к краю блока, зоны или к шине')
        for (p, q, net) in self.segs:
            if p[0] != q[0] and p[1] != q[1]:
                warn.append(f'косая линия {p}→{q} — ведите горизонтально и вертикально')
        n = 0
        for i, (p1, q1, n1) in enumerate(self.segs):
            for (p2, q2, n2) in self.segs[i + 1:]:
                if n1 != n2 and _proper_cross(p1, q1, p2, q2):
                    n += 1
                    warn.append(f'линии пересекаются: {p1}→{q1} и {p2}→{q2}')
        tips = getattr(self, 'tips', {})
        for i, (p1, q1, n1) in enumerate(self.segs):
            for (p2, q2, n2) in self.segs[i + 1:]:
                if n1 == n2 or not _overlap(p1, q1, p2, q2):
                    continue
                a, b = tips.get(n1), tips.get(n2)
                if a and b and (a[0] == b[0] or a[1] == b[1]):
                    continue  # общий ствол: развилка из одной точки или слияние в одну
                warn.append(f'линии идут друг по другу: {p1}→{q1} и {p2}→{q2} — не видно, где какая')
        for (t, x0, y0, x1, y1) in self.labels:
            for b in self.boxes:
                if x0 < b.r and b.l < x1 and y0 < b.b and b.t < y1:
                    warn.append(f'подпись «{t}» залезает на «{b.title}»')
        return warn

    # ---------- сборка
    def svg(self):
        d = ['<defs>']
        for k in self.LINE_KINDS:
            for pre in ('me', 'ms'):
                d.append(f'<marker id="{pre}-{k}" class="mk-{k}" viewBox="0 0 10 10" refX="9" refY="5" '
                         f'markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z"/></marker>')
        d.append('</defs>')
        return '\n'.join([f'<svg viewBox="0 0 {self.W:g} {self.H:g}" role="img" aria-label="{html.escape(self.aria)}">',
                          *d, *self.z, *self.o, '</svg>'])

    def save(self, out_html, title, legend=(), caption=None, min_width=1000):
        """legend: [('fg'|'acc'|'plan'|'data'|'ext'|'flow', 'что значит')] — только повторяющиеся кодировки."""
        sw = {'fg': '<i></i>', 'acc': '<i class="acc"></i>', 'plan': '<i class="dash"></i>',
              'data': '<b class="data"></b>', 'ext': '<b class="ext"></b>', 'flow': '<i class="flow"></i>'}
        leg = ''.join(f'<span>{sw[k]}{html.escape(t)}</span>' for k, t in legend)
        head = open(HEAD, encoding='utf-8').read()
        page = (head.replace('{{TITLE}}', html.escape(title)).replace('{{LEGEND}}', leg)
                .replace('{{MINW}}', str(min_width)))
        cap = f'<figcaption>{html.escape(caption)}</figcaption>' if caption else ''
        with open(out_html, 'w', encoding='utf-8') as f:
            f.write(page + self.svg() + cap + '</figure></div>\n</body>\n</html>\n')
        warn = self.check()
        for w in warn:
            print('ПРОВЕРКА:', w)
        print(f'{out_html}: блоков {len(self.boxes)}, предупреждений {len(warn)}')
        return warn


def _seg_hits_rect(p, q, l, t, r, b):
    (x1, y1), (x2, y2) = p, q
    if y1 == y2:
        return t < y1 < b and min(x1, x2) < r and max(x1, x2) > l
    if x1 == x2:
        return l < x1 < r and min(y1, y2) < b and max(y1, y2) > t
    return False


def _proper_cross(p1, q1, p2, q2):
    def hv(p, q):
        return 'h' if p[1] == q[1] else ('v' if p[0] == q[0] else None)
    a, b = hv(p1, q1), hv(p2, q2)
    if {a, b} != {'h', 'v'}:
        return False
    (hp, hq), (vp, vq) = ((p1, q1), (p2, q2)) if a == 'h' else ((p2, q2), (p1, q1))
    x, y = vp[0], hp[1]
    return min(hp[0], hq[0]) < x < max(hp[0], hq[0]) and min(vp[1], vq[1]) < y < max(vp[1], vq[1])


def _on_edge(e, r, tol=1.5):
    x, y = e; l, t, rr, b = r
    on_v = (abs(x - l) <= tol or abs(x - rr) <= tol) and t - tol <= y <= b + tol
    on_h = (abs(y - t) <= tol or abs(y - b) <= tol) and l - tol <= x <= rr + tol
    return on_v or on_h


def _on_seg(e, p, q, tol=1.5):
    x, y = e
    if p[1] == q[1]:
        return abs(y - p[1]) <= tol and min(p[0], q[0]) - tol <= x <= max(p[0], q[0]) + tol
    if p[0] == q[0]:
        return abs(x - p[0]) <= tol and min(p[1], q[1]) - tol <= y <= max(p[1], q[1]) + tol
    return False


def _overlap(p1, q1, p2, q2, min_len=3):
    if p1[1] == q1[1] == p2[1] == q2[1]:
        lo = max(min(p1[0], q1[0]), min(p2[0], q2[0])); hi = min(max(p1[0], q1[0]), max(p2[0], q2[0]))
        return hi - lo >= min_len
    if p1[0] == q1[0] == p2[0] == q2[0]:
        lo = max(min(p1[1], q1[1]), min(p2[1], q2[1])); hi = min(max(p1[1], q1[1]), max(p2[1], q2[1]))
        return hi - lo >= min_len
    return False

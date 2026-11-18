"""Пример генератора схемы. Скопируйте в проект (например, tools/diagram/gen.py) и меняйте.
Запуск: python3 -I gen.py out.html  → печатает предупреждения проверки.

Порядок: 1) сетка колонок, 2) зоны, 3) блоки, 4) линии, 5) save.
Координаты блоков берите из констант сетки, а точки линий — из блоков (b.right(), b.left() ...).
"""
import os
import sys

SKILL = os.path.expanduser('~/.claude/skills/system-diagram/scripts')
sys.path.insert(0, SKILL)
from diagram import Diagram  # noqa: E402

# ---------- сетка: колонки слева направо по пути данных
SRC_X, SRC_W = 20, 170      # источники (снаружи)
JOB_X, JOB_W = 280, 170     # сбор
BUS_X = 480                 # шина: потоки сходятся в одну линию
ARC_X, ARC_W = 510, 160     # архив
DB_X, DB_W = 720, 220       # хранилище
OUT_X, OUT_W = 1000, 170    # показ
USR_X, USR_W = 1240, 170    # люди (роли, не имена)
ROW0, ROW_H, ROW_GAP = 110, 40, 16
def row(i): return ROW0 + i * (ROW_H + ROW_GAP)

W, H = 1430, 470
d = Diagram(W, H, aria='Пример: два источника, сбор, сырой архив, база со сводками, дашборд для команды; копии в отдельном хранилище.')

# ---------- зоны (рисуются под блоками)
d.zone(250, 20, 960, 360, 'Сервер', kind='server', label_at='bottom')
d.zone(JOB_X - 10, ROW0 - 30, JOB_W + 20, 3 * ROW_H + 2 * ROW_GAP + 44, 'Сбор', kind='group')
d.zone(DB_X, ROW0 - 30, DB_W, 230, 'PostgreSQL', kind='data')

# ---------- блоки
src = [d.box(SRC_X, row(0), SRC_W, ROW_H, 'Сервис А'),
       d.box(SRC_X, row(1), SRC_W, ROW_H, 'Внешний API', kind='ext'),
       d.box(SRC_X, row(2), SRC_W, ROW_H, 'Старая система', kind='plan')]
job = [d.box(JOB_X, row(0), JOB_W, ROW_H, 'Сборщик А'),
       d.box(JOB_X, row(1), JOB_W, ROW_H, 'Сборщик Б'),
       d.box(JOB_X, row(2), JOB_W, ROW_H, 'Импорт истории', kind='plan')]
arc = d.box(ARC_X, row(0) - 5, ARC_W, 50, 'Сырой архив', 'только дописывается', kind='data')
core = d.box(DB_X + 15, row(0) - 2, DB_W - 30, 44, 'Данные источников')
mart = d.box(DB_X + 15, row(2), DB_W - 30, 44, 'Сводки', 'полные или неполные')
dash = d.box(OUT_X, row(2), OUT_W, 44, 'Дашборд', 'права по ролям')
team = d.box(USR_X, row(2), USR_W, 44, 'Команда', kind='role')
s3 = d.box(DB_X + 15, 400, DB_W - 30, 44, 'Копии', 'в другом городе')

# ---------- линии: источники → сборщики → шина → архив → база → сводки → дашборд
d.line([src[0].right(), job[0].left()])
d.line([src[1].right(), job[1].left()], kind='acc')
d.line([src[2].right(), job[2].left()], kind='plan', label='разово')
for j in job:
    d.bus([j.right(), (BUS_X, j.cy)])
d.bus([(BUS_X, job[2].cy), (BUS_X, arc.cy)])
d.line([(BUS_X, arc.cy), arc.left()])
d.line([arc.right(), core.left()])
d.line([core.bottom(), mart.top()], label='пересчёт', at=(core.cx + 8, (core.b + mart.t) / 2 + 4), anchor='start')
d.line([mart.right(), dash.left()], label='чтение')
d.line([team.left(), dash.right()], label='вход')
d.line([arc.bottom(), (arc.cx, s3.cy), s3.left()], label='сразу', at=(arc.cx + 8, 395), anchor='start')
d.line([(DB_X + 160, ROW0 - 30 + 230), (DB_X + 160, s3.t)], label='непрерывно', at=(DB_X + 168, 392), anchor='start')

d.save(sys.argv[1] if len(sys.argv) > 1 else 'diagram.html',
       title='Пример схемы',
       legend=[('fg', 'обычный поток'), ('acc', 'внешний сервис'), ('plan', 'разово или под вопросом'),
               ('data', 'хранилище'), ('flow', 'точки бегут по направлению данных')],
       caption='Данные идут слева направо: сбор, архив, база, показ. Копии уходят в отдельное хранилище.',
       min_width=1000)

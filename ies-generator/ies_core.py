# -*- coding: utf-8 -*-
"""
ies_core.py — разбор, пересчёт и запись файлов фотометрии IESNA LM-63.

Модуль не зависит от интерфейса: его можно использовать и отдельно.
"""

import math
import os
import re

# Однобайтовые кириллические кодировки, среди которых выбирает детектор.
CYRILLIC_ENCODINGS = ("cp1251", "koi8-r", "cp866", "iso-8859-5", "mac-cyrillic")

# Кодировка, в которой сохраняются новые файлы.
WRITE_ENCODING = "koi8-r"

VALUES_PER_LINE = 10  # сколько чисел писать в одной строке данных


class IESError(Exception):
    """Ошибка разбора файла IES."""


def _fmt(x):
    """Аккуратное представление числа: без лишних нулей в конце."""
    if x is None:
        return "0"
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    s = ("%.4f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def _fmt_cd(x):
    """Формат силы света: два знака после запятой."""
    return "%.2f" % x


def _fmt_angle(x):
    """Углы: как правило один знак после запятой (0.0, 22.5, 90.0)."""
    if abs(x - round(x, 1)) < 1e-9:
        return "%.1f" % x
    return _fmt(x)


def _fmt_size(x):
    """Габариты: три знака после запятой, как в исходных файлах."""
    if abs(x - round(x, 3)) < 1e-9:
        return "%.3f" % x
    return _fmt(x)


class IESFile(object):
    """Разобранный файл IES."""

    def __init__(self):
        self.encoding_in = None
        self.first_line = "IESNA:LM-63-2002"  # строка формата, если она есть
        self.keywords = []        # список [ключ, значение] в исходном порядке
        self.tilt_line = "TILT=NONE"
        self.tilt_body = []       # строки блока TILT, если TILT=INCLUDE

        self.n_lamps = 1
        self.lumens_per_lamp = 0.0
        self.multiplier = 1.0
        self.n_vert = 0
        self.n_horz = 0
        self.photometric_type = 1
        self.units_type = 2       # 1 — футы, 2 — метры
        self.width = 0.0
        self.length = 0.0
        self.height = 0.0

        self.ballast_factor = 1.0
        self.future_use = 1.0
        self.input_watts = 0.0

        self.vert_angles = []
        self.horz_angles = []
        self.candela = []         # candela[номер горизонт. угла][номер вертик. угла]

        self.source_path = None
        self.warnings = []

    # ------------------------------------------------------------------ чтение

    @staticmethod
    def read(path):
        raw = open(path, "rb").read()
        text, used = detect_encoding(raw)
        if text is None:
            raise IESError("Не удалось определить кодировку файла: %s" % path)

        obj = IESFile._parse(text)
        obj.encoding_in = used
        obj.source_path = path
        return obj

    @staticmethod
    def _parse(text):
        obj = IESFile()
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        # ---- ищем строку TILT
        tilt_idx = None
        for i, line in enumerate(lines):
            if line.strip().upper().startswith("TILT="):
                tilt_idx = i
                break
        if tilt_idx is None:
            raise IESError("В файле не найдена строка TILT= — это не файл IES LM-63.")

        header = lines[:tilt_idx]
        obj.tilt_line = lines[tilt_idx].strip()

        # ---- шапка: строка формата + ключевые слова [XXX]
        for line in header:
            s = line.rstrip()
            if not s.strip():
                continue
            m = re.match(r"^\s*\[([^\]]*)\]\s?(.*)$", s)
            if m:
                obj.keywords.append([m.group(1).strip().upper(), m.group(2).strip()])
            elif s.strip().upper().startswith("IESNA") or s.strip().upper().startswith("IES"):
                obj.first_line = s.strip()
            else:
                # нестандартная строка шапки — сохраняем как есть
                obj.keywords.append(["__RAW__", s.strip()])

        rest_lines = lines[tilt_idx + 1:]

        # ---- блок TILT=INCLUDE
        if obj.tilt_line.upper().replace(" ", "") == "TILT=INCLUDE":
            tilt_nums = []
            consumed = 0
            for line in rest_lines:
                consumed += 1
                obj.tilt_body.append(line.rstrip())
                tilt_nums.extend(_numbers(line))
                if len(tilt_nums) >= 2:
                    need = 2 + int(tilt_nums[1]) * 2
                    if len(tilt_nums) >= need:
                        break
            rest_lines = rest_lines[consumed:]

        # ---- числовая часть
        nums = []
        for line in rest_lines:
            nums.extend(_numbers(line))

        if len(nums) < 13:
            raise IESError("Числовая часть файла слишком короткая — файл повреждён.")

        obj.n_lamps = int(nums[0])
        obj.lumens_per_lamp = nums[1]
        obj.multiplier = nums[2]
        obj.n_vert = int(nums[3])
        obj.n_horz = int(nums[4])
        obj.photometric_type = int(nums[5])
        obj.units_type = int(nums[6])
        obj.width = nums[7]
        obj.length = nums[8]
        obj.height = nums[9]
        obj.ballast_factor = nums[10]
        obj.future_use = nums[11]
        obj.input_watts = nums[12]

        need = 13 + obj.n_vert + obj.n_horz + obj.n_vert * obj.n_horz
        if len(nums) < need:
            raise IESError(
                "Не хватает чисел: ожидалось %d, найдено %d. Файл повреждён." % (need, len(nums))
            )

        i = 13
        obj.vert_angles = nums[i:i + obj.n_vert]
        i += obj.n_vert
        obj.horz_angles = nums[i:i + obj.n_horz]
        i += obj.n_horz
        obj.candela = []
        for _ in range(obj.n_horz):
            obj.candela.append(nums[i:i + obj.n_vert])
            i += obj.n_vert

        return obj

    # ------------------------------------------------------------- вычисления

    def zonal_flux(self):
        """
        Световой поток по кривой силы света (зональный метод).
        Учитывает множитель. Результат — люмены.
        """
        if not self.candela:
            return 0.0

        total = 0.0
        nv = self.n_vert
        va = self.vert_angles
        ha = self.horz_angles

        for j in range(nv):
            # границы вертикальной зоны вокруг угла va[j]
            if nv == 1:
                lo, hi = 0.0, 180.0
            elif j == 0:
                lo = va[0]
                hi = (va[0] + va[1]) / 2.0
            elif j == nv - 1:
                lo = (va[j] + va[j - 1]) / 2.0
                hi = va[j]
            else:
                lo = (va[j] + va[j - 1]) / 2.0
                hi = (va[j] + va[j + 1]) / 2.0

            # крайние зоны расширяем до полюсов
            if j == 0 and abs(va[0]) < 1e-6:
                lo = 0.0
            if j == nv - 1 and abs(va[-1] - 180.0) < 1e-6:
                hi = 180.0

            lo = max(0.0, min(180.0, lo))
            hi = max(0.0, min(180.0, hi))
            if hi <= lo:
                continue

            omega = 2.0 * math.pi * (math.cos(math.radians(lo)) - math.cos(math.radians(hi)))

            # усреднение силы света по азимуту
            if self.n_horz <= 1:
                avg = self.candela[0][j]
            else:
                num = 0.0
                den = 0.0
                for k in range(self.n_horz):
                    if k == 0:
                        d_lo = ha[0]
                    else:
                        d_lo = (ha[k] + ha[k - 1]) / 2.0
                    if k == self.n_horz - 1:
                        d_hi = ha[-1]
                    else:
                        d_hi = (ha[k] + ha[k + 1]) / 2.0
                    w = d_hi - d_lo
                    if w <= 0:
                        w = 1e-9
                    num += self.candela[k][j] * w
                    den += w
                avg = num / den if den else 0.0

            total += avg * omega

        return total * self.multiplier

    def declared_flux(self):
        """Световой поток по полю «люмены на лампу» (с учётом числа ламп)."""
        if self.lumens_per_lamp is None:
            return 0.0
        if self.lumens_per_lamp < 0:
            return 0.0  # -1 означает абсолютную фотометрию
        return self.lumens_per_lamp * max(1, self.n_lamps)

    def efficacy(self, flux=None):
        """Световая отдача, лм/Вт."""
        f = self.declared_flux() if flux is None else flux
        if not self.input_watts:
            return None
        return f / self.input_watts

    def max_candela(self):
        """
        Наибольшая сила света в файле.
        Возвращает (значение в кд, вертикальный угол, горизонтальный угол).
        """
        best_val = 0.0
        best_v = None
        best_h = None
        for k, row in enumerate(self.candela):
            for j, c in enumerate(row):
                if c > best_val:
                    best_val = c
                    best_v = self.vert_angles[j]
                    best_h = self.horz_angles[k]
        return best_val * self.multiplier, best_v, best_h

    def axial_candela(self):
        """
        Осевая сила света — при вертикальном угле 0° (вниз по оси прибора).
        Если плоскостей несколько, берётся наибольшее из значений.
        """
        if not self.vert_angles or not self.candela:
            return 0.0
        # индекс угла, ближайшего к нулю
        j = min(range(len(self.vert_angles)), key=lambda i: abs(self.vert_angles[i]))
        value = max(row[j] for row in self.candela)
        return value * self.multiplier

    def luminous_area(self):
        """
        Площадь светового окна в квадратных метрах.

        По стандарту LM-63 отрицательные габариты означают круглую форму,
        поэтому такой случай считается как площадь круга или эллипса.
        Возвращает None, если габариты нулевые (точечный источник).
        """
        w = abs(self.width)
        l = abs(self.length)
        if w <= 0 or l <= 0:
            return None
        if self.width < 0 and self.length < 0:
            return math.pi * w * l / 4.0
        return w * l

    def luminance(self, intensity=None, area=None):
        """
        Габаритная яркость, кд/м² — сила света, делённая на площадь
        светового окна. По умолчанию берётся максимальная осевая сила
        света. Возвращает None, если площадь неизвестна.
        """
        if intensity is None:
            intensity = self.axial_candela()
        if area is None:
            area = self.luminous_area()
        if not area:
            return None
        return intensity / area

    def get_keyword(self, key):
        key = key.upper()
        for k, v in self.keywords:
            if k == key:
                return v
        return None

    def set_keyword(self, key, value, after=None, create=True):
        """
        Записать значение ключевого слова. Если поля нет — добавить.
        `after` — список ключей, после которых желательно вставить новое поле.
        """
        key = key.upper()
        for pair in self.keywords:
            if pair[0] == key:
                pair[1] = value
                return
        if not create:
            return
        pos = len(self.keywords)
        if after:
            for anchor in after:
                for idx, pair in enumerate(self.keywords):
                    if pair[0] == anchor.upper():
                        pos = idx + 1
                        break
                else:
                    continue
                break
        self.keywords.insert(pos, [key, value])

    def remove_keyword(self, key):
        key = key.upper()
        self.keywords = [p for p in self.keywords if p[0] != key]

    # ------------------------------------------------------------- пересчёт

    def rescale_to_flux(self, target_flux, source_flux):
        """
        Пересчитать силы света под новый световой поток.
        Множитель после пересчёта равен 1.00, поле «люмены на лампу» —
        целевому потоку.
        """
        if source_flux <= 0:
            raise IESError("Исходный световой поток должен быть больше нуля.")
        if target_flux <= 0:
            raise IESError("Заданный световой поток должен быть больше нуля.")

        k = (target_flux / source_flux) * self.multiplier
        self.candela = [[c * k for c in row] for row in self.candela]
        self.multiplier = 1.0
        self.n_lamps = 1
        self.lumens_per_lamp = target_flux

    def apply_color_factor(self, factor, scale_candela=True):
        """
        Пересчёт на другую цветность.

        Поле «люмены на лампу» умножается на коэффициент, множитель
        приводится к 1.00. Если scale_candela=True, кривая силы света
        масштабируется тем же коэффициентом — тогда файл остаётся
        внутренне согласованным.

        Возвращает (старый поток, новый поток).
        """
        if factor <= 0:
            raise IESError("Коэффициент должен быть больше нуля.")

        old_flux = self.declared_flux()

        k = factor if scale_candela else 1.0
        self.candela = [[c * self.multiplier * k for c in row] for row in self.candela]
        self.multiplier = 1.0

        if self.lumens_per_lamp > 0:
            self.lumens_per_lamp = self.lumens_per_lamp * factor
            self.n_lamps = 1
        else:
            # абсолютная фотометрия: поле люмен не используется
            pass

        return old_flux, self.declared_flux()

    # --------------------------------------------------------------- запись

    def to_text(self):
        out = []
        if self.first_line:
            out.append(self.first_line)

        for key, value in self.keywords:
            if key == "__RAW__":
                out.append(value)
            else:
                out.append("[%s] %s" % (key, value))

        out.append(self.tilt_line)
        if self.tilt_body:
            out.extend(self.tilt_body)

        out.append(" ".join([
            _fmt(self.n_lamps),
            _fmt(self.lumens_per_lamp),
            "%.2f" % self.multiplier,
            _fmt(self.n_vert),
            _fmt(self.n_horz),
            _fmt(self.photometric_type),
            _fmt(self.units_type),
            _fmt_size(self.width),
            _fmt_size(self.length),
            _fmt_size(self.height),
        ]))

        out.append(" ".join([
            "%.3f" % self.ballast_factor,
            _fmt(self.future_use),
            _fmt(self.input_watts),
        ]))

        out.extend(_wrap([_fmt_angle(a) for a in self.vert_angles]))
        out.extend(_wrap([_fmt_angle(a) for a in self.horz_angles]))
        for row in self.candela:
            out.extend(_wrap([_fmt_cd(c) for c in row]))

        return "\r\n".join(out) + "\r\n"

    def save(self, path, encoding=WRITE_ENCODING):
        """
        Сохранить файл. Возвращает список символов, которые не удалось
        закодировать в заданной кодировке (пустой список — всё в порядке).
        """
        text = self.to_text()
        bad = []
        try:
            data = text.encode(encoding)
        except UnicodeEncodeError:
            bad = sorted(set([ch for ch in text if not _encodable(ch, encoding)]))
            data = text.encode(encoding, errors="replace")
        with open(path, "wb") as f:
            f.write(data)
        return bad


# ---------------------------------------------------------------- утилиты


def _cyrillic_score(text):
    """
    Насколько текст похож на осмысленный русский.

    В неверно подобранной кириллической кодировке строчные и заглавные буквы
    меняются местами, поэтому доля строчных среди всех кириллических —
    надёжный признак правильной кодировки.
    """
    lower = 0
    upper = 0
    junk = 0
    for ch in text:
        code = ord(ch)
        if 0x0430 <= code <= 0x044F or ch == "ё":
            lower += 1
        elif 0x0410 <= code <= 0x042F or ch == "Ё":
            upper += 1
        elif code > 0x007F:
            # псевдографика, дингбаты и прочие следы неверной кодировки
            if 0x2500 <= code <= 0x25FF or 0x0080 <= code <= 0x00BF:
                junk += 1
    cyr = lower + upper
    if cyr == 0:
        return -junk * 0.5
    return (float(lower) / cyr) * cyr - junk * 0.5


def detect_encoding(raw):
    """
    Определить кодировку и декодировать содержимое.
    Возвращает пару (текст, название кодировки).
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"

    # чистый ASCII — кодировка не имеет значения
    if all(b < 0x80 for b in bytearray(raw)):
        return raw.decode("ascii"), "ascii"

    # строгая проверка на UTF-8: случайный однобайтовый текст её не проходит
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    best_text = None
    best_enc = None
    best_score = None
    for enc in CYRILLIC_ENCODINGS:
        try:
            candidate = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        score = _cyrillic_score(candidate)
        if best_score is None or score > best_score:
            best_score, best_text, best_enc = score, candidate, enc

    if best_text is None:
        return raw.decode("latin-1"), "latin-1"
    return best_text, best_enc


def _encodable(ch, encoding):
    try:
        ch.encode(encoding)
        return True
    except UnicodeEncodeError:
        return False


def _numbers(line):
    """Вытащить из строки все числа."""
    # обрезаем возможные комментарии
    res = []
    for token in line.replace(",", " ").split():
        try:
            res.append(float(token))
        except ValueError:
            pass
    return res


def _wrap(items, per_line=VALUES_PER_LINE):
    lines = []
    for i in range(0, len(items), per_line):
        lines.append(" ".join(items[i:i + per_line]))
    return lines


def safe_filename(name):
    """Убрать из имени файла символы, запрещённые в Windows."""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.rstrip(" .")
    return name or "unnamed"


def replace_trailing_code(text, new_code):
    """
    Заменить трёхзначное число в конце строки на новое.

    'DPO12-38-003 Universal Soft 840' + '930'
        -> ('DPO12-38-003 Universal Soft 930', True)

    Если трёхзначного числа в конце нет, строка возвращается без
    изменений, а второй элемент пары равен False.
    """
    if text is None:
        return text, False
    m = re.search(r"(\d{3})(\s*)$", text)
    if not m:
        return text, False
    return text[:m.start(1)] + new_code + m.group(2), True


def list_ies_files(folder):
    res = []
    for fn in sorted(os.listdir(folder)):
        if fn.lower().endswith(".ies"):
            res.append(os.path.join(folder, fn))
    return res

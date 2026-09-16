# -*- coding: utf-8 -*-
"""
ies_app.py — генератор файлов IES.

Возможности:
  1. Создание пачки файлов IES из базового с пересчётом светового потока.
  2. Отчёты в Excel по созданным файлам и по произвольной папке.
  3. Расчёт габаритной яркости по заданному размеру светового окна.
  4. Пересчёт папки файлов на другую цветность.

Сборка в .exe описана в файле «Инструкция.md».
"""

import os
import re
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ies_core import IESError, IESFile, replace_trailing_code, safe_filename
import ies_report

APP_TITLE = "Генератор IES-файлов  ·  ASTZ"
VERSION = "1.2"


# --------------------------------------------------------------- утилиты ввода

def parse_number(text, field_name, allow_zero=False):
    """Прочитать число из поля ввода. Принимает и точку, и запятую."""
    s = (text or "").strip().replace(",", ".").replace(" ", "")
    if not s:
        raise ValueError("Поле «%s» не заполнено." % field_name)
    try:
        value = float(s)
    except ValueError:
        raise ValueError("В поле «%s» введено не число: %s" % (field_name, text))
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError("Значение в поле «%s» должно быть больше нуля." % field_name)
    return value


def read_lines(widget):
    """Непустые строки из многострочного поля."""
    raw = widget.get("1.0", "end").replace("\r\n", "\n").split("\n")
    return [line.strip() for line in raw if line.strip()]


def device_name(ies, path):
    """Название прибора: [LUMINAIRE], иначе [LUMCAT], иначе имя файла."""
    for key in ("LUMINAIRE", "LUMCAT"):
        value = (ies.get_keyword(key) or "").strip()
        if value:
            return value
    return os.path.splitext(os.path.basename(path))[0]


def make_log(parent, height=10, title="Журнал"):
    """Создать рамку с текстовым журналом и полосой прокрутки."""
    box = ttk.Labelframe(parent, text=title, padding=6)
    widget = tk.Text(box, height=height, wrap="word", font=("Consolas", 9),
                     background="#fbfbfb")
    sb = ttk.Scrollbar(box, command=widget.yview)
    widget.configure(yscrollcommand=sb.set, state="disabled")
    sb.pack(side="right", fill="y")
    widget.pack(side="left", fill="both", expand=True)
    widget.tag_configure("ok", foreground="#1a7f37")
    widget.tag_configure("warn", foreground="#b26a00")
    widget.tag_configure("err", foreground="#c0392b")
    return box, widget


# ------------------------------------------------------- диалог выбора потока

class FluxChoiceDialog(tk.Toplevel):
    """Спрашивает, какой поток считать исходным при расхождении значений."""

    def __init__(self, parent, declared, zonal):
        tk.Toplevel.__init__(self, parent)
        self.title("Расхождение светового потока")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        diff = abs(declared - zonal)
        pct = (diff / zonal * 100.0) if zonal else 0.0

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(
            frm,
            text="Значения светового потока в базовом файле не совпадают.",
            font=("Segoe UI", 10, "bold"),
            wraplength=430,
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            frm,
            text="Расхождение: %.1f лм (%.2f %%). Выберите, какое значение "
                 "принять за исходный поток для пересчёта." % (diff, pct),
            wraplength=430,
        ).pack(anchor="w", pady=(0, 12))

        self.var = tk.StringVar(value="zonal")

        ttk.Radiobutton(
            frm,
            text="По кривой силы света (зональный метод):  %.1f лм" % zonal,
            variable=self.var, value="zonal",
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            frm,
            text="Из поля «люмены на лампу»:  %.1f лм" % declared,
            variable=self.var, value="declared",
        ).pack(anchor="w", pady=2)

        ttk.Label(
            frm,
            text="Рекомендуется зональный метод: он описывает реальную кривую, "
                 "записанную в файле.",
            wraplength=430, foreground="#555555",
        ).pack(anchor="w", pady=(10, 14))

        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="Отмена", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Продолжить", command=self._ok).pack(side="right", padx=(0, 8))

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.update_idletasks()
        self._center(parent)
        self.wait_window(self)

    def _center(self, parent):
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    def _ok(self):
        self.result = self.var.get()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ------------------------------------------------------------ основное окно

class App(tk.Tk):

    def __init__(self):
        tk.Tk.__init__(self)
        self.title("%s  v%s" % (APP_TITLE, VERSION))
        self.geometry("1020x790")
        self.minsize(940, 700)

        self.base_ies = None          # разобранный базовый файл
        self.created_items = []       # сводка по последней генерации
        self.lum_files = []           # файлы для расчёта габаритной яркости

        self._build_style()
        self._build_ui()

    # ------------------------------------------------------------- оформление

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("TLabel", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    # -------------------------------------------------------------- интерфейс

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_make = ttk.Frame(nb, padding=10)
        self.tab_report = ttk.Frame(nb, padding=10)
        self.tab_lum = ttk.Frame(nb, padding=10)
        self.tab_color = ttk.Frame(nb, padding=10)

        nb.add(self.tab_make, text="  Создание файлов IES  ")
        nb.add(self.tab_report, text="  Отчёты Excel  ")
        nb.add(self.tab_lum, text="  Габаритная яркость  ")
        nb.add(self.tab_color, text="  Пересчёт на другую цветность  ")

        self._build_tab_make(self.tab_make)
        self._build_tab_report(self.tab_report)
        self._build_tab_luminance(self.tab_lum)
        self._build_tab_color(self.tab_color)

        self.status = tk.StringVar(value="Готово. Выберите базовый файл IES.")
        bar = ttk.Frame(self)
        bar.pack(fill="x", side="bottom")
        ttk.Separator(bar).pack(fill="x")
        ttk.Label(bar, textvariable=self.status, padding=(10, 4)).pack(anchor="w")

    # --- вкладка 1: создание -------------------------------------------------

    def _build_tab_make(self, root):
        box1 = ttk.Labelframe(root, text="1. Базовый файл IES", padding=8)
        box1.pack(fill="x")

        line = ttk.Frame(box1)
        line.pack(fill="x")
        self.var_base = tk.StringVar()
        ttk.Entry(line, textvariable=self.var_base).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Обзор…", command=self.pick_base, width=12).pack(side="left", padx=(6, 0))

        self.base_info = tk.Text(box1, height=7, wrap="word", relief="flat",
                                 background="#f4f4f4", font=("Consolas", 9))
        self.base_info.pack(fill="x", pady=(8, 0))
        self.base_info.configure(state="disabled")

        box2 = ttk.Labelframe(root, text="2. Параметры новых файлов", padding=8)
        box2.pack(fill="x", pady=(10, 0))

        grid = ttk.Frame(box2)
        grid.pack(fill="x")

        self.var_flux = tk.StringVar()
        self.var_watts = tk.StringVar()
        self.var_len = tk.StringVar()
        self.var_wid = tk.StringVar()
        self.var_hgt = tk.StringVar()

        fields = [
            ("Световой поток, лм", self.var_flux, 0, 0),
            ("Мощность, Вт", self.var_watts, 0, 1),
            ("Длина, м", self.var_len, 1, 0),
            ("Ширина, м", self.var_wid, 1, 1),
            ("Высота, м", self.var_hgt, 1, 2),
        ]
        for text, var, row, col in fields:
            cell = ttk.Frame(grid)
            cell.grid(row=row, column=col, sticky="w", padx=(0, 24), pady=4)
            ttk.Label(cell, text=text).pack(anchor="w")
            ttk.Entry(cell, textvariable=var, width=18).pack(anchor="w")

        opts = ttk.Frame(box2)
        opts.pack(fill="x", pady=(8, 0))
        self.var_drop_lumcat = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts,
            text="Удалять строку [LUMCAT] целиком (иначе оставить её пустой)",
            variable=self.var_drop_lumcat,
        ).pack(anchor="w")

        tol = ttk.Frame(opts)
        tol.pack(anchor="w", pady=(6, 0))
        ttk.Label(tol, text="Порог расхождения потоков, %:").pack(side="left")
        self.var_tol = tk.StringVar(value="1.0")
        ttk.Entry(tol, textvariable=self.var_tol, width=8).pack(side="left", padx=(6, 0))

        box3 = ttk.Labelframe(root, text="3. Названия (одна строка — один файл)", padding=8)
        box3.pack(fill="both", expand=True, pady=(10, 0))

        cols = ttk.Frame(box3)
        cols.pack(fill="both", expand=True)

        left = ttk.Frame(cols)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ttk.Label(left, text="Имена файлов (латиница, без .ies)").pack(anchor="w")
        self.txt_files = tk.Text(left, height=8, font=("Consolas", 9), undo=True)
        self.txt_files.pack(fill="both", expand=True)

        right = ttk.Frame(cols)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ttk.Label(right, text="Названия приборов для поля [LUMINAIRE]").pack(anchor="w")
        self.txt_names = tk.Text(right, height=8, font=("Consolas", 9), undo=True)
        self.txt_names.pack(fill="both", expand=True)

        box4 = ttk.Labelframe(root, text="4. Папка для сохранения", padding=8)
        box4.pack(fill="x", pady=(10, 0))
        line = ttk.Frame(box4)
        line.pack(fill="x")
        self.var_out = tk.StringVar()
        ttk.Entry(line, textvariable=self.var_out).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Обзор…", command=self.pick_out, width=12).pack(side="left", padx=(6, 0))

        run = ttk.Frame(root)
        run.pack(fill="x", pady=(10, 0))
        ttk.Button(run, text="Создать файлы IES", style="Accent.TButton",
                   command=self.do_create).pack(side="left", ipady=4, ipadx=10)
        ttk.Button(run, text="Очистить журнал",
                   command=lambda: self.clear(self.log)).pack(side="left", padx=8)

        box, self.log = make_log(root, height=8)
        box.pack(fill="both", expand=True, pady=(10, 0))

    # --- вкладка 2: отчёты ---------------------------------------------------

    def _build_tab_report(self, root):
        box1 = ttk.Labelframe(
            root, text="Отчёт 1. Сводка по файлам, созданным в этом сеансе", padding=10)
        box1.pack(fill="x")
        ttk.Label(
            box1,
            text="Столбцы: Название · Световой поток · Мощность · Световая отдача ·\n"
                 "Длина · Ширина · Макс. сила света · Габаритная яркость, кд/м².\n"
                 "Кнопка активна после создания файлов на первой вкладке.",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        self.btn_rep1 = ttk.Button(
            box1, text="Выгрузить сводку в Excel", command=self.do_report_created,
            state="disabled")
        self.btn_rep1.pack(anchor="w", ipady=3, ipadx=6)

        box2 = ttk.Labelframe(root, text="Отчёт 2. Анализ папки с файлами IES", padding=10)
        box2.pack(fill="x", pady=(14, 0))
        ttk.Label(
            box2,
            text="Столбцы: Название · Световой поток · Мощность · Световая отдача ·\n"
                 "Длина · Ширина · Высота (м) · Макс. сила света · Габаритная яркость, кд/м².\n"
                 "Одна строка — один файл IES.",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        line = ttk.Frame(box2)
        line.pack(fill="x")
        self.var_scan = tk.StringVar()
        ttk.Entry(line, textvariable=self.var_scan).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Обзор…", command=self.pick_scan, width=12).pack(side="left", padx=(6, 0))

        ttk.Button(box2, text="Сканировать папку и выгрузить в Excel",
                   command=self.do_report_scan).pack(anchor="w", pady=(10, 0), ipady=3, ipadx=6)

        box, self.log2 = make_log(root, height=12, title="Журнал отчётов")
        box.pack(fill="both", expand=True, pady=(14, 0))

    # --- вкладка 3: габаритная яркость ---------------------------------------

    def _build_tab_luminance(self, root):
        box1 = ttk.Labelframe(root, text="1. Файлы IES для расчёта", padding=8)
        box1.pack(fill="both", expand=True)

        btns = ttk.Frame(box1)
        btns.pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Выбрать файлы IES…", command=self.pick_lum_files,
                   width=22).pack(side="left")
        ttk.Button(btns, text="Добавить ещё…", command=self.add_lum_files,
                   width=18).pack(side="left", padx=6)
        ttk.Button(btns, text="Очистить список", command=self.clear_lum_files,
                   width=18).pack(side="left")

        holder = ttk.Frame(box1)
        holder.pack(fill="both", expand=True)
        self.lst_lum = tk.Listbox(holder, height=9, font=("Consolas", 9),
                                  selectmode="extended")
        sb = ttk.Scrollbar(holder, command=self.lst_lum.yview)
        self.lst_lum.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lst_lum.pack(side="left", fill="both", expand=True)

        box2 = ttk.Labelframe(root, text="2. Размер светового окна", padding=8)
        box2.pack(fill="x", pady=(10, 0))

        grid = ttk.Frame(box2)
        grid.pack(anchor="w")
        self.var_win_len = tk.StringVar()
        self.var_win_wid = tk.StringVar()
        for text, var, col in (("Длина, м", self.var_win_len, 0),
                               ("Ширина, м", self.var_win_wid, 1)):
            cell = ttk.Frame(grid)
            cell.grid(row=0, column=col, sticky="w", padx=(0, 24))
            ttk.Label(cell, text=text).pack(anchor="w")
            ttk.Entry(cell, textvariable=var, width=18).pack(anchor="w")

        ttk.Button(box2, text="Подставить размеры из первого файла",
                   command=self.fill_window_from_file).pack(anchor="w", pady=(8, 0))

        ttk.Label(
            box2,
            text="Габаритная яркость = максимальная осевая сила света / площадь светового окна.",
            foreground="#555555",
        ).pack(anchor="w", pady=(8, 0))

        run = ttk.Frame(root)
        run.pack(fill="x", pady=(12, 0))
        ttk.Button(run, text="Рассчитать и выгрузить в Excel", style="Accent.TButton",
                   command=self.do_luminance).pack(side="left", ipady=4, ipadx=10)
        ttk.Button(run, text="Очистить журнал",
                   command=lambda: self.clear(self.log3)).pack(side="left", padx=8)

        box, self.log3 = make_log(root, height=10, title="Журнал расчёта")
        box.pack(fill="both", expand=True, pady=(10, 0))

    # --- вкладка 4: пересчёт на цветность ------------------------------------

    def _build_tab_color(self, root):
        box1 = ttk.Labelframe(root, text="1. Папка с исходными файлами IES", padding=8)
        box1.pack(fill="x")
        line = ttk.Frame(box1)
        line.pack(fill="x")
        self.var_color_dir = tk.StringVar()
        ttk.Entry(line, textvariable=self.var_color_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Обзор…", command=self.pick_color_dir,
                   width=12).pack(side="left", padx=(6, 0))
        ttk.Label(box1, text="Обрабатываются все файлы .ies в этой папке.",
                  foreground="#555555").pack(anchor="w", pady=(6, 0))

        box2 = ttk.Labelframe(root, text="2. Параметры пересчёта", padding=8)
        box2.pack(fill="x", pady=(10, 0))

        grid = ttk.Frame(box2)
        grid.pack(anchor="w")

        self.var_factor = tk.StringVar()
        self.var_code = tk.StringVar()
        self.var_subdir = tk.StringVar()

        cell = ttk.Frame(grid)
        cell.grid(row=0, column=0, sticky="w", padx=(0, 24))
        ttk.Label(cell, text="Коэффициент для светового потока").pack(anchor="w")
        ttk.Entry(cell, textvariable=self.var_factor, width=18).pack(anchor="w")

        cell = ttk.Frame(grid)
        cell.grid(row=0, column=1, sticky="w", padx=(0, 24))
        ttk.Label(cell, text="Новый код цветности (3 цифры)").pack(anchor="w")
        ttk.Entry(cell, textvariable=self.var_code, width=18).pack(anchor="w")

        cell = ttk.Frame(grid)
        cell.grid(row=0, column=2, sticky="w")
        ttk.Label(cell, text="Имя новой папки").pack(anchor="w")
        ttk.Entry(cell, textvariable=self.var_subdir, width=26).pack(anchor="w")

        ttk.Label(
            box2,
            text="Новая папка будет создана внутри папки с исходными файлами.\n"
                 "Код цветности заменяется в конце названия из поля [LUMINAIRE] "
                 "и в конце имени файла.\n"
                 "Если поле [LUMINAIRE] пустое, название переносится в него "
                 "из поля [LUMCAT].",
            foreground="#555555", justify="left",
        ).pack(anchor="w", pady=(8, 0))

        opts = ttk.Frame(box2)
        opts.pack(fill="x", pady=(8, 0))

        self.var_scale_cd = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts,
            text="Пересчитывать силы света вместе с потоком (рекомендуется)",
            variable=self.var_scale_cd,
        ).pack(anchor="w")

        self.var_fix_lumcat = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts,
            text="Менять код цветности также в поле [LUMCAT]",
            variable=self.var_fix_lumcat,
        ).pack(anchor="w")

        run = ttk.Frame(root)
        run.pack(fill="x", pady=(12, 0))
        ttk.Button(run, text="Пересчитать на другую цветность", style="Accent.TButton",
                   command=self.do_color_shift).pack(side="left", ipady=4, ipadx=10)
        ttk.Button(run, text="Очистить журнал",
                   command=lambda: self.clear(self.log4)).pack(side="left", padx=8)

        box, self.log4 = make_log(root, height=14, title="Журнал пересчёта")
        box.pack(fill="both", expand=True, pady=(10, 0))

    # ------------------------------------------------------------------ журнал

    def _write(self, widget, text, tag=None):
        widget.configure(state="normal")
        widget.insert("end", text + "\n", tag or ())
        widget.see("end")
        widget.configure(state="disabled")
        self.update_idletasks()

    def say(self, text, tag=None):
        self._write(self.log, text, tag)

    def say2(self, text, tag=None):
        self._write(self.log2, text, tag)

    def say3(self, text, tag=None):
        self._write(self.log3, text, tag)

    def say4(self, text, tag=None):
        self._write(self.log4, text, tag)

    def clear(self, widget):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    # ------------------------------------------------------------- выбор путей

    def pick_base(self):
        path = filedialog.askopenfilename(
            title="Выберите базовый файл IES",
            filetypes=[("Файлы IES", "*.ies *.IES"), ("Все файлы", "*.*")])
        if path:
            self.var_base.set(path)
            self.load_base(path)

    def pick_out(self):
        path = filedialog.askdirectory(title="Папка для новых файлов IES")
        if path:
            self.var_out.set(path)

    def pick_scan(self):
        path = filedialog.askdirectory(title="Папка с файлами IES для анализа")
        if path:
            self.var_scan.set(path)

    def pick_color_dir(self):
        path = filedialog.askdirectory(title="Папка с файлами IES для пересчёта")
        if path:
            self.var_color_dir.set(path)

    # ------------------------------------------- список файлов для яркости

    def _ask_lum_files(self):
        return filedialog.askopenfilenames(
            title="Выберите файлы IES (можно несколько)",
            filetypes=[("Файлы IES", "*.ies *.IES"), ("Все файлы", "*.*")])

    def pick_lum_files(self):
        paths = self._ask_lum_files()
        if paths:
            self.lum_files = list(paths)
            self._refresh_lum_list()

    def add_lum_files(self):
        paths = self._ask_lum_files()
        if not paths:
            return
        for p in paths:
            if p not in self.lum_files:
                self.lum_files.append(p)
        self._refresh_lum_list()

    def clear_lum_files(self):
        self.lum_files = []
        self._refresh_lum_list()

    def _refresh_lum_list(self):
        self.lst_lum.delete(0, "end")
        for p in self.lum_files:
            self.lst_lum.insert("end", os.path.basename(p))
        self.status.set("Файлов для расчёта яркости: %d" % len(self.lum_files))

    def fill_window_from_file(self):
        if not self.lum_files:
            messagebox.showinfo("Нет файлов", "Сначала выберите файлы IES.")
            return
        try:
            ies = IESFile.read(self.lum_files[0])
        except (IESError, OSError) as exc:
            messagebox.showerror("Ошибка чтения", str(exc))
            return
        self.var_win_len.set(str(abs(ies.length)))
        self.var_win_wid.set(str(abs(ies.width)))
        self.say3("Размеры подставлены из файла %s: длина %s м, ширина %s м"
                  % (os.path.basename(self.lum_files[0]), abs(ies.length), abs(ies.width)))

    # -------------------------------------------------------- загрузка базы

    def load_base(self, path):
        try:
            ies = IESFile.read(path)
        except (IESError, OSError) as exc:
            self.base_ies = None
            messagebox.showerror("Ошибка чтения", str(exc))
            self.say("Не удалось прочитать файл: %s" % exc, "err")
            return

        self.base_ies = ies
        declared = ies.declared_flux()
        zonal = ies.zonal_flux()
        imax, vang, hang = ies.max_candela()
        iaxial = ies.axial_candela()
        area = ies.luminous_area()
        lum = ies.luminance(iaxial, area)

        info = [
            "Кодировка входного файла: %s" % ies.encoding_in,
            "Углы: вертикальных %d (%s…%s°), горизонтальных %d (%s…%s°)"
            % (ies.n_vert, ies.vert_angles[0], ies.vert_angles[-1],
               ies.n_horz, ies.horz_angles[0], ies.horz_angles[-1]),
            "Люмены на лампу: %s     Множитель: %s     Мощность: %s Вт"
            % (declared, ies.multiplier, ies.input_watts),
            "Поток по кривой силы света: %.1f лм" % zonal,
            "Макс. осевая сила света: %.1f кд     Габаритная яркость: %s"
            % (iaxial, ("%.0f кд/м²" % lum) if lum else "—"),
            "Наибольшая сила света в файле: %.1f кд (при %s° / %s°)"
            % (imax, vang, hang),
            "Габариты в файле: ширина %s · длина %s · высота %s (единицы: %s)"
            % (ies.width, ies.length, ies.height,
               "метры" if ies.units_type == 2 else "футы"),
            "[LUMCAT] %s   |   [LUMINAIRE] %s   |   [MANUFAC] %s"
            % (ies.get_keyword("LUMCAT") or "—",
               ies.get_keyword("LUMINAIRE") or "—",
               ies.get_keyword("MANUFAC") or "—"),
        ]
        self.base_info.configure(state="normal")
        self.base_info.delete("1.0", "end")
        self.base_info.insert("1.0", "\n".join(info))
        self.base_info.configure(state="disabled")

        self.say("Загружен базовый файл: %s" % os.path.basename(path), "ok")

        if not self.var_len.get():
            self.var_len.set(str(ies.length))
        if not self.var_wid.get():
            self.var_wid.set(str(ies.width))
        if not self.var_hgt.get():
            self.var_hgt.set(str(ies.height))
        if not self.var_watts.get():
            self.var_watts.set(str(ies.input_watts))

        if abs(ies.ballast_factor - 1.0) > 1e-6:
            msg = ("Коэффициент балласта в базовом файле равен %s, а не 1.00. "
                   "Он будет сохранён без изменений." % ies.ballast_factor)
            self.say("ВНИМАНИЕ: " + msg, "warn")
            messagebox.showwarning("Коэффициент балласта", msg)

        if ies.units_type != 2:
            self.say("ВНИМАНИЕ: в файле указаны футы, а не метры (units type = %d). "
                     "Габариты будут записаны как есть." % ies.units_type, "warn")

        if abs(ies.multiplier - 1.0) > 1e-9:
            self.say("Множитель %s будет учтён в силах света, в новых файлах "
                     "он станет 1.00." % ies.multiplier)

        self.status.set("Базовый файл загружен: %s" % os.path.basename(path))

    # ------------------------------------------------------- исходный поток

    def resolve_source_flux(self, ies):
        """Вернуть исходный поток для пересчёта или None, если отменено."""
        declared = ies.declared_flux()
        zonal = ies.zonal_flux()

        try:
            tol = float(self.var_tol.get().replace(",", "."))
        except ValueError:
            tol = 1.0

        if declared <= 0:
            self.say("В поле «люмены на лампу» нет пригодного значения (%s). "
                     "Использован зональный расчёт: %.1f лм"
                     % (ies.lumens_per_lamp, zonal), "warn")
            return zonal

        diff_pct = abs(declared - zonal) / zonal * 100.0 if zonal else 0.0
        if diff_pct <= tol:
            self.say("Значения потока сходятся (расхождение %.2f %%). "
                     "Исходный поток: %.1f лм" % (diff_pct, zonal))
            return zonal

        dlg = FluxChoiceDialog(self, declared, zonal)
        if dlg.result is None:
            return None
        if dlg.result == "declared":
            self.say("Выбран поток из поля «люмены на лампу»: %.1f лм" % declared)
            return declared
        self.say("Выбран поток по кривой силы света: %.1f лм" % zonal)
        return zonal

    # ---------------------------------------------------------- создание IES

    def do_create(self):
        try:
            self._create()
        except ValueError as exc:
            messagebox.showerror("Проверьте ввод", str(exc))
            self.say(str(exc), "err")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", "%s\n\n%s" % (exc, traceback.format_exc()))
            self.say("Ошибка: %s" % exc, "err")

    def _create(self):
        if self.base_ies is None:
            raise ValueError("Сначала выберите базовый файл IES.")

        out_dir = self.var_out.get().strip()
        if not out_dir:
            raise ValueError("Не указана папка для сохранения.")
        if not os.path.isdir(out_dir):
            raise ValueError("Папка для сохранения не найдена:\n%s" % out_dir)

        base_path = os.path.abspath(self.base_ies.source_path or "")
        if os.path.dirname(base_path) == os.path.abspath(out_dir):
            if not messagebox.askyesno(
                    "Одна и та же папка",
                    "Папка сохранения совпадает с папкой базового файла.\n"
                    "Базовый файл может быть перезаписан. Продолжить?"):
                return

        flux = parse_number(self.var_flux.get(), "Световой поток, лм")
        watts = parse_number(self.var_watts.get(), "Мощность, Вт")
        length = parse_number(self.var_len.get(), "Длина, м")
        width = parse_number(self.var_wid.get(), "Ширина, м")
        height = parse_number(self.var_hgt.get(), "Высота, м")

        for value, label in ((length, "Длина"), (width, "Ширина"), (height, "Высота")):
            if value > 10:
                if not messagebox.askyesno(
                        "Проверьте габариты",
                        "%s = %s м. Это похоже на миллиметры.\n"
                        "Габариты нужно задавать в метрах. Продолжить?" % (label, value)):
                    return
                break

        file_names = read_lines(self.txt_files)
        lum_names = read_lines(self.txt_names)

        if not file_names:
            raise ValueError("Не заполнен список имён файлов.")
        if len(file_names) != len(lum_names):
            raise ValueError(
                "Число строк не совпадает: имён файлов — %d, названий приборов — %d.\n"
                "В обоих полях должно быть одинаковое количество строк."
                % (len(file_names), len(lum_names)))

        dupes = set(n for n in file_names if file_names.count(n) > 1)
        if dupes:
            raise ValueError("Повторяющиеся имена файлов: %s" % ", ".join(sorted(dupes)))

        source_flux = self.resolve_source_flux(self.base_ies)
        if source_flux is None:
            self.say("Создание отменено пользователем.", "warn")
            return

        self.say("")
        self.say("— Создание файлов: поток %s лм, мощность %s Вт, "
                 "габариты %s × %s × %s м —" % (flux, watts, length, width, height))

        created = []
        errors = 0

        for fname, lname in zip(file_names, lum_names):
            try:
                ies = IESFile.read(self.base_ies.source_path)
                ies.rescale_to_flux(flux, source_flux)

                ies.length = length
                ies.width = width
                ies.height = height
                ies.input_watts = watts

                if self.var_drop_lumcat.get():
                    ies.remove_keyword("LUMCAT")
                else:
                    ies.set_keyword("LUMCAT", "", create=False)

                ies.set_keyword("LUMINAIRE", lname, after=["LUMCAT", "MANUFAC", "OTHER"])

                manuf = (ies.get_keyword("MANUFAC") or "").strip()
                if manuf.upper() != "ASTZ":
                    ies.set_keyword("MANUFAC", "ASTZ", after=["OTHER", "TESTLAB"])
                    if manuf:
                        self.say("  [MANUFAC] «%s» → «ASTZ»" % manuf)

                safe = safe_filename(fname)
                if safe != fname:
                    self.say("  Имя файла «%s» изменено на «%s» "
                             "(недопустимые символы)." % (fname, safe), "warn")

                out_path = os.path.join(out_dir, safe + ".IES")
                bad = ies.save(out_path)
                if bad:
                    self.say("  ВНИМАНИЕ: символы %s не кодируются в koi8-r и заменены "
                             "на «?» в файле %s" % (" ".join(bad), safe), "warn")

                check = IESFile.read(out_path)
                check_flux = check.zonal_flux()
                iaxial = check.axial_candela()
                imax, vang, _ = check.max_candela()
                lum = check.luminance()

                if imax > iaxial * 1.01:
                    self.say("     наибольшая сила света %.1f кд при %s° выше осевой "
                             "%.1f кд; в расчёт берётся осевая"
                             % (imax, vang, iaxial), "warn")

                created.append({
                    "name": lname, "file": safe + ".IES",
                    "flux": flux, "watts": watts,
                    "length": length, "width": width, "imax": round(iaxial, 1),
                })
                self.say("  ✓ %s.IES — %s — поток %.1f лм — яркость %s"
                         % (safe, lname, check_flux,
                            ("%.0f кд/м²" % lum) if lum else "—"), "ok")

            except Exception as exc:  # noqa: BLE001
                errors += 1
                self.say("  ✗ %s — ошибка: %s" % (fname, exc), "err")

        self.created_items = created
        if created:
            self.btn_rep1.configure(state="normal")

        self.say("Готово: создано файлов — %d, ошибок — %d." % (len(created), errors),
                 "ok" if not errors else "warn")
        self.status.set("Создано файлов: %d" % len(created))

        if created:
            messagebox.showinfo(
                "Готово",
                "Создано файлов: %d\nОшибок: %d\n\nПапка:\n%s"
                % (len(created), errors, out_dir))

    # ------------------------------------------------------------- отчёт 1

    def do_report_created(self):
        if not self.created_items:
            messagebox.showinfo("Нет данных", "Сначала создайте файлы IES на первой вкладке.")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить сводку", defaultextension=".xlsx",
            initialfile="Сводка_созданные_IES.xlsx",
            filetypes=[("Книга Excel", "*.xlsx")])
        if not path:
            return
        try:
            ies_report.export_created(path, self.created_items)
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения",
                                 "Не удалось записать файл.\n"
                                 "Возможно, он открыт в Excel.\n\n%s" % exc)
            return
        self.say2("Сводка сохранена: %s (строк: %d)" % (path, len(self.created_items)), "ok")
        messagebox.showinfo("Готово", "Файл сохранён:\n%s" % path)

    # ------------------------------------------------------------- отчёт 2

    def do_report_scan(self):
        folder = self.var_scan.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Папка не найдена", "Укажите существующую папку с файлами IES.")
            return

        files = [os.path.join(folder, fn) for fn in sorted(os.listdir(folder))
                 if fn.lower().endswith(".ies")]
        if not files:
            messagebox.showinfo("Пусто", "В папке нет файлов с расширением .ies")
            return

        items = []
        self.say2("")
        self.say2("— Анализ папки: %s —" % folder)

        for path in files:
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                ies = IESFile.read(path)
                zonal = ies.zonal_flux()
                declared = ies.declared_flux()
                flux = declared if declared > 0 else zonal
                iaxial = ies.axial_candela()
                imax, vang, _ = ies.max_candela()
                lum = ies.luminance(iaxial)

                items.append({
                    "name": name,
                    "flux": round(flux, 1),
                    "watts": ies.input_watts,
                    "length": abs(ies.length),
                    "width": abs(ies.width),
                    "height": abs(ies.height),
                    "imax": round(iaxial, 1),
                    "zonal": round(zonal, 1),
                })

                if imax > iaxial * 1.01:
                    self.say2("  %s: наибольшая сила света %.1f кд при %s° выше осевой "
                              "%.1f кд; в расчёт берётся осевая"
                              % (name, imax, vang, iaxial), "warn")

                if lum is None:
                    self.say2("  %s: габариты нулевые, яркость не считается" % name, "warn")
                elif declared > 0 and zonal > 0 and abs(declared - zonal) / zonal > 0.01:
                    self.say2("  %s: поток в поле %.1f лм, по кривой %.1f лм — расхождение"
                              % (name, declared, zonal), "warn")
                else:
                    self.say2("  ✓ %s — яркость %.0f кд/м²" % (name, lum))
            except Exception as exc:  # noqa: BLE001
                self.say2("  ✗ %s — %s" % (name, exc), "err")

        if not items:
            messagebox.showwarning("Нет данных", "Ни один файл не удалось прочитать.")
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить отчёт по папке", defaultextension=".xlsx",
            initialfile="Анализ_папки_IES.xlsx",
            filetypes=[("Книга Excel", "*.xlsx")])
        if not path:
            return
        try:
            ies_report.export_scan(path, items)
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения",
                                 "Не удалось записать файл.\n"
                                 "Возможно, он открыт в Excel.\n\n%s" % exc)
            return

        self.say2("Отчёт сохранён: %s (строк: %d)" % (path, len(items)), "ok")
        messagebox.showinfo("Готово", "Обработано файлов: %d\n\nФайл сохранён:\n%s"
                            % (len(items), path))

    # -------------------------------------------------- габаритная яркость

    def do_luminance(self):
        try:
            self._luminance()
        except ValueError as exc:
            messagebox.showerror("Проверьте ввод", str(exc))
            self.say3(str(exc), "err")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", "%s\n\n%s" % (exc, traceback.format_exc()))
            self.say3("Ошибка: %s" % exc, "err")

    def _luminance(self):
        if not self.lum_files:
            raise ValueError("Не выбраны файлы IES.")

        win_len = parse_number(self.var_win_len.get(), "Длина светового окна, м")
        win_wid = parse_number(self.var_win_wid.get(), "Ширина светового окна, м")

        if win_len > 10 or win_wid > 10:
            if not messagebox.askyesno(
                    "Проверьте размеры",
                    "Размер светового окна %s × %s м. Это похоже на миллиметры.\n"
                    "Размеры задаются в метрах. Продолжить?" % (win_len, win_wid)):
                return

        area = win_len * win_wid
        self.say3("")
        self.say3("— Расчёт габаритной яркости: окно %s × %s м, площадь %.4f м² —"
                  % (win_len, win_wid, area))

        items = []
        for path in self.lum_files:
            base = os.path.basename(path)
            try:
                ies = IESFile.read(path)
                zonal = ies.zonal_flux()
                declared = ies.declared_flux()
                flux = declared if declared > 0 else zonal

                iaxial = ies.axial_candela()
                imax, vang, _ = ies.max_candela()
                lum = iaxial / area

                items.append({
                    "name": device_name(ies, path),
                    "flux": round(flux, 1),
                    "watts": ies.input_watts,
                    "iaxial": round(iaxial, 1),
                })

                self.say3("  ✓ %s — осевая сила света %.1f кд — яркость %.0f кд/м²"
                          % (base, iaxial, lum), "ok")

                if imax > iaxial * 1.01:
                    self.say3("     наибольшая сила света в файле %.1f кд при %s°, "
                              "то есть больше осевой" % (imax, vang), "warn")

            except Exception as exc:  # noqa: BLE001
                self.say3("  ✗ %s — %s" % (base, exc), "err")

        if not items:
            messagebox.showwarning("Нет данных", "Ни один файл не удалось прочитать.")
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить расчёт габаритной яркости", defaultextension=".xlsx",
            initialfile="Габаритная_яркость.xlsx",
            filetypes=[("Книга Excel", "*.xlsx")])
        if not path:
            return
        try:
            ies_report.export_luminance(path, items, win_len, win_wid)
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения",
                                 "Не удалось записать файл.\n"
                                 "Возможно, он открыт в Excel.\n\n%s" % exc)
            return

        self.say3("Расчёт сохранён: %s (строк: %d)" % (path, len(items)), "ok")
        messagebox.showinfo("Готово", "Обработано файлов: %d\n\nФайл сохранён:\n%s"
                            % (len(items), path))

    # ------------------------------------------- пересчёт на другую цветность

    def do_color_shift(self):
        try:
            self._color_shift()
        except ValueError as exc:
            messagebox.showerror("Проверьте ввод", str(exc))
            self.say4(str(exc), "err")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", "%s\n\n%s" % (exc, traceback.format_exc()))
            self.say4("Ошибка: %s" % exc, "err")

    def _color_shift(self):
        src_dir = self.var_color_dir.get().strip()
        if not src_dir or not os.path.isdir(src_dir):
            raise ValueError("Укажите существующую папку с файлами IES.")

        factor = parse_number(self.var_factor.get(), "Коэффициент для светового потока")

        code = self.var_code.get().strip()
        if not re.fullmatch(r"\d{3}", code):
            raise ValueError("Код цветности должен состоять ровно из трёх цифр, "
                             "например 930 или 840.")

        sub = safe_filename(self.var_subdir.get().strip())
        if not sub or sub == "unnamed":
            raise ValueError("Укажите имя новой папки.")

        files = [os.path.join(src_dir, fn) for fn in sorted(os.listdir(src_dir))
                 if fn.lower().endswith(".ies")]
        if not files:
            raise ValueError("В папке нет файлов с расширением .ies")

        scale = self.var_scale_cd.get()

        # --- проверка на совпадение будущих имён файлов
        planned = {}
        for path in files:
            stem, ext = os.path.splitext(os.path.basename(path))
            new_stem, _ = replace_trailing_code(stem, code)
            planned.setdefault(safe_filename(new_stem) + ext, []).append(
                os.path.basename(path))

        clashes = {k: v for k, v in planned.items() if len(v) > 1}
        if clashes:
            lines = []
            for target, sources in sorted(clashes.items()):
                lines.append("%s  ←  %s" % (target, ", ".join(sources)))
            text = "\n".join(lines)
            self.say4("")
            self.say4("ОШИБКА: несколько файлов дают одно и то же имя:", "err")
            for line in lines:
                self.say4("  " + line, "err")
            messagebox.showerror(
                "Совпадение имён файлов",
                "После замены кода на %s несколько файлов получат одинаковое имя, "
                "и часть из них будет потеряна:\n\n%s\n\n"
                "Скорее всего в папке лежат файлы с разными кодами цветности. "
                "Разложите их по папкам и пересчитайте по отдельности."
                % (code, text))
            return

        out_dir = os.path.join(src_dir, sub)
        if os.path.isdir(out_dir):
            existing = [f for f in os.listdir(out_dir) if f.lower().endswith(".ies")]
            if existing:
                if not messagebox.askyesno(
                        "Папка уже существует",
                        "Папка «%s» уже есть и содержит %d файлов IES.\n"
                        "Одноимённые файлы будут перезаписаны. Продолжить?"
                        % (sub, len(existing))):
                    return
        else:
            os.makedirs(out_dir)

        self.say4("")
        self.say4("— Пересчёт на цветность %s: коэффициент %s, файлов %d —"
                  % (code, factor, len(files)))
        self.say4("  Папка назначения: %s" % out_dir)
        if scale:
            self.say4("  Силы света пересчитываются вместе с потоком.")
        else:
            self.say4("  Силы света НЕ пересчитываются — меняется только "
                      "поле «люмены на лампу».", "warn")

        done = 0
        errors = 0

        for path in files:
            base = os.path.basename(path)
            stem, ext = os.path.splitext(base)
            try:
                ies = IESFile.read(path)

                if ies.encoding_in != "koi8-r":
                    self.say4("  %s: кодировка %s → будет сохранена в koi8-r"
                              % (base, ies.encoding_in))

                old_flux, new_flux = ies.apply_color_factor(factor, scale_candela=scale)

                # --- название прибора
                old_name = ies.get_keyword("LUMINAIRE")
                if old_name is None or not old_name.strip():
                    donor = (ies.get_keyword("LUMCAT") or "").strip()
                    if donor:
                        ies.set_keyword("LUMINAIRE", donor,
                                        after=["LUMCAT", "MANUFAC", "OTHER"])
                        ies.set_keyword("LUMCAT", "", create=False)
                        old_name = donor
                        self.say4("     [LUMINAIRE] было пустым — название «%s» "
                                  "перенесено из [LUMCAT]" % donor)
                    else:
                        old_name = ""

                if not old_name:
                    self.say4("  %s: поля [LUMINAIRE] и [LUMCAT] пустые — "
                              "название не изменено" % base, "warn")
                else:
                    new_name, found = replace_trailing_code(old_name, code)
                    if found:
                        ies.set_keyword("LUMINAIRE", new_name)
                        self.say4("     [LUMINAIRE] «%s» → «%s»" % (old_name, new_name))
                    else:
                        self.say4("  %s: в конце [LUMINAIRE] «%s» нет трёхзначного "
                                  "кода — название не изменено" % (base, old_name), "warn")

                # --- поле [LUMCAT] по желанию
                if self.var_fix_lumcat.get():
                    old_cat = ies.get_keyword("LUMCAT")
                    if old_cat and old_cat.strip():
                        new_cat, found = replace_trailing_code(old_cat, code)
                        if found:
                            ies.set_keyword("LUMCAT", new_cat)
                            self.say4("     [LUMCAT] «%s» → «%s»" % (old_cat, new_cat))

                # --- имя файла
                new_stem, found = replace_trailing_code(stem, code)
                if not found:
                    self.say4("  %s: в конце имени файла нет трёхзначного кода — "
                              "имя оставлено прежним" % base, "warn")
                new_name_file = safe_filename(new_stem) + ext

                out_path = os.path.join(out_dir, new_name_file)
                bad = ies.save(out_path)
                if bad:
                    self.say4("     ВНИМАНИЕ: символы %s не кодируются в koi8-r "
                              "и заменены на «?»" % " ".join(bad), "warn")

                done += 1
                self.say4("  ✓ %s → %s   поток %.1f → %.1f лм"
                          % (base, new_name_file, old_flux, new_flux), "ok")

            except Exception as exc:  # noqa: BLE001
                errors += 1
                self.say4("  ✗ %s — ошибка: %s" % (base, exc), "err")

        self.say4("Готово: пересчитано файлов — %d, ошибок — %d." % (done, errors),
                  "ok" if not errors else "warn")
        self.status.set("Пересчитано на цветность %s: %d файлов" % (code, done))

        if done:
            messagebox.showinfo(
                "Готово",
                "Пересчитано файлов: %d\nОшибок: %d\n\nПапка:\n%s"
                % (done, errors, out_dir))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

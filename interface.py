"""Выбор пункта, его параметры и показ результата."""

from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PIL import Image

import processing as edit
import statistics_image as stats


STEPS = [
    ("1", "1. Исходное изображение"), ("2", "2. Каналы и гистограммы"),
    ("3", "3. Окно 11 × 11"), ("4", "4. Однородность областей"),
    ("5a", "5а. Яркость"), ("5b", "5б. Контраст"), ("5c", "5в. Негатив"),
    ("5d", "5г. Обмен каналов"), ("5e", "5д. Отражение"),
    ("5f", "5е. Размытие"), ("5g", "5ж. Гамма-коррекция"),
    ("6", "6. Профиль яркости"), ("7", "7. Карта контрастности"),
    ("8", "8. Сохранение"),
]

# Подпись, минимум, максимум и начальное значение ползунка.
SLIDERS = {
    "5a": [("Общая", -100, 100, 0), ("R", -100, 100, 0),
           ("G", -100, 100, 0), ("B", -100, 100, 0)],
    "5b": [("Контраст", -100, 100, 0)],
    "5g": [("Гамма", 0.2, 3, 1)],
}
CHOICES = {
    "2": ["Оттенки серого", "Красный канал", "Зелёный канал", "Синий канал"],
    "5d": ["Красный ↔ Зелёный", "Красный ↔ Синий", "Зелёный ↔ Синий"],
    "5e": ["Слева направо", "Сверху вниз"],
    "7": ["Четыре соседа", "Восемь соседей", "Квадратное окно"],
}


ANALYSIS = """Анализ однородных и неоднородных областей

Примеры относятся к фотографии «фото-улицы.png».
Для анализа выбраны четыре окна размером 11 × 11 пикселей.
Дисперсия равна квадрату стандартного отклонения.

1. Светлый участок неба — относительно однородная область.
   Центр: (300, 72). Средняя яркость: 249.50. Стандартное отклонение: 20.60.

2. Ровный участок дороги — однородная область.
   Центр: (509, 248). Средняя яркость: 177.15. Стандартное отклонение: 3.03.

3. Граница листвы и светлого неба — неоднородная область.
   Центр: (340, 70). Средняя яркость: 131.58. Стандартное отклонение: 78.58.

4. Участок с контрастными деталями улицы — неоднородная область.
   Центр: (290, 192). Средняя яркость: 146.90. Стандартное отклонение: 71.25.

В однородных областях яркости пикселей близки друг к другу. Поэтому их
гистограмма должна быть сравнительно узкой, а дисперсия и стандартное
отклонение — небольшими. Например, для дороги отклонение равно 3.03:
яркости пикселей в этом окне почти не различаются.

В неоднородных областях яркости заметно различаются. Их гистограмма
должна быть более широкой или иметь несколько максимумов. Дисперсия
и стандартное отклонение больше. На границе листвы и неба отклонение
равно 78.58: в окне есть и тёмные пиксели листвы, и светлые пиксели неба.

Средняя яркость показывает общий уровень светлоты, но сама по себе
не определяет однородность. Для вывода нужно учитывать гистограмму,
дисперсию и стандартное отклонение.
"""


class LabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KZ lab 2")
        self.geometry("1100x760")
        self.image = self.flipped = self.window_frame = None
        self.table, self.values = [], []
        self.saved = {}

        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Открыть изображение", command=self.open_image).pack(side="left")
        self.step = ttk.Combobox(toolbar, values=[title for _, title in STEPS],
                                 state="readonly", width=35)
        self.step.current(0)
        self.step.pack(side="left", padx=15)
        self.step.bind("<<ComboboxSelected>>", self.select_step)
        self.controls = ttk.Frame(self, padding=10)
        self.controls.pack(fill="x")
        self.info = ttk.Label(self, wraplength=1050, justify="left")
        self.info.pack(anchor="w", padx=10)
        self.figure = Figure(figsize=(9, 5), layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("motion_notify_event", self.show_pixel)
        self.analysis = tk.Text(self, wrap="word", padx=18, pady=14,
                                font=("TkDefaultFont", 12), relief="flat")
        self.analysis.insert("1.0", ANALYSIS)
        self.analysis.configure(state="disabled")
        sample = Path(__file__).with_name("фото-улицы.png")
        if sample.is_file():
            self.load_image(sample)

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("PNG, BMP, TIFF", "*.png *.bmp *.tif *.tiff")]
        )
        if path:
            self.load_image(path)

    def load_image(self, path):
        try:
            with Image.open(path) as source:
                if source.mode != "RGB" or source.format not in ("PNG", "BMP", "TIFF"):
                    raise ValueError("Нужно RGB-изображение PNG, BMP или TIFF.")
                self.image = source.copy()
        except (OSError, ValueError) as error:
            messagebox.showerror("Ошибка загрузки", str(error))
            return
        self.table = stats.brightness_table(self.image)
        self.saved = {"Оригинал": self.image.copy()}
        self.step.current(0)
        self.select_step()

    def select_step(self, _event=None):
        for child in self.controls.winfo_children():
            child.destroy()
        self.values, self.window_frame = [], None
        self.info.configure(text="")
        self.analysis.pack_forget()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        if self.image is None:
            return
        self.flipped = self.image.copy()
        code = STEPS[self.step.current()][0]
        choices = list(self.saved) if code == "8" else CHOICES.get(code)
        if choices:
            box = ttk.Combobox(self.controls, values=choices, state="readonly", width=35)
            box.current(0)
            box.pack(side="left", padx=5)
            self.values.append(box)
        sliders = SLIDERS.get(code, [])
        if code == "6":
            sliders = [("Строка y", 0, self.image.height - 1, self.image.height // 2)]
        if code == "7":
            sliders = [("Размер окна", 3, 15, 5)]
        for title, low, high, value in sliders:
            slider = tk.Scale(self.controls, label=title, from_=low, to=high,
                              resolution=0.1 if code == "5g" else 2 if code == "7" else 1,
                              orient="horizontal", length=170)
            slider.set(value)
            slider.pack(side="left", padx=5)
            self.values.append(slider)
        if code == "5c":
            for color in ("R", "G", "B"):
                value = tk.BooleanVar(value=True)
                ttk.Checkbutton(self.controls, text=color, variable=value).pack(side="left", padx=10)
                self.values.append(value)
        if code == "7":
            self.values[0].bind("<<ComboboxSelected>>", self.update_window_size)
            self.update_window_size()
        text = "Применить"
        if code == "8":
            text = "Сохранить выбранное"
        if code not in ("1", "3", "4"):
            ttk.Button(self.controls, text=text, command=self.run).pack(side="left", padx=10)
        if code == "8":
            self.values[0].bind("<<ComboboxSelected>>", self.preview_saved)
        if code == "4":
            self.canvas.get_tk_widget().pack_forget()
            self.analysis.pack(fill="both", expand=True, padx=10, pady=10)
            return
        self.show_images([self.image], ["Исходное изображение"])
        if code == "3":
            self.window_frame = Rectangle((0, 0), 13, 13, fill=False, color="gold", visible=False)
            self.figure.axes[0].add_patch(self.window_frame)
            self.info.configure(text="Двигайте курсор по изображению. Окно 11 × 11; рамка 13 × 13.")


    def show_images(self, pictures, titles):
        self.figure.clear()
        for index, picture in enumerate(pictures):
            axis = self.figure.add_subplot(1, len(pictures), index + 1)
            axis.imshow(picture, cmap="gray", vmin=0, vmax=255)
            axis.set_title(titles[index])
            axis.axis("off")
        self.canvas.draw_idle()

    def update_window_size(self, _event=None):
        self.values[1].configure(state="normal" if self.values[0].current() == 2 else "disabled")

    def run(self):
        code = STEPS[self.step.current()][0]
        values = [widget.get() for widget in self.values]
        name = self.step.get()
        result = None

        if code == "2":
            pictures, histograms = stats.channels_and_histograms(self.image)
            index = self.values[0].current()
            for title, picture in zip(CHOICES["2"], pictures):
                self.saved[title] = picture.copy()
            self.figure.clear()
            axis = self.figure.add_subplot(1, 2, 1)
            axis.imshow(pictures[index], cmap="gray", vmin=0, vmax=255)
            axis.set_title(values[0])
            axis.axis("off")
            axis = self.figure.add_subplot(1, 2, 2)
            color = ["gray", "red", "green", "blue"][index]
            axis.bar(range(256), histograms[index], color=color)
            axis.set(xlabel="Значение 0–255", ylabel="Количество пикселей", title="Гистограмма")
        elif code == "5a":
            result = edit.change_brightness(self.image, values[0], values[1], values[2], values[3])
        elif code == "5b":
            result = edit.change_contrast(self.image, values[0])
        elif code == "5c":
            result = edit.make_negative(self.image, values[0], values[1], values[2])
        elif code == "5d":
            mode = ["red_green", "red_blue", "green_blue"][self.values[0].current()]
            result = edit.swap_channels(self.image, mode)
        elif code == "5e":
            mode = "horizontal" if self.values[0].current() == 0 else "vertical"
            self.flipped = edit.flip_image(self.flipped, mode)
            result = self.flipped
        elif code == "5f":
            four = edit.blur_image(self.image, "four")
            eight = edit.blur_image(self.image, "eight")
            self.saved["Размытие: 4 соседа"], self.saved["Размытие: 8 соседей"] = four, eight
            self.show_images(
                [self.image, four, eight], ["Оригинал", "4-связность", "8-связность"]
            )
        elif code == "5g":
            result = edit.gamma_correction(self.image, values[0])
        elif code == "6":
            row = int(values[0])
            self.figure.clear()
            axis = self.figure.add_subplot(2, 1, 1)
            axis.imshow(self.image)
            axis.axhline(row, color="gold")
            axis.set_title(f"Строка y = {row}")
            axis.axis("off")
            axis = self.figure.add_subplot(2, 1, 2)
            axis.plot(stats.brightness_profile(self.table, row), color="black")
            axis.set(xlabel="Координата x", ylabel="Яркость", ylim=(0, 255))
            buffer = BytesIO()
            self.figure.savefig(buffer, format="png")
            buffer.seek(0)
            with Image.open(buffer) as picture:
                self.saved[f"Профиль, строка {row}"] = picture.copy()
        elif code == "7":
            mode = ["four", "eight", "window"][self.values[0].current()]
            result = stats.contrast_map(self.table, mode, int(values[1]))
            name = "Карта: " + values[0]
            if mode == "window":
                name += f" {int(values[1])}x{int(values[1])}"
        elif code == "8":
            path = filedialog.asksaveasfilename(
                initialfile=values[0] + ".png", defaultextension=".png"
            )
            if path:
                try:
                    self.saved[values[0]].save(path, format="PNG")
                except OSError as error:
                    messagebox.showerror("Ошибка сохранения", str(error))
        if result is not None:
            self.saved[name] = result.copy()
            self.show_images([self.image, result], ["Оригинал", name])
        self.canvas.draw_idle()

    def preview_saved(self, _event=None):
        name = self.values[0].get()
        self.show_images([self.saved[name]], [name])

    def show_pixel(self, event):
        if STEPS[self.step.current()][0] != "3" or self.window_frame is None:
            return
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            self.window_frame.set_visible(False)
            self.canvas.draw_idle()
            return
        x, y = int(event.xdata + 0.5), int(event.ydata + 0.5)
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            return
        self.window_frame.set_xy((x - 6.5, y - 6.5))
        self.window_frame.set_visible(True)
        r, g, b = self.image.getpixel((x, y))
        intensity = float(r + g + b) / 3
        text = (
            f"x={x}, y={y} | RGB=({r}, {g}, {b}) | "
            f"Интенсивность={intensity:.2f}\n"
        )
        result = stats.window_statistics(self.table, x, y)
        if result is None:
            text += "Окно выходит за край изображения."
        else:
            mean, variance, deviation = result
            text += (
                f"Среднее={mean:.2f} | Дисперсия={variance:.2f} | "
                f"Стандартное отклонение={deviation:.2f}"
            )
        self.info.configure(text=text)
        self.canvas.draw_idle()


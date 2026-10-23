"""Каналы, гистограммы, статистика окна и карта контрастности."""

from PIL import Image

from processing import neighbor_offsets


def channels_and_histograms(source):
    gray_image = Image.new("L", source.size)
    red_image = Image.new("RGB", source.size)
    green_image = Image.new("RGB", source.size)
    blue_image = Image.new("RGB", source.size)
    gray_hist = [0] * 256
    red_hist = [0] * 256
    green_hist = [0] * 256
    blue_hist = [0] * 256
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            gray = (r + g + b) // 3
            gray_image.putpixel((x, y), gray)
            red_image.putpixel((x, y), (r, 0, 0))
            green_image.putpixel((x, y), (0, g, 0))
            blue_image.putpixel((x, y), (0, 0, b))
            # Считаем частоты каждого канала отдельно.
            gray_hist[gray] += 1
            red_hist[r] += 1
            green_hist[g] += 1
            blue_hist[b] += 1
    pictures = [gray_image, red_image, green_image, blue_image]
    histograms = [gray_hist, red_hist, green_hist, blue_hist]
    return pictures, histograms


def brightness_table(source):
    table = []
    for y in range(source.height):
        row = []
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            row.append((r + g + b) / 3)
        table.append(row)
    return table


def window_statistics(table, x, y):
    """Статистика полного окна 11 × 11; у края возвращаем None."""
    height, width = len(table), len(table[0])
    if x < 5 or y < 5 or x >= width - 5 or y >= height - 5:
        return None
    total = 0
    total_squares = 0
    for row_y in range(y - 5, y + 6):
        for column_x in range(x - 5, x + 6):
            value = table[row_y][column_x]
            total += value
            total_squares += value * value
    mean = total / 121
    variance = total_squares / 121 - mean * mean
    if variance < 0:
        variance = 0
    return mean, variance, variance ** 0.5


def brightness_profile(table, row_y):
    # Строка таблицы уже содержит яркости слева направо.
    return table[row_y].copy()


def contrast_map(table, mode, window_size=5):
    height, width = len(table), len(table[0])
    result = Image.new("L", (width, height))
    offsets = neighbor_offsets(mode, window_size)
    for y in range(height):
        for x in range(width):
            minimum = table[y][x]
            maximum = table[y][x]
            for offset_x, offset_y in offsets:
                neighbor_x, neighbor_y = x + offset_x, y + offset_y
                if 0 <= neighbor_x < width and 0 <= neighbor_y < height:
                    value = table[neighbor_y][neighbor_x]
                    if value < minimum:
                        minimum = value
                    if value > maximum:
                        maximum = value
            result.putpixel((x, y), int(maximum - minimum))
    return result

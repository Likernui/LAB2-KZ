"""Ручная обработка пикселей. Pillow используется для хранения изображений."""

from PIL import Image


def limit_value(value):
    """Ограничиваем значение канала."""
    if value < 0:
        return 0
    if value > 255:
        return 255
    return int(value)


def change_brightness(source, common, red, green, blue):
    result = Image.new("RGB", source.size)
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            result.putpixel((x, y), (
                limit_value(r + common + red),
                limit_value(g + common + green),
                limit_value(b + common + blue),
            ))
    return result


def change_contrast(source, value):
    result = Image.new("RGB", source.size)
    factor = (100 + value) / 100
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            result.putpixel((x, y), (
                limit_value(128 + (r - 128) * factor),
                limit_value(128 + (g - 128) * factor),
                limit_value(128 + (b - 128) * factor),
            ))
    return result


def make_negative(source, invert_red, invert_green, invert_blue):
    result = Image.new("RGB", source.size)
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            # Каналы выбираются независимо друг от друга.
            if invert_red:
                r = 255 - r
            if invert_green:
                g = 255 - g
            if invert_blue:
                b = 255 - b
            result.putpixel((x, y), (r, g, b))
    return result


def swap_channels(source, mode):
    result = Image.new("RGB", source.size)
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            if mode == "red_green":
                pixel = (g, r, b)
            elif mode == "red_blue":
                pixel = (b, g, r)
            else:
                pixel = (r, b, g)
            result.putpixel((x, y), pixel)
    return result


def flip_image(source, mode):
    result = Image.new("RGB", source.size)
    for y in range(source.height):
        for x in range(source.width):
            if mode == "horizontal":
                source_x = source.width - 1 - x
                source_y = y
            else:
                source_x = x
                source_y = source.height - 1 - y
            pixel = source.getpixel((source_x, source_y))
            result.putpixel((x, y), pixel)
    return result


def neighbor_offsets(mode, window_size=3):
    """Смещения включают центральный пиксель."""
    if mode == "four":
        return [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
    radius = 1 if mode == "eight" else window_size // 2
    offsets = []
    for offset_y in range(-radius, radius + 1):
        for offset_x in range(-radius, radius + 1):
            offsets.append((offset_x, offset_y))
    return offsets


def blur_image(source, mode):
    result = Image.new("RGB", source.size)
    offsets = neighbor_offsets(mode)
    for y in range(source.height):
        for x in range(source.width):
            red_sum = 0
            green_sum = 0
            blue_sum = 0
            count = 0
            for offset_x, offset_y in offsets:
                neighbor_x = x + offset_x
                neighbor_y = y + offset_y
                # За краем изображения соседей нет.
                if 0 <= neighbor_x < source.width and 0 <= neighbor_y < source.height:
                    r, g, b = source.getpixel((neighbor_x, neighbor_y))
                    red_sum += r
                    green_sum += g
                    blue_sum += b
                    count += 1
            result.putpixel((x, y), (
                red_sum // count, green_sum // count, blue_sum // count,
            ))
    return result


def gamma_correction(source, gamma):
    result = Image.new("RGB", source.size)
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source.getpixel((x, y))
            result.putpixel((x, y), (
                limit_value(255 * (r / 255) ** gamma),
                limit_value(255 * (g / 255) ** gamma),
                limit_value(255 * (b / 255) ** gamma),
            ))
    return result

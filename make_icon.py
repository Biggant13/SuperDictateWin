from PIL import Image, ImageDraw

def create_icon():
    size = 256  # Высокое разрешение для иконки
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    # Масштабируем координаты (в трее рисуется 64x64, умножаем на 4)
    scale = 4
    d.ellipse((4*scale, 4*scale, 60*scale, 60*scale), fill=(220, 50, 50, 255))
    d.ellipse((22*scale, 18*scale, 42*scale, 38*scale), fill=(255, 255, 255, 255))
    d.rectangle((28*scale, 34*scale, 36*scale, 46*scale), fill=(255, 255, 255, 255))
    
    # Сохраняем во все нужные размеры для Windows
    img.save("app.ico", format="ICO", sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    print("✅ Файл app.ico создан в корне проекта!")

if __name__ == "__main__":
    create_icon()
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGBA", (256, 256), (10, 10, 10, 255))
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("arial.ttf", 100)
except:
    font = ImageFont.load_default()

draw.text((40, 60), "/", fill=(255, 0, 0, 255), font=font)
draw.text((90, 60), "/", fill=(255, 255, 0, 255), font=font)
draw.text((140, 60), "/", fill=(0, 255, 0, 255), font=font)
draw.text((190, 60), "/", fill=(0, 0, 255, 255), font=font)

img.save("logo.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
print("Icono logo.ico creado exitosamente.")

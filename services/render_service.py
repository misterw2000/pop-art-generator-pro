import logging
import numpy as np
import cv2
from typing import Optional
from core.models.project import Project
from core.enums import BlendMode
from infrastructure.gpu.context import GPUContext
from PIL import Image as PILImage, ImageDraw, ImageFont

class RenderService:
    def __init__(self, gpu_context: GPUContext):
        self.logger = logging.getLogger("PopArtGeneratorPro.RenderService")
        self.gpu = gpu_context

    def render_project_to_canvas(self, project: Project) -> np.ndarray:
        if not project.layers:
            return np.zeros((project.height, project.width, 4), dtype=np.uint8)

        canvas = np.zeros((project.height, project.width, 4), dtype=np.float32)

        for layer in project.layers:
            if not layer.visible:
                continue
            
            if layer.filter_type:
                canvas = self._apply_adjustment_layer(canvas, layer.filter_type)
                continue

            if layer.pixels is None:
                continue
                
            layer_pixels = layer.pixels.astype(np.float32)
            
            if layer.mask and layer.mask.data is not None:
                mask_data = layer.mask.data.astype(np.float32) / 255.0
                if mask_data.shape != (project.height, project.width):
                    mask_data = cv2.resize(mask_data, (project.width, project.height))
                layer_pixels[:, :, 3] = layer_pixels[:, :, 3] * mask_data
            
            base_rgb = canvas[:, :, :3] / 255.0
            blend_rgb = layer_pixels[:, :, :3] / 255.0
            
            if layer.blend_mode == BlendMode.SCREEN:
                blended_rgb = 1.0 - (1.0 - base_rgb) * (1.0 - blend_rgb)
            else:
                blended_rgb = blend_rgb
                
            layer_alpha = (layer_pixels[:, :, 3] / 255.0) * layer.opacity
            base_alpha = canvas[:, :, 3] / 255.0
            
            out_alpha = layer_alpha + base_alpha * (1.0 - layer_alpha)
            out_alpha_safe = np.where(out_alpha > 0, out_alpha, 1.0)
            
            out_rgb = (blended_rgb * layer_alpha[..., None] + base_rgb * base_alpha[..., None] * (1.0 - layer_alpha[..., None])) / out_alpha_safe[..., None]
            
            canvas[:, :, :3] = out_rgb * 255.0
            canvas[:, :, 3] = out_alpha * 255.0
            
        return canvas.astype(np.uint8)

    def _apply_adjustment_layer(self, canvas: np.ndarray, filter_type: str) -> np.ndarray:
        img = canvas.astype(np.uint8)
        h, w = img.shape[:2]
        
        if filter_type == "blur":
            img = cv2.GaussianBlur(img, (25, 25), 0)
        elif filter_type == "sharpen":
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            img = cv2.filter2D(img, -1, kernel)
        elif filter_type == "invert":
            img[:, :, :3] = cv2.bitwise_not(img[:, :, :3])
        elif filter_type == "bright_up":
            hsv = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2HSV)
            h_ch, s, v = cv2.split(hsv)
            v = cv2.add(v, 50)
            v[v > 255] = 255
            img[:,:,:3] = cv2.cvtColor(cv2.merge((h_ch, s, v)), cv2.COLOR_HSV2RGB)
        elif filter_type == "bright_down":
            hsv = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2HSV)
            h_ch, s, v = cv2.split(hsv)
            v = cv2.subtract(v, 50)
            v[v < 0] = 0
            img[:,:,:3] = cv2.cvtColor(cv2.merge((h_ch, s, v)), cv2.COLOR_HSV2RGB)
            
        elif filter_type == "paper_grain":
            noise = np.random.randint(0, 100, (h, w, 1), dtype=np.uint8)
            img[:,:,:3] = np.clip(img[:,:,:3].astype(np.int32) - noise, 0, 255).astype(np.uint8)
        elif filter_type == "canvas_texture":
            noise = np.random.randint(0, 255, (h, w, 1), dtype=np.uint8)
            noise = cv2.GaussianBlur(noise, (5,5), 0)
            mask = (noise.astype(np.float32) / 255.0 * 0.3 + 0.7)
            img[:,:,:3] = np.clip(img[:,:,:3].astype(np.float32) * mask, 0, 255).astype(np.uint8)
        elif filter_type == "film_grain":
            noise = np.random.randint(-50, 50, (h, w, 3), dtype=np.int16)
            img[:,:,:3] = np.clip(img[:,:,:3].astype(np.int16) + noise, 0, 255).astype(np.uint8)
        elif filter_type == "ink_bleed":
            b, g, r, a = cv2.split(img)
            kernel = np.ones((5,5), np.uint8)
            b = cv2.dilate(b, kernel, iterations=1)
            g = cv2.dilate(g, kernel, iterations=1)
            r = cv2.dilate(r, kernel, iterations=1)
            a = cv2.GaussianBlur(a, (7,7), 0)
            img = cv2.merge([b, g, r, a])
        elif filter_type == "spray_paint":
            alpha = img[:,:,3]
            noise = np.random.randint(0, 255, alpha.shape, dtype=np.uint8)
            noise = cv2.GaussianBlur(noise, (5,5), 0)
            mask = cv2.bitwise_and(alpha, noise)
            img[:,:,3] = cv2.addWeighted(alpha, 0.4, mask, 0.6, 0)
        elif filter_type == "paint_drips":
            alpha = img[:,:,3]
            drips = alpha.copy()
            for _ in range(100):
                x = np.random.randint(0, w)
                y_start = np.random.randint(0, h//2)
                length = np.random.randint(50, 150)
                thickness = np.random.randint(2, 6)
                cv2.line(drips, (x, y_start), (x, y_start+length), 255, thickness)
            img[:,:,3] = cv2.addWeighted(alpha, 0.7, drips, 0.3, 0)
        elif filter_type == "benday_dots":
            dot_size = 8
            filtered_img = np.zeros_like(img)
            alpha = img[:, :, 3]
            small_w = max(1, w // dot_size)
            small_h = max(1, h // dot_size)
            small_alpha = cv2.resize(alpha, (small_w, small_h), interpolation=cv2.INTER_AREA)
            small_img = cv2.resize(img, (small_w, small_h), interpolation=cv2.INTER_AREA)
            for y in range(small_h):
                for x in range(small_w):
                    intensity = small_alpha[y, x] / 255.0
                    radius = int(intensity * (dot_size / 2.0))
                    if radius > 0:
                        center = (x * dot_size + dot_size // 2, y * dot_size + dot_size // 2)
                        b, g, r = int(small_img[y, x, 0]), int(small_img[y, x, 1]), int(small_img[y, x, 2])
                        cv2.circle(filtered_img, center, radius, (b, g, r, 255), -1)
            img = filtered_img
        elif filter_type == "line_screen":
            line_w = 6
            filtered_img = np.zeros_like(img)
            alpha = img[:, :, 3]
            small_w = max(1, w // line_w)
            small_h = max(1, h // line_w)
            small_alpha = cv2.resize(alpha, (small_w, small_h), interpolation=cv2.INTER_AREA)
            small_img = cv2.resize(img, (small_w, small_h), interpolation=cv2.INTER_AREA)
            for y in range(small_h):
                for x in range(small_w):
                    intensity = small_alpha[y, x] / 255.0
                    thickness = int(intensity * (line_w / 2.0))
                    if thickness > 0:
                        pt1 = (x * line_w + line_w // 2, y * line_w)
                        pt2 = (x * line_w + line_w // 2, y * line_w + line_w)
                        b, g, r = int(small_img[y, x, 0]), int(small_img[y, x, 1]), int(small_img[y, x, 2])
                        cv2.line(filtered_img, pt1, pt2, (b, g, r, 255), thickness)
            img = filtered_img
        elif filter_type == "graffiti_scribble":
            overlay = img.copy()
            for _ in range(40):
                pt1 = (np.random.randint(0, w), np.random.randint(0, h))
                pt2 = (pt1[0] + np.random.randint(-120, 120), pt1[1] + np.random.randint(-120, 120))
                color = (0, 0, 0, 255) if np.random.rand() > 0.3 else (255, 255, 255, 255)
                cv2.line(overlay, pt1, pt2, color, np.random.randint(1, 3))
            img = cv2.addWeighted(img, 0.75, overlay, 0.25, 0)
        elif filter_type == "screen_ink":
            img = cv2.GaussianBlur(img, (3,3), 0)
            b, g, r, a = cv2.split(img)
            kernel = np.ones((3,3), np.uint8)
            a = cv2.dilate(a, kernel, iterations=1)
            img = cv2.merge([b, g, r, a])
            
        elif filter_type == "fat_pixel":
            small = cv2.resize(img, (max(1, w//16), max(1, h//16)), interpolation=cv2.INTER_AREA)
            img = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        elif filter_type == "16_bit":
            img[:,:,:3] = (img[:,:,:3] // 64) * 64
        elif filter_type == "terminal":
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
            dot_size = 8
            filtered_img = np.zeros_like(img)
            small_w = max(1, w // dot_size)
            small_h = max(1, h // dot_size)
            small_gray = cv2.resize(gray, (small_w, small_h), interpolation=cv2.INTER_AREA)
            for y in range(small_h):
                for x in range(small_w):
                    intensity = small_gray[y, x] / 255.0
                    radius = int(intensity * (dot_size / 2.0))
                    if radius > 0:
                        center = (x * dot_size + dot_size // 2, y * dot_size + dot_size // 2)
                        cv2.circle(filtered_img, center, radius, (0, 255, 0, 255), -1)
            img = filtered_img
        elif filter_type == "risograph":
            gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2GRAY)
            _, mask_dark = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            _, mask_light = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            riso = np.zeros_like(img)
            riso[mask_dark == 255] = [255, 0, 128, 255]
            riso[mask_light == 255] = [0, 128, 255, 255]
            riso[:, :, 0] = np.roll(riso[:, :, 0], 8, axis=1)
            riso[:, :, 2] = np.roll(riso[:, :, 2], -8, axis=1)
            noise = np.random.randint(0, 60, (h, w, 1), dtype=np.uint8)
            riso[:,:,:3] = np.clip(riso[:,:,:3].astype(np.int32) - noise, 0, 255).astype(np.uint8)
            img = riso
        elif filter_type == "emoji_pop":
            gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2GRAY)
            scale = 24
            small_h, small_w = max(1, h//scale), max(1, w//scale)
            small_gray = cv2.resize(gray, (small_w, small_h), interpolation=cv2.INTER_AREA)
            
            temp_w = small_w * scale
            temp_h = small_h * scale
            pil_img = PILImage.new("RGBA", (temp_w, temp_h), (0, 0, 0, 255))
            draw = ImageDraw.Draw(pil_img)
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\seguiemj.ttf", scale)
            except:
                font = ImageFont.load_default()
                
            emojis = "😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍😘😗😙😚😋😛😝😜🤓😎😏😒😞😔😟😕🙁☹️😣😖😫😩😢😭😤😠😡😱😨😰😥😓🤗🤔🤥😶😐😑😬🙄😯😦😧😮😲😴🤤😪😵🤐👋🤚🖐️✋🖖👌✌️🤞🤘🤙👈👉👆👇☝️👍👎✊👊🤛🤜👏🙌👐🙏✍️💅🤳💪🏃🚶🏄🏊🚴🏋️🤸⛹️🤾🤽🏌️🏇⛷️🏂👶👦👧👱👨👩👴👵👲👳👮👷💂🕵️👩‍⚕️👨‍⚕️👩‍🏫👨‍🏫👩‍🚀👨‍🚀👩‍🎤👨‍🎤👩‍💻👨‍💻👩‍🔧👨‍🔧👩‍🚒👨‍🚒👩‍✈️👨‍✈️👩‍⚖️👨‍⚖️🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐽🐸🐵🦍🐔🐧🐦🐤🐣🐥🦆🦅🦉🦇🕊️🐺🐗🐴🦄🐝🐞🦋🐌🐛🕷️🦂🐢🐍🦎🐙🦑🦐🦀🐠🐟🐡🦈🐬🐳🐋🐊🦏🐘🦌🌸🌹🌺🌻🌼🌷🌱🌲🌳🌴🌵🍀🍁🍂🍃🌿☘️🍎🍏🍐🍊🍋🍌🍉🍇🍓🍒🍑🍍🥝🍅🥑🍆🥔🥕🌽🌶️🥒🍞🥐🥖🧀🍔🍟🍕🌭🌮🌯🥗🍝🍜🍣🍱🍩🍪🎂🍰🍫🍿🍯🍭🍬🍮⚽🏀🏈⚾🎾🏐🏆🥇🥈🥉🎮🎲🎯🎨🎸🎹🎧🎤🎬🚗🚕🚙🚌🚎🚓🚑🚒🚚🚜✈️🚀🚁🚢⛵🚲🛴🛵🚦🚥⌚📱💻🖥️🖨️📷📹🎥📺📻🔋💡🔦💰💵💴💶💷💳💎⚙️🔧🔨🛠️🔑🔒🔓❤️❣️💕💞💓💗💖💘💝💟⭐🌟✨💫🔥💥💦💨🌈☀️🌙☁️☔⚡❄️🌪️🌊🌍🌎🌏🌑🌕🌞⚠️🚫❌⭕✔️❗❓⁉️‼️🔴🔵⚫⚪◼️◻️◾◽🔺🔻🔸🔹🌌🌠🌚🌛🌜🌝☄️🛰️☠️👽👾🤖🎭🗿👁️🕯️🎩👑💍💄👓🕶️🍽️🍴🥄🔪🏠🏡🏢🏥🏦🏰🏯🗼🗽⛪🕌🕍⛩️🏛️🌋🏔️⛰️🏕️🏖️🏜️🌅🌄🌁🌉🌃🌆🌇🛏️🛋️🚪🚽🚿🛁📚📖📝✏️🖊️🖋️🖌️📌📍📎🖇️📏📐✂️📦📫📬📭📮🗑️🔒🔑🗝️⚗️🖱️⌨️💾💿📀📡🔌🔋🖲️🎁🎈🎉🎊🎀🏮♠️♥️♦️♣️🃏🎴🀄⚔️🛡️🗡️☯️⚛️☢️☣️⚠️☑️✖️➕➖➗♻️⚜️⚙️⚖️⚒️⚚⚕️⚗️🔰🌀💠🛑⛔🚧🚨🚦🚥🛒🛍️⛸️♟️🛎️🏎️🏍️🛩️🛫🛬🛥️🛳️🚤⛴️🚂🚆🚇🚊🚉🛡️⚜️🏵️🥀🤠🤡🤑🤓😈👿💩🤶🎅"
            num_emojis = len(emojis)
            
            for y in range(small_h):
                for x in range(small_w):
                    inv_val = int(255 - small_gray[y, x])
                    idx = int(inv_val * num_emojis / 256)
                    if idx >= num_emojis: idx = num_emojis - 1
                    try:
                        draw.text((x * scale, y * scale), emojis[idx], embedded_color=True, font=font)
                    except:
                        pass
                        
            pil_img = pil_img.resize((w, h), PILImage.Resampling.NEAREST)
            img = np.array(pil_img)
        elif filter_type == "cmyk_dots":
            rgb = img[:,:,:3].astype(np.float32) / 255.0
            k = 1 - np.max(rgb, axis=2)
            c = (1 - rgb[:,:,2] - k) / (1 - k + 1e-5)
            m = (1 - rgb[:,:,1] - k) / (1 - k + 1e-5)
            y_ch = (1 - rgb[:,:,0] - k) / (1 - k + 1e-5)
            filtered_img = np.zeros_like(img)
            dot_size = 6
            small_w = max(1, w // dot_size)
            small_h = max(1, h // dot_size)
            c_small = cv2.resize(c, (small_w, small_h), interpolation=cv2.INTER_AREA)
            m_small = cv2.resize(m, (small_w, small_h), interpolation=cv2.INTER_AREA)
            y_small = cv2.resize(y_ch, (small_w, small_h), interpolation=cv2.INTER_AREA)
            k_small = cv2.resize(k, (small_w, small_h), interpolation=cv2.INTER_AREA)
            for y in range(small_h):
                for x in range(small_w):
                    cx, cy = x * dot_size + dot_size // 2, y * dot_size + dot_size // 2
                    r_c = int(c_small[y, x] * (dot_size / 2.0))
                    if r_c > 0: cv2.circle(filtered_img, (cx, cy), r_c, (255, 255, 0, 255), -1)
                    r_m = int(m_small[y, x] * (dot_size / 2.0))
                    if r_m > 0: cv2.circle(filtered_img, (cx, cy), r_m, (0, 255, 255, 255), -1)
                    r_y = int(y_small[y, x] * (dot_size / 2.0))
                    if r_y > 0: cv2.circle(filtered_img, (cx, cy), r_y, (255, 0, 255, 255), -1)
                    r_k = int(k_small[y, x] * (dot_size / 2.0))
                    if r_k > 0: cv2.circle(filtered_img, (cx, cy), r_k, (0, 0, 0, 255), -1)
            img = filtered_img
        elif filter_type == "halftone_print":
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
            dot_size = 6
            filtered_img = np.full_like(img, 255)
            small_w = max(1, w // dot_size)
            small_h = max(1, h // dot_size)
            small_gray = cv2.resize(gray, (small_w, small_h), interpolation=cv2.INTER_AREA)
            for y in range(small_h):
                for x in range(small_w):
                    intensity = 1.0 - (small_gray[y, x] / 255.0)
                    radius = int(intensity * (dot_size / 2.0))
                    if radius > 0:
                        center = (x * dot_size + dot_size // 2, y * dot_size + dot_size // 2)
                        cv2.circle(filtered_img, center, radius, (0, 0, 0, 255), -1)
            img = filtered_img
        elif filter_type == "dithered_1bit":
            gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2GRAY)
            bayer = np.tile(np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) * 16, (h//4 + 1, w//4 + 1))[:h, :w]
            dithered = np.where(gray > bayer, 255, 0)
            img[:,:,:3] = cv2.cvtColor(dithered.astype(np.uint8), cv2.COLOR_GRAY2RGB)
        elif filter_type == "punk_collage":
            img[:,:,:3] = cv2.convertScaleAbs(img[:,:,:3], alpha=1.5, beta=-50)
            for _ in range(20):
                x, y = np.random.randint(0, max(1, w//2)), np.random.randint(0, max(1, h//2))
                rw, rh = np.random.randint(50, 200), np.random.randint(50, 200)
                block = img[y:y+rh, x:x+rw].copy()
                dx, dy = np.random.randint(-50, 50), np.random.randint(-50, 50)
                ny, nx = np.clip(y+dy, 0, max(1, h-rh)), np.clip(x+dx, 0, max(1, w-rw))
                img[ny:ny+rh, nx:nx+rw] = block
        elif filter_type == "bootleg_pixel":
            small = cv2.resize(img, (max(1, w//32), max(1, h//32)), interpolation=cv2.INTER_LINEAR)
            img = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            hsv = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2HSV)
            hsv[:,:,0] = (hsv[:,:,0] + 90) % 180
            img[:,:,:3] = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            
        elif filter_type == "glitch_error":
            glitch_img = img.copy()
            for _ in range(15):
                y_start = np.random.randint(0, max(1, h - 20))
                y_end = y_start + np.random.randint(5, 20)
                dx = np.random.randint(-50, 50)
                slice_img = glitch_img[y_start:y_end, :].copy()
                glitch_img[y_start:y_end, :] = np.roll(slice_img, dx, axis=1)
            b, g, r, a = cv2.split(glitch_img)
            b = np.roll(b, 15, axis=1)
            r = np.roll(r, -15, axis=1)
            glitch_img = cv2.merge([b, g, r, a])
            for _ in range(5):
                x = np.random.randint(0, max(1, w-100))
                y = np.random.randint(0, max(1, h-100))
                glitch_img[y:y+50, x:x+50, 0] = 255 if np.random.rand() > 0.5 else 0
            img = glitch_img
            
        elif filter_type == "80_tech_wave":
            gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_RGB2GRAY)
            synth = np.zeros_like(img)
            synth[(gray > 180)] = [0, 255, 255, 255]
            synth[(gray > 80) & (gray <= 180)] = [255, 0, 255, 255]
            synth[gray <= 80] = [0, 0, 40, 255]
            vp_x, vp_y = w // 2, h
            for i in range(1, 20):
                y = int(h - (i * 15)**1.2)
                if y < 0: break
                cv2.line(synth, (0, y), (w, y), (255, 0, 255, 255), 1)
            for i in range(-10, 11):
                x_bot = vp_x + i * (w // 8)
                cv2.line(synth, (x_bot, h), (vp_x, int(h*0.6)), (255, 0, 255, 255), 1)
            img = synth

        return img.astype(np.float32)
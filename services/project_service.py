import logging
import cv2
import numpy as np
from typing import Optional
import copy
from core.models.project import Project, Layer
from core.models.layer import Mask, Transform
from core.models.palette import Palette
from core.enums import LayerType, BlendMode
from services.history_service import HistoryService

class ProjectService:
    
    def __init__(self, history_service: HistoryService, ai_detector=None):
        self.logger = logging.getLogger("PopArtGeneratorPro.ProjectService")
        self.history = history_service
        self.current_project: Optional[Project] = None
        self.raw_original_image: Optional[np.ndarray] = None
        self.current_spread: int = 56

    def create_project_from_image(self, image_data: np.ndarray, palette: Palette = None, spread: int = 56, template: str = "default"):
        self.raw_original_image = image_data.copy()
        self.current_spread = spread
        
        height, width = image_data.shape[:2]
        max_offset = 6 * spread
        canvas_w = width + max_offset
        
        self.current_project = Project(name="Untitled", width=canvas_w, height=height)
        
        bg_layer = Layer(id="bg", name="Background", type=LayerType.IMAGE, pixels=np.zeros((height, canvas_w, 4), dtype=np.uint8))
        bg_layer.pixels[:, :, 3] = 255
        self.current_project.add_layer(bg_layer)
        
        gray = cv2.cvtColor(image_data, cv2.COLOR_RGBA2GRAY)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        templates = {
            "default": {"colors": [(10,10,10), (255,255,255), (255,255,0), (128,128,128), (0,0,255), (0,255,0), (255,0,0)], "textures": []},
            "warhol": {"colors": [(255,0,255), (255,255,0), (0,255,255), (255,0,0)], "textures": ["screen_ink"]},
            "lichtenstein": {"colors": [(255,0,0), (255,255,0), (0,0,255), (10,10,10)], "textures": ["benday_dots"]},
            "punk": {"colors": [(255,0,0), (10,10,10), (255,255,255)], "textures": ["paper_grain"]},
            "banksy": {"colors": [(255,255,255), (128,128,128), (10,10,10)], "textures": ["spray_paint", "paint_drips"]},
            "murakami": {"colors": [(255,105,180), (0,191,255), (255,255,0), (255,255,255)], "textures": []},
            "haring": {"colors": [(255,0,0), (255,255,0), (0,255,0), (10,10,10)], "textures": ["line_screen"]},
            "hokusai": {"colors": [(0,51,102), (255,255,255), (255,127,80)], "textures": ["line_screen"]},
            "koons": {"colors": [(192,192,192), (255,255,255), (0,0,255), (255,0,0)], "textures": []},
            "basquiat": {"colors": [(10,10,10), (255,0,0), (255,255,0), (0,0,255)], "textures": ["graffiti_scribble", "paper_grain"]},
            "picasso": {"colors": [(13,71,161), (198,40,40), (251,192,45), (255,255,255), (106,27,154)], "textures": []}
        }
        
        if template == "banksy":
            _, gray = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
            
        selected_template = templates.get(template, templates["default"])
        forced_colors = selected_template["colors"]
        num_layers = len(forced_colors)
        
        for i in range(num_layers):
            color = forced_colors[i]
            ink_opacity = gray
            offset_x = (num_layers - 1 - i) * spread
            
            hex_name = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
            
            layer = self._generate_popart_layer(
                name=hex_name, 
                base_image=image_data, 
                gray_img=ink_opacity,
                color=color, 
                offset_x=offset_x, 
                offset_y=0,
                opacity=1.0,
                canvas_w=canvas_w
            )
            
            if i >= num_layers - 3:
                layer.visible = True
            else:
                layer.visible = False
                
            self.current_project.add_layer(layer)
            
        for tex in selected_template["textures"]:
            tex_layer = Layer(
                id=f"tex_{len(self.current_project.layers)}",
                name=f"Filter: {tex}",
                type=LayerType.ADJUSTMENT,
                pixels=None,
                filter_type=tex
            )
            self.current_project.add_layer(tex_layer)
            
        self.current_project.active_layer_index = len(self.current_project.layers) - 1
        self.history.save_state(self.current_project)
        return self.current_project

    def _generate_popart_layer(self, name: str, base_image: np.ndarray, gray_img: np.ndarray, color: tuple, offset_x: float, offset_y: float, opacity: float, canvas_w: int) -> Layer:
        height, width = gray_img.shape
        r, g, b = color
        
        colored_pixels = np.zeros((height, canvas_w, 4), dtype=np.float32)
        colored_pixels[:, :width, 0] = (gray_img * (r/255.0))
        colored_pixels[:, :width, 1] = (gray_img * (g/255.0))
        colored_pixels[:, :width, 2] = (gray_img * (b/255.0))
        colored_pixels[:, :width, 3] = gray_img
        
        M = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
        shifted_pixels = cv2.warpAffine(colored_pixels, M, (canvas_w, height))
        shifted_pixels = np.clip(shifted_pixels, 0, 255).astype(np.uint8)
        
        return Layer(
            id=name.lower().replace("#", ""),
            name=name,
            type=LayerType.IMAGE,
            pixels=shifted_pixels,
            mask=None,
            transform=Transform(x=0, y=0),
            opacity=opacity,
            blend_mode=BlendMode.SCREEN
        )

    def update_layer_color(self, index: int, color: tuple):
        if not self.current_project: return
        if 0 <= index < len(self.current_project.layers):
            layer = self.current_project.layers[index]
            if layer.pixels is not None and layer.type == LayerType.IMAGE:
                h, w = layer.pixels.shape[:2]
                new_pixels = np.zeros((h, w, 4), dtype=np.uint8)
                r, g, b = color
                alpha = layer.pixels[:, :, 3]
                new_pixels[:, :, 0] = (alpha * (r/255.0)).astype(np.uint8)
                new_pixels[:, :, 1] = (alpha * (g/255.0)).astype(np.uint8)
                new_pixels[:, :, 2] = (alpha * (b/255.0)).astype(np.uint8)
                new_pixels[:, :, 3] = alpha
                
                layer.pixels = new_pixels
                hex_name = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
                layer.name = hex_name
                layer.id = hex_name.lower().replace("#", "")
                self.history.save_state(self.current_project)

    def update_offset(self, spread: int):
        if self.raw_original_image is None or self.current_project is None: return
        self.create_project_from_image(self.raw_original_image, spread=spread)

    def add_empty_layer(self):
        if not self.current_project: return
        height, width = self.current_project.height, self.current_project.width
        empty_pixels = np.zeros((height, width, 4), dtype=np.uint8)
        new_layer = Layer(id=f"layer_{len(self.current_project.layers)}", name=f"Layer {len(self.current_project.layers)}", type=LayerType.IMAGE, pixels=empty_pixels)
        self.current_project.add_layer(new_layer)
        self.history.save_state(self.current_project)

    def add_adjustment_layer(self, filter_type: str):
        if not self.current_project: return
        name = f"Adjust: {filter_type}"
        valid_filters = [
            "blur", "sharpen", "halftone", "paper_grain", "canvas_texture", "film_grain", 
            "ink_bleed", "spray_paint", "paint_drips", "benday_dots", "line_screen", 
            "graffiti_scribble", "screen_ink", "cubist_facet", "fat_pixel", "16_bit", 
            "terminal", "risograph", "emoji_pop", "cmyk_dots", "halftone_print", 
            "dithered_1bit", "punk_collage", "bootleg_pixel", "glitch_error", "80_tech_wave"
        ]
        if filter_type in valid_filters:
            name = f"Filter: {filter_type}"
            
        new_layer = Layer(
            id=f"adj_{len(self.current_project.layers)}",
            name=name,
            type=LayerType.ADJUSTMENT,
            pixels=None,
            filter_type=filter_type
        )
        self.current_project.add_layer(new_layer)
        self.history.save_state(self.current_project)

    def duplicate_active_layer(self):
        if not self.current_project or self.current_project.active_layer_index == -1: return
        idx = self.current_project.active_layer_index
        orig = self.current_project.layers[idx]
        dup = copy.deepcopy(orig)
        dup.id = f"layer_{len(self.current_project.layers)}"
        dup.name = f"{orig.name} copy"
        self.current_project.layers.insert(idx + 1, dup)
        self.current_project.active_layer_index = idx + 1
        self.history.save_state(self.current_project)

    def delete_layer(self, index: int):
        if not self.current_project: return
        if 0 <= index < len(self.current_project.layers) and len(self.current_project.layers) > 1:
            self.current_project.layers.pop(index)
            self.current_project.active_layer_index = max(0, self.current_project.active_layer_index - 1)
            self.history.save_state(self.current_project)

    def move_layer(self, from_idx: int, to_idx: int):
        if not self.current_project: return
        if 0 <= from_idx < len(self.current_project.layers) and 0 <= to_idx < len(self.current_project.layers):
            layer = self.current_project.layers.pop(from_idx)
            self.current_project.layers.insert(to_idx, layer)
            self.current_project.active_layer_index = to_idx
            self.history.save_state(self.current_project)

    def resize_project(self, scale: float):
        if not self.current_project: return
        new_w = int(self.current_project.width * scale)
        new_h = int(self.current_project.height * scale)
        self.current_project.width = new_w
        self.current_project.height = new_h
        for layer in self.current_project.layers:
            if layer.pixels is not None:
                layer.pixels = cv2.resize(layer.pixels, (new_w, new_h))
        self.history.save_state(self.current_project)

    def resize_canvas(self, w: int, h: int):
        if not self.current_project: return
        self.current_project.width = w
        self.current_project.height = h
        for layer in self.current_project.layers:
            if layer.pixels is not None:
                old_h, old_w = layer.pixels.shape[:2]
                new_pixels = np.zeros((h, w, 4), dtype=np.uint8)
                min_w = min(w, old_w)
                min_h = min(h, old_h)
                new_pixels[:min_h, :min_w] = layer.pixels[:min_h, :min_w]
                layer.pixels = new_pixels
        self.history.save_state(self.current_project)
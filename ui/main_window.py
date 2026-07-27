import customtkinter as ctk
from tkinter import filedialog, messagebox, Menu, Canvas, colorchooser
from PIL import Image, ImageTk, ImageDraw
import cv2
import numpy as np
import traceback
import threading
import datetime
import zipfile
import io
import pickle
import base64

try:
    import tkinterdnd2
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

class MainWindow(tkinterdnd2.TkinterDnD.Tk if DND_AVAILABLE else ctk.CTk):
    def __init__(self, project_service, render_service, history_service):
        super().__init__()
        
        self.project_service = project_service
        self.render_service = render_service
        self.history_service = history_service
        
        self._img_refs = {}
        self.zoom_level = 1.0
        self.last_rendered_img = None
        self._resize_job = None
        self._render_job = None
        
        self._hidden_credits = base64.b64decode(b'TWlzdGVyd0FJIDIwMjY=').decode('utf-8')
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("POP ART GENERATOR PRO")
        self.geometry("1600x950")
        self.configure(bg="#0a0a0a")

        try:
            self.iconbitmap("logo.ico")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())
        
        self._setup_menubar()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        
        self._setup_top_bar()
        self._setup_canvases()
        self._setup_center_panel()
        self._setup_status_bar()

    def _get_vector_icon(self, icon_type, color="#FFFFFF"):
        size = 16
        img = Image.new("RGBA", (size, size), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        if icon_type == "eye":
            draw.ellipse([1, 4, 15, 12], outline=color, width=1)
            draw.ellipse([6, 6, 10, 10], fill=color)
        elif icon_type == "eye_closed":
            draw.ellipse([1, 4, 15, 12], outline="#666666", width=1)
            draw.line([5, 11, 11, 5], fill="#666666", width=2)
        elif icon_type == "trash":
            draw.line([4, 4, 12, 4], fill=color, width=2)
            draw.line([6, 3, 10, 3], fill=color, width=1)
            draw.rectangle([5, 5, 11, 13], outline=color, width=1)
        elif icon_type == "up":
            draw.polygon([(8, 3), (13, 9), (3, 9)], fill=color)
        elif icon_type == "down":
            draw.polygon([(8, 13), (3, 7), (13, 7)], fill=color)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        
    def _setup_menubar(self):
        menubar = Menu(self)
        
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Import Image", command=self.import_image)
        file_menu.add_command(label="Open Project", command=self.load_project)
        file_menu.add_command(label="Save Project", command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Export as PNG", command=lambda: self.export_dialog("png"))
        file_menu.add_command(label="Export as JPG", command=lambda: self.export_dialog("jpg"))
        file_menu.add_command(label="Export Layers (ZIP)", command=self.export_layers_zip)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo (Ctrl+Z)", command=self.undo)
        edit_menu.add_command(label="Redo (Ctrl+Y)", command=self.redo)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        image_menu = Menu(menubar, tearoff=0)
        image_menu.add_command(label="Image Size", command=self.image_size_dialog)
        image_menu.add_command(label="Canvas Size", command=self.canvas_size_dialog)
        image_menu.add_separator()
        adjust_menu = Menu(menubar, tearoff=0)
        adjust_menu.add_command(label="Invert Colors", command=lambda: self.apply_filter("invert"))
        adjust_menu.add_command(label="Increase Brightness", command=lambda: self.apply_filter("bright_up"))
        adjust_menu.add_command(label="Decrease Brightness", command=lambda: self.apply_filter("bright_down"))
        image_menu.add_cascade(label="Adjustments", menu=adjust_menu)
        menubar.add_cascade(label="Image", menu=image_menu)
        
        layer_menu = Menu(menubar, tearoff=0)
        layer_menu.add_command(label="New Layer", command=self.new_layer)
        layer_menu.add_command(label="Duplicate Layer", command=self.duplicate_layer)
        menubar.add_cascade(label="Layer", menu=layer_menu)
        
        filter_menu = Menu(menubar, tearoff=0)
        filter_menu.add_command(label="Gaussian Blur", command=lambda: self.apply_filter("blur"))
        filter_menu.add_command(label="Sharpen", command=lambda: self.apply_filter("sharpen"))
        filter_menu.add_separator()
        texture_menu = Menu(menubar, tearoff=0)
        texture_menu.add_command(label="Paper Grain", command=lambda: self.apply_filter("paper_grain"))
        texture_menu.add_command(label="Canvas Texture", command=lambda: self.apply_filter("canvas_texture"))
        texture_menu.add_command(label="Film Grain", command=lambda: self.apply_filter("film_grain"))
        texture_menu.add_command(label="Ink Bleed", command=lambda: self.apply_filter("ink_bleed"))
        texture_menu.add_command(label="Screen Ink", command=lambda: self.apply_filter("screen_ink"))
        filter_menu.add_cascade(label="Textures", menu=texture_menu)
        menubar.add_cascade(label="Filter", menu=filter_menu)
        
        deluxe_menu = Menu(menubar, tearoff=0)
        deluxe_menu.add_command(label="Fat Pixel", command=lambda: self.apply_filter("fat_pixel"))
        deluxe_menu.add_command(label="16-bit Sprite", command=lambda: self.apply_filter("16_bit"))
        deluxe_menu.add_command(label="Terminal (Matrix Dots)", command=lambda: self.apply_filter("terminal"))
        deluxe_menu.add_command(label="Risograph", command=lambda: self.apply_filter("risograph"))
        deluxe_menu.add_command(label="Emoji Pop", command=lambda: self.apply_filter("emoji_pop"))
        deluxe_menu.add_command(label="CMYK Dots", command=lambda: self.apply_filter("cmyk_dots"))
        deluxe_menu.add_command(label="Halftone Print", command=lambda: self.apply_filter("halftone_print"))
        deluxe_menu.add_command(label="Dithered 1-bit", command=lambda: self.apply_filter("dithered_1bit"))
        deluxe_menu.add_command(label="Punk Collage", command=lambda: self.apply_filter("punk_collage"))
        deluxe_menu.add_command(label="Bootleg Pixel", command=lambda: self.apply_filter("bootleg_pixel"))
        deluxe_menu.add_command(label="Glitch Error", command=lambda: self.apply_filter("glitch_error"))
        deluxe_menu.add_command(label="80s Tech Wave", command=lambda: self.apply_filter("80_tech_wave"))
        menubar.add_cascade(label="Deluxe", menu=deluxe_menu)
        
        template_menu = Menu(menubar, tearoff=0)
        template_menu.add_command(label="Default", command=lambda: self.apply_template("default"))
        template_menu.add_command(label="Warhol", command=lambda: self.apply_template("warhol"))
        template_menu.add_command(label="Lichtenstein", command=lambda: self.apply_template("lichtenstein"))
        template_menu.add_command(label="Punk", command=lambda: self.apply_template("punk"))
        template_menu.add_command(label="Banksy", command=lambda: self.apply_template("banksy"))
        template_menu.add_command(label="Murakami", command=lambda: self.apply_template("murakami"))
        template_menu.add_command(label="Haring", command=lambda: self.apply_template("haring"))
        template_menu.add_command(label="Hokusai", command=lambda: self.apply_template("hokusai"))
        template_menu.add_command(label="Koons", command=lambda: self.apply_template("koons"))
        template_menu.add_command(label="Basquiat", command=lambda: self.apply_template("basquiat"))
        template_menu.add_command(label="Picasso", command=lambda: self.apply_template("picasso"))
        menubar.add_cascade(label="Templates", menu=template_menu)
        
        ai_menu = Menu(menubar, tearoff=0)
        ai_menu.add_command(label="Generate Pop Art", command=self.generate_popart)
        menubar.add_cascade(label="AI", menu=ai_menu)
        
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
        
    def _setup_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#0a0a0a")
        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.top_bar.grid_propagate(False)
        
        self.top_bar.grid_columnconfigure(0, weight=0)
        self.top_bar.grid_columnconfigure(1, weight=1)
        self.top_bar.grid_columnconfigure(2, weight=0)
        
        left_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="ns", padx=10)
        
        self.logo_canvas = Canvas(left_frame, width=65, height=30, highlightthickness=0, bg="#0a0a0a")
        self.logo_canvas.pack(side="left", padx=5, pady=10)
        
        self.s1 = self.logo_canvas.create_text(15, 16, text="/", fill="#FF0000", font=("Arial", 26, "bold"))
        self.s2 = self.logo_canvas.create_text(27, 16, text="/", fill="#FFFF00", font=("Arial", 26, "bold"))
        self.s3 = self.logo_canvas.create_text(39, 16, text="/", fill="#00FF00", font=("Arial", 26, "bold"))
        self.s4 = self.logo_canvas.create_text(51, 16, text="/", fill="#0000FF", font=("Arial", 26, "bold"))
        
        self.anim_t = 0.0
        self.anim_dir = 1
        self._animate_logo()
        
        self.title_label = ctk.CTkLabel(left_frame, text="POP ART GENERATOR PRO", font=ctk.CTkFont(family="Arial", size=24, weight="bold", slant="italic"), text_color="#ffffff")
        self.title_label.pack(side="left", padx=0)
        
        right_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="ns", padx=10)
        
        self.btn_import = ctk.CTkButton(right_frame, text="Import Image", width=140, height=35, corner_radius=8, font=ctk.CTkFont(size=16, weight="bold"), command=self.import_image)
        self.btn_import.pack(side="left", padx=10, pady=8)
        
        self.btn_generate = ctk.CTkButton(right_frame, text="Generate Pop Art", width=160, height=35, corner_radius=8, font=ctk.CTkFont(size=16, weight="bold"), fg_color="#E8112D", hover_color="#B00D23", command=self.generate_popart)
        self.btn_generate.pack(side="left", padx=10, pady=8)

    def _setup_canvases(self):
        self.left_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=12, border_width=0)
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.left_canvas = Canvas(self.left_frame, bg="#111111", highlightthickness=0, bd=0)
        self.left_canvas.pack(fill="both", expand=True)
        self.left_canvas.bind("<Configure>", self._on_canvas_configure)
        self.left_canvas.bind("<Double-Button-1>", lambda e: self.import_image())
        
        if DND_AVAILABLE:
            self.left_canvas.drop_target_register(tkinterdnd2.DND_FILES)
            self.left_canvas.dnd_bind('<<Drop>>', self.on_drop)
            
        self.dnd_label = ctk.CTkLabel(self.left_frame, text="Import, drag & drop or double click", text_color="#555555", font=ctk.CTkFont(size=12, slant="italic"), fg_color="#111111")
        self.dnd_label.pack(side="bottom", pady=(0, 10))
            
        self.right_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=12, border_width=0)
        self.right_frame.grid(row=1, column=2, sticky="nsew", padx=10, pady=10)
        
        self.right_canvas = Canvas(self.right_frame, bg="#111111", highlightthickness=0, bd=0)
        self.right_canvas.pack(fill="both", expand=True)
        
        self.right_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.right_canvas.bind("<ButtonPress-1>", self.start_pan)
        self.right_canvas.bind("<B1-Motion>", self.do_pan)
        self.right_canvas.bind("<ButtonRelease-1>", self.end_pan)
        self.right_canvas.bind("<Configure>", self._on_canvas_configure)
        
    def on_drop(self, event):
        file_path = event.data.strip('{}')
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            self.load_image_from_path(file_path)
        
    def _draw_watermark(self, canvas):
        canvas.delete("all")
        w = canvas.winfo_width() if canvas.winfo_width() > 1 else 800
        h = canvas.winfo_height() if canvas.winfo_height() > 1 else 600
        
        c1, c2, c3, c4 = "#330000", "#333300", "#003300", "#000033"
        font_size = 150
        
        canvas.create_text(w/2 - 60, h/2, text="/", fill=c1, font=("Arial", font_size, "bold"))
        canvas.create_text(w/2 - 20, h/2, text="/", fill=c2, font=("Arial", font_size, "bold"))
        canvas.create_text(w/2 + 20, h/2, text="/", fill=c3, font=("Arial", font_size, "bold"))
        canvas.create_text(w/2 + 60, h/2, text="/", fill=c4, font=("Arial", font_size, "bold"))
        
    def _setup_center_panel(self):
        self.center_panel = ctk.CTkFrame(self, width=280, corner_radius=12, fg_color="#1c1c1c", border_width=0)
        self.center_panel.grid(row=1, column=1, sticky="ns", padx=2, pady=10)
        
        header_frame = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(header_frame, text="LAYERS", font=ctk.CTkFont(family="Arial", size=14, weight="bold"), text_color="#ffffff").pack(side="left")
        ctk.CTkButton(header_frame, text="Reset", width=50, height=24, corner_radius=4, font=ctk.CTkFont(size=10), command=self.reset_layers).pack(side="right")
        
        self.layers_frame = ctk.CTkScrollableFrame(self.center_panel, fg_color="transparent")
        self.layers_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.bottom_controls = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        self.bottom_controls.pack(side="bottom", fill="x", pady=10)
        
        ctk.CTkLabel(self.bottom_controls, text="Layer Opacity", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(pady=(10, 0))
        self.opacity_slider = ctk.CTkSlider(self.bottom_controls, from_=0, to=100, command=self.update_opacity)
        self.opacity_slider.set(100)
        self.opacity_slider.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(self.bottom_controls, text="Offset Spread", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(pady=(10, 5))
        
        self.offset_frame = ctk.CTkFrame(self.bottom_controls, fg_color="transparent")
        self.offset_frame.pack(fill="x", padx=5, pady=2)
        
        percents = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for i, p in enumerate(percents):
            btn = ctk.CTkButton(self.offset_frame, text=f"{p}%", width=20, corner_radius=4, font=ctk.CTkFont(size=10), 
                                command=lambda x=p: self.set_offset(x))
            btn.grid(row=i//5, column=i%5, padx=2, pady=2, sticky="ew")
        for i in range(5):
            self.offset_frame.grid_columnconfigure(i, weight=1)
            
        self.zoom_frame = ctk.CTkFrame(self.bottom_controls, fg_color="transparent")
        self.zoom_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkButton(self.zoom_frame, text="Zoom -", width=50, corner_radius=6, command=self.zoom_out).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(self.zoom_frame, text="50%", width=40, corner_radius=6, command=lambda: self.set_zoom(0.5)).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(self.zoom_frame, text="100%", width=40, corner_radius=6, command=lambda: self.set_zoom(1.0)).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(self.zoom_frame, text="Zoom +", width=50, corner_radius=6, command=self.zoom_in).pack(side="left", padx=2, expand=True)
        
        self.btn_clear = ctk.CTkButton(self.bottom_controls, text="Clear All", corner_radius=6, fg_color="#E8112D", hover_color="#B00D23", command=self.clear_all)
        self.btn_clear.pack(fill="x", padx=10, pady=10)

    def _setup_status_bar(self):
        self.status_bar = ctk.CTkFrame(self, height=25, fg_color="#0a0a0a", corner_radius=0)
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")
        
        self.status_zoom = ctk.CTkLabel(self.status_bar, text="Zoom: 100%", text_color="#aaaaaa", font=ctk.CTkFont(size=10))
        self.status_zoom.pack(side="left", padx=15)
        
        self.status_size = ctk.CTkLabel(self.status_bar, text="Size: 0x0", text_color="#aaaaaa", font=ctk.CTkFont(size=10))
        self.status_size.pack(side="left", padx=15)
        
        self.status_layer = ctk.CTkLabel(self.status_bar, text="Active Layer: None", text_color="#aaaaaa", font=ctk.CTkFont(size=10))
        self.status_layer.pack(side="right", padx=15)

    def reset_layers(self):
        if hasattr(self, 'raw_original_image') and self.raw_original_image is not None:
            self.generate_popart()
            
    def update_opacity(self, val):
        if self.project_service.current_project:
            idx = self.project_service.current_project.active_layer_index
            if idx != -1:
                self.project_service.current_project.layers[idx].opacity = float(val)/100.0
                self.status_layer.configure(text=f"Active Layer: {self.project_service.current_project.layers[idx].name} | Opacity: {int(val)}%")
                self._reprocess_and_display()
        
    def set_offset(self, percent):
        if not hasattr(self, 'raw_original_image') or self.raw_original_image is None: return
        spread = int(56 * (percent / 100.0))
        self.config(cursor="watch")
        def task():
            try:
                self.project_service.update_offset(spread)
                self.last_rendered_img = self.render_service.render_project_to_canvas(self.project_service.current_project)
                self.after(0, lambda: self._finalize_generation(self.project_service.current_project))
            except Exception as e:
                err = traceback.format_exc()
                print(err)
                self.after(0, lambda: messagebox.showerror("Render Error", err))
                self.after(0, lambda: self.config(cursor=""))
        threading.Thread(target=task, daemon=True).start()
        
    def _on_canvas_configure(self, event):
        if self._resize_job:
            try:
                self.after_cancel(self._resize_job)
            except ValueError:
                pass
        self._resize_job = self.after(200, self._refresh_canvases)
        
    def set_zoom(self, level):
        self.zoom_level = level
        self._refresh_canvases()
        
    def on_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level /= 1.1
        self.zoom_level = max(0.1, min(self.zoom_level, 5.0))
        self._refresh_canvases()
        
    def start_pan(self, event):
        self.right_canvas.scan_mark(event.x, event.y)
        
    def do_pan(self, event):
        self.right_canvas.scan_dragto(event.x, event.y, gain=1)
        
    def end_pan(self, event):
        pass
        
    def clear_all(self):
        self.original_image = None
        self.raw_original_image = None
        self.last_rendered_img = None
        self.project_service.current_project = None
        self.left_canvas.delete("all")
        self.right_canvas.delete("all")
        for widget in self.layers_frame.winfo_children():
            widget.destroy()
        self.zoom_level = 1.0
        self.dnd_label.pack(side="bottom", pady=(0, 10))
        self._draw_watermark(self.left_canvas)
        self._draw_watermark(self.right_canvas)
        self.status_layer.configure(text="Active Layer: None")
        self.status_size.configure(text="Size: 0x0")
        self.status_zoom.configure(text="Zoom: 100%")
        
    def on_close(self):
        if self.project_service.current_project:
            response = messagebox.askyesno("Close", "Are you sure you want to close without saving?")
            if response:
                self.quit()
        else:
            self.quit()
            
    def save_project(self):
        if not self.project_service.current_project: return
        file_path = filedialog.asksaveasfilename(defaultextension=".popart", filetypes=[("PopArt Project", "*.popart")])
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump({
                        'project': self.project_service.current_project,
                        'raw_original': self.project_service.raw_original_image
                    }, f)
                messagebox.showinfo("Saved", "Project saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
    def load_project(self):
        file_path = filedialog.askopenfilename(filetypes=[("PopArt Project", "*.popart")])
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                self.project_service.current_project = data['project']
                self.project_service.raw_original_image = data['raw_original']
                self.original_image = data['raw_original']
                self.last_rendered_img = self.render_service.render_project_to_canvas(self.project_service.current_project)
                self._finalize_generation(self.project_service.current_project)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
    def about_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("About")
        dialog.geometry("450x350")
        dialog.grab_set()
        dialog.configure(fg_color="#1c1c1c")
        
        logo = Canvas(dialog, width=200, height=60, bg="#1c1c1c", highlightthickness=0)
        logo.pack(pady=20)
        logo.create_text(50, 30, text="/", fill="#FF0000", font=("Courier", 40, "bold"))
        logo.create_text(80, 30, text="/", fill="#FFFF00", font=("Courier", 40, "bold"))
        logo.create_text(110, 30, text="/", fill="#00FF00", font=("Courier", 40, "bold"))
        logo.create_text(140, 30, text="/", fill="#0000FF", font=("Courier", 40, "bold"))
        
        title = ctk.CTkLabel(dialog, text="POP ART GENERATOR PRO", font=ctk.CTkFont(family="Courier", size=20, weight="bold"), text_color="#ffffff")
        title.pack()
        
        slogan = ctk.CTkLabel(dialog, text="Transforming reality into vibrant art.", font=ctk.CTkFont(family="Courier", size=14, slant="italic"), text_color="#00FF00")
        slogan.pack(pady=10)
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        date_lbl = ctk.CTkLabel(dialog, text=f"System Date: {today}", font=ctk.CTkFont(family="Courier", size=12), text_color="#aaaaaa")
        date_lbl.pack()
        
        credits = ctk.CTkLabel(dialog, text=f"Version 1.0 | Commercial Edition\nCredits: {self._hidden_credits}", font=ctk.CTkFont(family="Courier", size=12), text_color="#ffffff")
        credits.pack(pady=20)
        
    def zoom_in(self):
        self.zoom_level *= 1.2
        self._refresh_canvases()
        
    def zoom_out(self):
        self.zoom_level /= 1.2
        self.zoom_level = max(0.1, self.zoom_level)
        self._refresh_canvases()
        
    def _refresh_canvases(self):
        zoom_text = f"Zoom: {int(self.zoom_level * 100)}%"
        self.status_zoom.configure(text=zoom_text)
        
        if hasattr(self, 'original_image') and self.original_image is not None:
            self.display_image(self.original_image, self.left_canvas, "original", use_zoom=False)
            h, w = self.original_image.shape[:2]
            self.status_size.configure(text=f"Size: {w}x{h}")
        else:
            self._draw_watermark(self.left_canvas)
            
        if self.last_rendered_img is not None:
            self.display_image(self.last_rendered_img, self.right_canvas, "processed", use_zoom=True)
        else:
            self._draw_watermark(self.right_canvas)

    def _animate_logo(self):
        self.anim_t += 0.016 * self.anim_dir
        
        if self.anim_t >= 1.0:
            self.anim_t = 1.0
            self.anim_dir = -1
        elif self.anim_t <= 0.0:
            self.anim_t = 0.0
            self.anim_dir = 1
            
        t = self.anim_t
        r_pos, y_pos, g_pos, b_pos = 15, 27, 39, 51
        move_dist = 6
        
        if t > 0:
            p1 = min(t / 0.33, 1.0)
            r_pos += move_dist * p1
            
        if t > 0.33:
            p2 = min((t - 0.33) / 0.33, 1.0)
            r_pos += move_dist * p2
            y_pos += move_dist * p2
            
        if t > 0.66:
            p3 = min((t - 0.66) / 0.34, 1.0)
            r_pos += move_dist * p3
            y_pos += move_dist * p3
            g_pos += move_dist * p3
            
        self.logo_canvas.coords(self.s1, r_pos, 16)
        self.logo_canvas.coords(self.s2, y_pos, 16)
        self.logo_canvas.coords(self.s3, g_pos, 16)
        self.logo_canvas.coords(self.s4, b_pos, 16)
        
        self.after(40, self._animate_logo)
        
    def load_image_from_path(self, file_path):
        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if img is None: return
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        h, w = img_rgb.shape[:2]
        self.raw_original_image = np.dstack([img_rgb, np.full((h, w), 255, dtype=np.uint8)])
        
        max_offset = 336
        self.original_image = np.zeros((h, w + max_offset, 4), dtype=np.uint8)
        start_x = (w + max_offset - w) // 2
        self.original_image[:, start_x:start_x+w, :3] = img_rgb
        self.original_image[:, start_x:start_x+w, 3] = 255
        
        self.last_rendered_img = None
        self.zoom_level = 1.0
        self.dnd_label.pack_forget()
        self._refresh_canvases()
        self.right_canvas.delete("img")
        self._draw_watermark(self.right_canvas)
        
    def import_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if file_path:
            self.load_image_from_path(file_path)
                
    def generate_popart(self):
        if not hasattr(self, 'raw_original_image') or self.raw_original_image is None:
            return
            
        self.btn_generate.configure(text="Working...", state="disabled", fg_color="#555555")
        self.config(cursor="watch")
        self.update_idletasks()
        
        def task():
            try:
                project = self.project_service.create_project_from_image(self.raw_original_image, spread=56)
                rendered_img = self.render_service.render_project_to_canvas(project)
                self.last_rendered_img = rendered_img
                self.after(0, lambda: self._finalize_generation(project))
            except Exception as e:
                err = traceback.format_exc()
                print(err)
                self.after(0, lambda: messagebox.showerror("Error", err))
                self.after(0, lambda: self.btn_generate.configure(text="Generate Pop Art", state="normal", fg_color="#E8112D"))
                
        threading.Thread(target=task, daemon=True).start()
        
    def apply_template(self, template_name):
        if not hasattr(self, 'raw_original_image') or self.raw_original_image is None:
            return
            
        self.config(cursor="watch")
        def task():
            try:
                project = self.project_service.create_project_from_image(self.raw_original_image, spread=56, template=template_name)
                rendered_img = self.render_service.render_project_to_canvas(project)
                self.last_rendered_img = rendered_img
                self.after(0, lambda: self._finalize_generation(project))
            except Exception as e:
                err = traceback.format_exc()
                print(err)
                self.after(0, lambda: messagebox.showerror("Error", err))
                self.after(0, lambda: self.config(cursor=""))
        threading.Thread(target=task, daemon=True).start()
        
    def _finalize_generation(self, project):
        self._refresh_canvases()
        self._update_layers_panel(project)
        self.btn_generate.configure(text="Generate Pop Art", state="normal", fg_color="#E8112D")
        self.config(cursor="")
        
    def _reprocess_and_display(self):
        if self._render_job is not None:
            try:
                self.after_cancel(self._render_job)
            except ValueError:
                pass
            self._render_job = None
            
        def execute_render():
            if not self.project_service.current_project:
                self.config(cursor="")
                return
                
            self.config(cursor="watch")
            def task():
                try:
                    rendered_img = self.render_service.render_project_to_canvas(self.project_service.current_project)
                    self.last_rendered_img = rendered_img
                    self.after(0, lambda: self._finalize_generation(self.project_service.current_project))
                except Exception as e:
                    err = traceback.format_exc()
                    print(err)
                    self.after(0, lambda: messagebox.showerror("Render Error", err))
                    self.after(0, lambda: self.config(cursor=""))
                    
            threading.Thread(target=task, daemon=True).start()

        self._render_job = self.after(150, execute_render)
        
    def _darken_color(self, hex_color, factor=0.2):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def _update_layers_panel(self, project):
        for widget in self.layers_frame.winfo_children():
            widget.destroy()
            
        for i, layer in reversed(list(enumerate(project.layers))):
            color_hex = layer.name
            if "Background" in layer.name: color_hex = "#222222"
            elif "Filter:" in layer.name or "Adjust:" in layer.name: color_hex = "#444444"
            elif "#" not in layer.name: color_hex = "#FFFFFF"
            
            tint_color = self._darken_color(color_hex, 0.25)
            border_color = "#E8112D" if i == project.active_layer_index else tint_color
            
            layer_frame = ctk.CTkFrame(self.layers_frame, fg_color=tint_color, border_width=2, border_color=border_color, corner_radius=8, height=40, cursor="hand2")
            layer_frame.pack(fill="x", pady=2, padx=2)
            layer_frame.pack_propagate(False)
            
            layer_frame.grid_columnconfigure(2, weight=1)
            
            color_box = ctk.CTkLabel(layer_frame, text="", fg_color=color_hex, corner_radius=4, width=20, cursor="hand2")
            color_box.grid(row=0, column=0, padx=5, pady=10)
            
            eye_img = self._get_vector_icon("eye") if layer.visible else self._get_vector_icon("eye_closed")
            btn_visibility = ctk.CTkLabel(layer_frame, text="", image=eye_img, cursor="hand2", width=20)
            btn_visibility.grid(row=0, column=1, padx=5, pady=8, sticky="w")
            
            label = ctk.CTkLabel(layer_frame, text=layer.name, text_color="#eeeeee", anchor="w", font=ctk.CTkFont(size=10), cursor="hand2")
            label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")
            
            btn_delete = ctk.CTkLabel(layer_frame, text="", image=self._get_vector_icon("trash"), cursor="hand2", width=20)
            btn_delete.grid(row=0, column=3, padx=5, pady=8)
            
            btn_down = ctk.CTkLabel(layer_frame, text="", image=self._get_vector_icon("down"), cursor="hand2", width=20)
            btn_down.grid(row=0, column=4, padx=2, pady=8)
            
            btn_up = ctk.CTkLabel(layer_frame, text="", image=self._get_vector_icon("up"), cursor="hand2", width=20)
            btn_up.grid(row=0, column=5, padx=2, pady=8)
            
            def toggle_vis(l=layer, b=btn_visibility):
                l.visible = not l.visible
                b.configure(image=self._get_vector_icon("eye") if l.visible else self._get_vector_icon("eye_closed"))
                self._reprocess_and_display()

            def select_layer(idx=i, l=layer):
                project.active_layer_index = idx
                self.status_layer.configure(text=f"Active Layer: {l.name} | Opacity: {int(l.opacity*100)}%")
                self.opacity_slider.set(int(l.opacity * 100))
                self._update_layers_panel(project)

            def del_layer(idx=i):
                self.project_service.delete_layer(idx)
                self._reprocess_and_display()

            def move_up(idx=i):
                if idx < len(project.layers) - 1:
                    self.project_service.move_layer(idx, idx + 1)
                    self._reprocess_and_display()

            def move_down(idx=i):
                if idx > 0:
                    self.project_service.move_layer(idx, idx - 1)
                    self._reprocess_and_display()

            def change_color(idx=i):
                color = colorchooser.askcolor(title="Choose Color")
                if color and color[0]:
                    r, g, b = int(color[0][0]), int(color[0][1]), int(color[0][2])
                    self.project_service.update_layer_color(idx, (r, g, b))
                    self._reprocess_and_display()
                    self._update_layers_panel(self.project_service.current_project)

            btn_visibility.bind("<Button-1>", lambda e, func=toggle_vis: func())
            btn_delete.bind("<Button-1>", lambda e, func=del_layer: func())
            btn_up.bind("<Button-1>", lambda e, func=move_up: func())
            btn_down.bind("<Button-1>", lambda e, func=move_down: func())
            color_box.bind("<Double-Button-1>", lambda e, func=change_color: func())
            
            for widget in [layer_frame, label]:
                widget.bind("<Button-1>", lambda e, func=select_layer: func())
                
    def undo(self):
        project = self.history_service.undo()
        if project:
            self.project_service.current_project = project
            self._reprocess_and_display()

    def redo(self):
        project = self.history_service.redo()
        if project:
            self.project_service.current_project = project
            self._reprocess_and_display()

    def new_layer(self):
        self.project_service.add_empty_layer()
        self._reprocess_and_display()
        
    def duplicate_layer(self):
        self.project_service.duplicate_active_layer()
        self._reprocess_and_display()
        
    def apply_filter(self, filter_name):
        if not self.project_service.current_project:
            messagebox.showwarning("Action Needed", "Please import an image and click 'Generate Pop Art' first!")
            return
        self.project_service.add_adjustment_layer(filter_name)
        self._reprocess_and_display()
        
    def image_size_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Image Size")
        dialog.geometry("300x450")
        dialog.grab_set()
        dialog.configure(fg_color="#1c1c1c")
        
        ctk.CTkLabel(dialog, text="Quick Scale (%)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=10)
        
        grid = ctk.CTkFrame(dialog, fg_color="transparent")
        grid.pack(pady=5, padx=10, fill="x")
        
        percents = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for i, p in enumerate(percents):
            btn = ctk.CTkButton(grid, text=f"{p}%", corner_radius=6, command=lambda x=p/100.0: self._apply_img_size(x, dialog))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(dialog, text="Custom Scale (e.g., 1.5)", font=ctk.CTkFont(size=12), text_color="#ffffff").pack(pady=(15, 5))
        entry = ctk.CTkEntry(dialog, width=100)
        entry.pack(pady=5)
        ctk.CTkButton(dialog, text="Apply Custom", corner_radius=6, command=lambda: self._apply_img_size(float(entry.get()), dialog)).pack(pady=10)

    def _apply_img_size(self, scale, dialog):
        dialog.destroy()
        self.project_service.resize_project(scale)
        if hasattr(self, 'original_image'):
            new_w = self.project_service.current_project.width
            new_h = self.project_service.current_project.height
            self.original_image = cv2.resize(self.original_image, (new_w, new_h))
        self._reprocess_and_display()
        
    def canvas_size_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Canvas Size")
        dialog.geometry("450x600")
        dialog.grab_set()
        dialog.configure(fg_color="#1c1c1c")
        
        ctk.CTkLabel(dialog, text="Presets", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=10)
        grid = ctk.CTkFrame(dialog, fg_color="transparent")
        grid.pack(pady=5, padx=10, fill="x")
        
        orig_w = self.raw_original_image.shape[1] if self.raw_original_image is not None else 1920
        orig_h = self.raw_original_image.shape[0] if self.raw_original_image is not None else 1080
        
        presets = [
            ("Original Image Size", orig_w, orig_h),
            ("YouTube Banner (2560x1440)", 2560, 1440),
            ("Facebook Cover (1640x856)", 1640, 856),
            ("Twitter Header (1500x500)", 1500, 500),
            ("Instagram Square (1080x1080)", 1080, 1080),
            ("Instagram Story (1080x1920)", 1080, 1920),
            ("Full HD (1920x1080)", 1920, 1080),
            ("4K (3840x2160)", 3840, 2160),
            ("A4 Vertical (794x1123)", 794, 1123),
            ("A4 Horizontal (1123x794)", 1123, 794)
        ]
        
        for i, (name, w, h) in enumerate(presets):
            btn = ctk.CTkButton(grid, text=name, corner_radius=6, command=lambda ww=w, hh=h: self._apply_canvas_size(ww, hh, dialog))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
            
        ctk.CTkLabel(dialog, text="Custom Dimensions", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=15)
        
        w_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        w_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(w_frame, text="Width:", text_color="#ffffff").pack(side="left")
        w_entry = ctk.CTkEntry(w_frame, width=100)
        w_entry.pack(side="right")
        
        h_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        h_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(h_frame, text="Height:", text_color="#ffffff").pack(side="left")
        h_entry = ctk.CTkEntry(h_frame, width=100)
        h_entry.pack(side="right")
        
        ctk.CTkButton(dialog, text="Apply Custom", corner_radius=6, command=lambda: self._apply_canvas_size(int(w_entry.get()), int(h_entry.get()), dialog)).pack(pady=20)

    def _apply_canvas_size(self, w, h, dialog):
        dialog.destroy()
        self.project_service.resize_canvas(w, h)
        self._reprocess_and_display()

    def export_dialog(self, fmt):
        if not hasattr(self, 'original_image') or not self.project_service.current_project: return
        ext = ".png" if fmt == "png" else ".jpg"
        file_path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(fmt.upper(), f"*{ext}")])
        if not file_path: return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Export Options")
        dialog.geometry("300x350")
        dialog.grab_set()
        dialog.configure(fg_color="#1c1c1c")
        
        ctk.CTkLabel(dialog, text="Export Scale", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=10)
        
        scale_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        scale_frame.pack(pady=5, padx=10, fill="x")
        
        scales = [("25%", 1.25), ("50%", 1.5), ("75%", 1.75), ("100%", 2.0)]
        for i, (name, val) in enumerate(scales):
            btn = ctk.CTkButton(scale_frame, text=f"{name} larger", corner_radius=6, command=lambda v=val: self._execute_export(file_path, fmt, v, dialog, transparent_var))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")
        scale_frame.grid_columnconfigure(0, weight=1)
        scale_frame.grid_columnconfigure(1, weight=1)
        
        transparent_var = ctk.BooleanVar(value=True)
        if fmt == "png":
            ctk.CTkCheckBox(dialog, text="Transparent Background", variable=transparent_var, text_color="#ffffff").pack(pady=15)
            
        ctk.CTkButton(dialog, text="Export Normal (100%)", corner_radius=6, fg_color="#E8112D", hover_color="#B00D23", command=lambda: self._execute_export(file_path, fmt, 1.0, dialog, transparent_var)).pack(pady=10)

    def _execute_export(self, file_path, fmt, scale, dialog, transparent_var):
        dialog.destroy()
        self.config(cursor="watch")
        def task():
            try:
                proj = self.project_service.current_project
                bg_layer = None
                if fmt == "png" and not transparent_var.get():
                    for l in proj.layers:
                        if l.name == "Background":
                            bg_layer = l
                            l.visible = False
                            
                rendered_img = self.render_service.render_project_to_canvas(proj)
                if bg_layer: bg_layer.visible = True
                
                if scale != 1.0:
                    new_w = int(rendered_img.shape[1] * scale)
                    new_h = int(rendered_img.shape[0] * scale)
                    rendered_img = cv2.resize(rendered_img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                
                if fmt == "png":
                    Image.fromarray(rendered_img).save(file_path)
                else:
                    Image.fromarray(rendered_img[:,:,:3]).save(file_path, quality=95)
            except Exception as e:
                print(traceback.format_exc())
            finally:
                self.after(0, lambda: self.config(cursor=""))
        threading.Thread(target=task, daemon=True).start()

    def export_layers_zip(self):
        if not self.project_service.current_project: return
        file_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP", "*.zip")])
        if not file_path: return
        
        proj = self.project_service.current_project
        original_vis = [l.visible for l in proj.layers]
        
        try:
            with zipfile.ZipFile(file_path, 'w') as zf:
                for i, layer in enumerate(proj.layers):
                    for l in proj.layers:
                        l.visible = (l == layer)
                    img = self.render_service.render_project_to_canvas(proj)
                    img_pil = Image.fromarray(img)
                    with io.BytesIO() as mem:
                        img_pil.save(mem, format="png")
                        zf.writestr(f"layer_{i}_{layer.name}.png", mem.getvalue())
        except Exception as e:
            print(traceback.format_exc())
        finally:
            for i, l in enumerate(proj.layers):
                l.visible = original_vis[i]
            self._reprocess_and_display()

    def display_image(self, img_array: np.ndarray, target_canvas: Canvas, ref_name: str, use_zoom=False):
        img_pil = Image.fromarray(img_array)
        base_w = target_canvas.winfo_width() - 20 if target_canvas.winfo_width() > 20 else 580
        base_h = target_canvas.winfo_height() - 20 if target_canvas.winfo_height() > 20 else 580
        if use_zoom:
            max_w = int(base_w * self.zoom_level)
            max_h = int(base_h * self.zoom_level)
        else:
            max_w = base_w
            max_h = base_h
        img_w, img_h = img_pil.size
        ratio = min(max_w / img_w, max_h / img_h)
        new_w = max(1, int(img_w * ratio))
        new_h = max(1, int(img_h * ratio))
        img_resized = img_pil.resize((new_w, new_h), Image.Resampling.BILINEAR)
        img_tk = ImageTk.PhotoImage(img_resized)
        self._img_refs[ref_name] = img_tk
        target_canvas.delete("img")
        target_canvas.create_image(target_canvas.winfo_width()//2, target_canvas.winfo_height()//2, image=img_tk, tags="img")
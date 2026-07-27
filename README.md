🎨 POP ART GENERATOR PRO
Transforming reality into vibrant art.Commercial-grade desktop software for generating Pop Art, Silkscreen, Multi Exposure, and Transparent Layer artwork. Built with Python, OpenCV, and CustomTkinter.

Main Interface

📖 Table of Contents
Overview
Key Features
Artist Templates
Deluxe Filters
Tech Stack
Installation & Running
Screenshots
License
📌 Overview
POP ART GENERATOR PRO is a professional, non-destructive photo editing application designed specifically for creating contemporary gallery art. It automatically generates multiple translucent colored layers from any portrait, preserving facial details while producing rich overlapping colors. Every feature is editable in real-time, mimicking the workflow of industry-standard software like Adobe Photoshop but specialized in Pop Art generation.

✨ Key Features
🖌️ Layer System & Compositing
Unlimited Layers: Create, duplicate, merge, and delete layers seamlessly.
Non-Destructive Adjustment Layers: Apply filters that affect underlying layers without altering the original image data.
Advanced Blend Modes: Screen, Multiply, Overlay, and more for authentic ink overlapping effects.
Layer Opacity Control: Real-time slider for precise transparency adjustments.
Color Picker: Double-click any layer to change its base color instantly.
Drag & Drop: Import images directly into the canvas from your file explorer.
🎯 AI & Automation
AI Subject Detection: Automatic background removal and subject masking using MediaPipe.
Dynamic Offset Spread: Control the misregistration effect (silkscreen) with precision percentages (10% to 100%).
Auto Contrast & Grayscale Optimization: Enhances image details before color separation.
📂 Export & Project Management
Custom .popart Format: Save your entire project (layers, masks, effects) to a single file.
High-Quality Export: PNG (with optional transparent background) and JPG.
ZIP Export: Export all layers individually into a compressed ZIP file.
Resolution Scaling: Export at 25%, 50%, 75%, or 100% larger scales.
🎨 Artist Templates
One-click styles emulating the greatest Pop Art and contemporary artists:

Default: Vibrant 7-color separation.
Warhol: Neon silkscreen with screen ink texture.
Lichtenstein: Comic book style with Benday dots.
Banksy: Stencil street art with spray paint and drips.
Basquiat: Neo-expressionism with graffiti scribbles and paper grain.
Picasso: Cubist facets with a distinct blue period palette.
Murakami, Haring, Hokusai, Koons: Various curated palettes and textures.
🌌 Deluxe Filters
A collection of unique, real-time filters:

Glitch Error: Digital corruption and RGB splitting.
80s Tech Wave: Synthwave neon grid with magenta and cyan mapping.
Halftone Print: Classic newspaper dot matrix.
CMYK Dots: 4-color printing process simulation.
Risograph: 2-color ink offset with grain.
Emoji Pop: Image reconstruction using a palette of emojis.
Terminal (Matrix): Green phosphor dot matrix display.
...and many more (Fat Pixel, 16-bit, Punk Collage, Bootleg Pixel).
🛠 Tech Stack
Category	Technology
Language	Python 3.11+
GUI Framework	CustomTkinter, Tkinter, TkinterDnD2
Image Processing	OpenCV, NumPy, Pillow (PIL), scikit-image
AI / Vision	MediaPipe
GPU Rendering	ModernGL, PyOpenGL
🚀 Installation & Running
Option 1: From Source (Developers)
Clone the repository:
git clone https://github.com/misterw2000/pop-art-generator-pro.git
Navigate to the project folder:
bash

cd pop-art-generator-pro
Create and activate a virtual environment:
bash

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
Install dependencies:
bash

pip install customtkinter opencv-python numpy Pillow scikit-image moderngl PyOpenGL mediapipe onnxruntime tkinterdnd2
Run the application:
bash

python main.py
Option 2: Pre-compiled Executable
Download the latest PopArtGeneratorPro.exe from the Releases page and double-click to run. No installation required.

📸 Screenshots
Screenshot 1

Screenshot 2

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

<br>

Copyright (c) 2026 MisterwAI
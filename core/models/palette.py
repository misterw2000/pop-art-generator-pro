from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Palette:
    name: str
    colors: List[Tuple[int, int, int]] # Lista de colores RGB

# Paleta por defecto solicitada
DEFAULT_POP_ART_PALETTE = Palette(
    name="Default Pop Art",
    colors=[
        (255, 212, 0),    # Yellow #FFD400
        (232, 17, 45),    # Red #E8112D
        (236, 0, 140),    # Magenta #EC008C
        (249, 168, 212),  # Light Pink #F9A8D4
        (247, 148, 29),   # Orange #F7941D
        (41, 171, 226),   # Cyan #29ABE2
        (164, 206, 57),   # Lime #A4CE39
        (46, 158, 74),    # Green #2E9E4A
        (43, 46, 140),    # Blue #2B2E8C
        (0, 0, 0),        # Black #000000
        (255, 255, 255)   # White #FFFFFF
    ]
)
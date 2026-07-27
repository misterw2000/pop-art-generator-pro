from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np
from core.enums import BlendMode, LayerType

@dataclass
class Transform:
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0

@dataclass
class Mask:
    data: np.ndarray
    feather: float = 0.0
    invert: bool = False

@dataclass
class Effect:
    name: str
    params: dict
    enabled: bool = True

@dataclass
class Layer:
    id: str
    name: str
    type: LayerType
    pixels: Optional[np.ndarray] = None
    mask: Optional[Mask] = None
    effects: List[Effect] = field(default_factory=list)
    transform: Transform = field(default_factory=Transform)
    opacity: float = 1.0
    fill: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    visible: bool = True
    locked: bool = False
    color_label: str = "none"
    notes: str = ""
    filter_type: Optional[str] = None

@dataclass
class Project:
    name: str
    width: int
    height: int
    layers: List[Layer] = field(default_factory=list)
    active_layer_index: int = -1
    
    def add_layer(self, layer: Layer):
        self.layers.append(layer)
        self.active_layer_index = len(self.layers) - 1
        
    def remove_layer(self, index: int):
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
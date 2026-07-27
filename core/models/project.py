from dataclasses import dataclass, field
from typing import List
from core.models.layer import Layer
from core.models.palette import Palette

@dataclass
class Project:
    name: str
    width: int
    height: int
    layers: List[Layer] = field(default_factory=list)
    active_layer_index: int = -1
    palette: Palette = None
    
    def add_layer(self, layer: Layer):
        self.layers.append(layer)
        self.active_layer_index = len(self.layers) - 1
        
    def remove_layer(self, index: int):
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
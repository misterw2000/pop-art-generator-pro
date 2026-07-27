import logging
from core.models.project import Project, Layer
from core.models.layer import Mask, Transform, Effect

class HistoryService:
    def __init__(self):
        self.logger = logging.getLogger("PopArtGeneratorPro.HistoryService")
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 30

    def save_state(self, project: Project):
        new_proj = Project(
            name=project.name, 
            width=project.width, 
            height=project.height, 
            active_layer_index=project.active_layer_index
        )
        
        for layer in project.layers:
            new_pixels = layer.pixels.copy() if layer.pixels is not None else None
            
            new_mask = None
            if layer.mask and layer.mask.data is not None:
                new_mask = Mask(
                    data=layer.mask.data.copy(), 
                    feather=layer.mask.feather, 
                    invert=layer.mask.invert
                )
                
            new_transform = Transform(
                x=layer.transform.x, y=layer.transform.y, 
                rotation=layer.transform.rotation, 
                scale_x=layer.transform.scale_x, scale_y=layer.transform.scale_y
            )
            
            new_effects = [Effect(name=e.name, params=e.params.copy(), enabled=e.enabled) for e in layer.effects]
            
            new_layer = Layer(
                id=layer.id, name=layer.name, type=layer.type, pixels=new_pixels, mask=new_mask,
                effects=new_effects, transform=new_transform, opacity=layer.opacity, fill=layer.fill,
                blend_mode=layer.blend_mode, visible=layer.visible, locked=layer.locked,
                color_label=layer.color_label, notes=layer.notes, filter_type=layer.filter_type
            )
            new_proj.layers.append(new_layer)
            
        self.undo_stack.append(new_proj)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self) -> Project:
        if len(self.undo_stack) > 1:
            current = self.undo_stack.pop()
            self.redo_stack.append(current)
            return self.undo_stack[-1]
        return self.undo_stack[0] if self.undo_stack else None

    def redo(self) -> Project:
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            return state
        return None
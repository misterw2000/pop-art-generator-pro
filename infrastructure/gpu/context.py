import moderngl
import numpy as np
from typing import Optional

class GPUContext:
    """Gestiona el contexto de ModernGL para renderizado acelerado por hardware."""
    def __init__(self):
        self.ctx: Optional[moderngl.Context] = None
        self.programs: dict = {}
        self._initialize_context()
        self._compile_shaders()

    def _initialize_context(self):
        try:
            # Contexto standalone. En integración final Qt, se usará context sharing.
            self.ctx = moderngl.create_standalone_context()
            self.ctx.enable(moderngl.BLEND)
        except Exception as e:
            raise RuntimeError(f"Fallo al inicializar ModernGL context: {e}")

    def _compile_shaders(self):
        vertex_shader = """
        #version 330
        in vec2 in_vert;
        in vec2 in_uv;
        out vec2 uv;
        void main() {
            uv = in_uv;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """
        
        fragment_shader = """
        #version 330
        uniform sampler2D base_texture;
        uniform sampler2D blend_texture;
        uniform float opacity;
        uniform int blend_mode;
        in vec2 uv;
        out vec4 fragColor;
        
        vec3 blend_normal(vec3 base, vec3 blend) { return blend; }
        vec3 blend_multiply(vec3 base, vec3 blend) { return base * blend; }
        vec3 blend_screen(vec3 base, vec3 blend) { return 1.0 - (1.0 - base) * (1.0 - blend); }
        
        void main() {
            vec4 base_col = texture(base_texture, uv);
            vec4 blend_col = texture(blend_texture, uv);
            vec3 result = base_col.rgb;
            
            if (blend_mode == 0) result = blend_normal(base_col.rgb, blend_col.rgb);
            else if (blend_mode == 1) result = blend_multiply(base_col.rgb, blend_col.rgb);
            else if (blend_mode == 2) result = blend_screen(base_col.rgb, blend_col.rgb);
            
            fragColor = vec4(result, blend_col.a * opacity);
        }
        """
        
        self.programs["composite"] = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
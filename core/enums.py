from enum import Enum

class BlendMode(Enum):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    COLOR_DODGE = "color_dodge"
    LINEAR_DODGE = "linear_dodge"
    ADD = "add"
    SUBTRACT = "subtract"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    LUMINOSITY = "luminosity"
    HUE = "hue"
    COLOR = "color"
    SATURATION = "saturation"
    PIN_LIGHT = "pin_light"
    VIVID_LIGHT = "vivid_light"
    LINEAR_BURN = "linear_burn"
    HARD_MIX = "hard_mix"

class LayerType(Enum):
    IMAGE = "image"
    ADJUSTMENT = "adjustment"
    TEXT = "text"
    SMART_OBJECT = "smart_object"
    GROUP = "group"

class ColorSpace(Enum):
    RGB = "rgb"
    CMYK = "cmyk"
    GRAYSCALE = "grayscale"
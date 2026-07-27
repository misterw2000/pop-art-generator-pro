import cv2
import numpy as np
import mediapipe as mp
import logging

class SubjectDetector:
    def __init__(self):
        self.logger = logging.getLogger("PopArtGeneratorPro.SubjectDetector")
        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        self.segmenter = self.mp_selfie_segmentation.SelfieSegmentation(model_selection=1)

    def extract_subject_mask(self, image_data: np.ndarray) -> np.ndarray:
        self.logger.info("Running AI segmentation...")
        
        if image_data.shape[2] == 4:
            image_rgb = cv2.cvtColor(image_data, cv2.COLOR_RGBA2RGB)
        else:
            image_rgb = image_data
            
        results = self.segmenter.process(image_rgb)
        mask = results.segmentation_mask
        
        binary_mask = (mask > 0.5).astype(np.uint8) * 255
        return binary_mask
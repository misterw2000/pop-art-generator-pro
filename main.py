import sys
import os

if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)

import logging
import numpy as np

from services.project_service import ProjectService
from services.render_service import RenderService
from services.history_service import HistoryService
from ui.main_window import MainWindow
from infrastructure.gpu.context import GPUContext

class ApplicationContainer:
    def __init__(self):
        self.logger = self._setup_logging()
        self.gpu_context = GPUContext()
        self.history_service = HistoryService()
        self.render_service = RenderService(self.gpu_context)
        self.project_service = ProjectService(self.history_service)

    def _setup_logging(self):
        logger = logging.getLogger("PopArtGeneratorPro")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

def main():
    container = ApplicationContainer()
    app = MainWindow(
        project_service=container.project_service,
        render_service=container.render_service,
        history_service=container.history_service
    )
    app.mainloop()

if __name__ == "__main__":
    main()

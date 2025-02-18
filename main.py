# This Python file uses the following encoding: utf-8
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator

from qfluentwidgets import FluentTranslator

from app.common.config import cfg
from app.view.main_window import MainWindow


if __name__ == "__main__":

    # enable dpi scale
    if cfg.get(cfg.dpiScale) != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # internationalization
    locale = cfg.get(cfg.language).value
    translator = FluentTranslator(locale)
    galleryTranslator = QTranslator()
    galleryTranslator.load(locale, "gallery", ".", ":/gallery/i18n")

    app.installTranslator(translator)
    app.installTranslator(galleryTranslator)
    app.setQuitOnLastWindowClosed(False)

    # create main window
    w = MainWindow()
    w.show()

    sys.exit(app.exec())

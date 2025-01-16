# coding: utf-8
from typing import List
from PySide6.QtCore import Qt, QUrl, QSize, QTimer
from PySide6.QtGui import QIcon, QDesktopServices, QAction
from PySide6.QtWidgets import QApplication,  QSystemTrayIcon, QMenu

from qfluentwidgets import (NavigationItemPosition, FluentWindow,
                            SplashScreen, SystemThemeListener, isDarkTheme)
from qfluentwidgets import FluentIcon as FIF

from .gallery_interface import GalleryInterface

from .ouc_net import OUCNet

from ..common.config import ZH_SUPPORT_URL, EN_SUPPORT_URL, cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common.translator import Translator
from ..common import resource

import platform

class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.initWindow()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # create sub interface
        # self.homeInterface = HomeInterface(self)
        self.oucNet = OUCNet(self)

        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('app/resources/icon_256x256.png'))  # 使用自定义图标
        self.tray_icon.setVisible(True)

        # 创建托盘菜单
        tray_menu = QMenu(self)
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.restore_window)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_application)

        tray_menu.addAction(restore_action)
        tray_menu.addAction(exit_action)

        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)

        # 设置关闭事件，使应用最小化到托盘而不是退出
        if platform.system() == 'Darwin':
            self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint)
        else:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint)

        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        self.connectSignalToSlot()

        # add items to navigation interface
        self.initNavigation()
        self.splashScreen.finish()

        # start theme listener
        self.themeListener.start()

    def restore_window(self):
        """恢复窗口"""
        self.show()
        self.activateWindow()  # 确保恢复时窗口激活

    def exit_application(self):
        """退出应用"""
        QApplication.quit()

    def on_tray_icon_activated(self, reason):
        """当托盘图标被点击时，恢复窗口"""
        if reason == QSystemTrayIcon.Trigger:
            self.restore_window()

    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.switchToSampleCard.connect(self.switchToSample)
        signalBus.supportSignal.connect(self.onSupport)

    def initNavigation(self):
        # add navigation items
        t = Translator()
        # self.addSubInterface(self.homeInterface, FIF.HOME, self.tr('Home'))
        # self.addSubInterface(self.iconInterface, Icon.EMOJI_TAB_SYMBOLS, t.icons)
        self.navigationInterface.addSeparator()

        pos = NavigationItemPosition.SCROLL

        # Mass
        self.addSubInterface(self.oucNet, FIF.CHAT, self.tr('OucNet'))

        # self.addSubInterface(self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(960, 780)
        self.setMinimumWidth(760)
        if platform.system() == 'Darwin':
            self.setWindowIcon(QIcon('app.icns'))
        else:
            self.setWindowIcon(QIcon('app/resources/icon_256x256.png'))

        self.setWindowTitle('OUC校园网工具')

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

    def onSupport(self):
        language = cfg.get(cfg.language).value
        if language.name() == "zh_CN":
            QDesktopServices.openUrl(QUrl(ZH_SUPPORT_URL))
        else:
            QDesktopServices.openUrl(QUrl(EN_SUPPORT_URL))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())

    def closeEvent(self, e):
        """当关闭窗口时，不退出应用，而是将其隐藏到托盘"""
        self.setWindowIcon(QIcon())
        e.ignore()  # 忽略关闭事件
        self.hide()     # 隐藏主窗口
        # self.themeListener.terminate()
        # self.themeListener.deleteLater()
        # super().closeEvent(e)

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()
        # retry
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def switchToSample(self, routeKey, index):
        """ switch to sample """
        interfaces = self.findChildren(GalleryInterface)
        for w in interfaces:
            if w.objectName() == routeKey:
                self.stackedWidget.setCurrentWidget(w, False)
                w.scrollToCard(index)

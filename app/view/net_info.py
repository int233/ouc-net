# This Python file uses the following encoding: utf-8
from typing import List, Union

from qfluentwidgets.common.icon import FluentIconBase

from PySide6.QtCore import Qt, Signal, QObject

from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath, QFont, QIcon

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QApplication

from qfluentwidgets import (IconWidget, BodyLabel, InfoBarIcon, FluentIcon, HyperlinkLabel, PushButton, EditableComboBox ,InfoBar, InfoBarPosition, CheckBox, LineEdit, PasswordLineEdit, PrimaryPushButton,HeaderCardWidget, CardGroupWidget )

from loguru import logger
import requests
import json
import os

class GroupHeaderCardWidget(HeaderCardWidget):
    """ Group header card widget """

    def _postInit(self, columns_num = 3):
        super()._postInit()
        self.groupWidgets = []  # type: List[CardGroupWidget]
        self.groupLayout = QGridLayout()

        self.groupLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.groupLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.addLayout(self.groupLayout)

        self.groupIndexes = {}

        # 设置网格布局的行列数
        self.currentRow = 0
        self.currentColumn = 0
        self.maxColumns = columns_num  # 每行最多3个group

    def addGroup(self, icon: Union[str, FluentIconBase, QIcon], title: str, content: str, widget: QWidget | list = None, stretch=0, group_index : int = None) -> CardGroupWidget:
        """ add widget to a new group

        Parameters
        ----------
        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        widget: QWidget
            the widget to be added

        stretch: int
            the layout stretch of widget
        """


        group = CardGroupWidget(icon, title, content, self)

        if widget:
            if isinstance(widget, list):
                for w in widget:
                    group.addWidget(w, stretch=stretch)
            else:
                group.addWidget(widget, stretch=stretch)

        if self.groupWidgets:
            self.groupWidgets[-1].setSeparatorVisible(True)

        # 添加group到网格布局
        self.groupLayout.addWidget(group, self.currentRow, self.currentColumn)

        # 更新当前行和列
        self.groupWidgets.append(group)
        self.currentColumn += 1

        # 如果group_index不为空，存储该索引
        if group_index is not None:
            self.groupIndexes[group_index] = group

        # 如果当前列数超过最大列数，则换行
        if self.currentColumn >= self.maxColumns:
            self.currentColumn = 0
            self.currentRow += 1
        return group

    def groupCount(self):
        logger.debug(f"Widges Counts: {len(self.groupWidgets)}")
        return len(self.groupWidgets)
    
    def removeGroup(self, group_index: int):
        """Remove group widget by index."""
        group = self.groupIndexes.get(group_index)

        if group:
            # 从布局中移除控件
            self.groupLayout.removeWidget(group)
            # 删除控件
            group.deleteLater()

            # 更新groupWidgets，删除对应的group
            if group in self.groupWidgets:
                self.groupWidgets.remove(group)
            
            # 清除group_index索引
            if group_index in self.groupIndexes:
                del self.groupIndexes[group_index]
    def removeAll(self):
        """Remove all groups/widgets."""
        for group in self.groupWidgets:
            # 从布局中移除控件
            self.groupLayout.removeWidget(group)
            # 删除控件
            group.deleteLater()

        # 清空groupWidgets列表
        self.groupWidgets.clear()

        # 清空groupIndexes字典
        self.groupIndexes.clear()

class NetInfoCard(GroupHeaderCardWidget):
    """ System requirements card """

    def __init__(self, title, netInfo, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setBorderRadius(8)

        self.netInfo = self.format_info(netInfo)

        self.copyipv4Button = PushButton(FluentIcon.COPY, "复制")
        self.copyipv6Button = PushButton(FluentIcon.COPY, "复制")
        self.chooseButton = PushButton("选择")
        self.comboBox_selectID = EditableComboBox()
        self.comboBox_selectNetInterface = EditableComboBox()

        self.hintIcon = IconWidget(InfoBarIcon.INFORMATION)
        self.hintLabel1 = BodyLabel("选择账号")
        self.hintLabel2 = BodyLabel("选择网络接口")
        self.signinButton = PrimaryPushButton(FluentIcon.MOVE, "登录")
        self.signinButton.clicked.connect(self.signinClicked)
        self.signoutButton = PushButton(FluentIcon.MOVE, "注销")
        self.signoutButton.clicked.connect(self.signoutClicked)
        self.bottomLayout = QHBoxLayout()

        self.chooseButton.setFixedWidth(120)
        self.comboBox_selectID.setFixedWidth(160)

        # 获取用户id
        self.comboBox_selectNetInterface.setFixedWidth(160)
        self.comboBox_selectNetInterface.addItems(["无线网络", "有线网络"])
        self.comboBox_selectNetInterface.setCurrentIndex(0)


        # 设置底部工具栏布局
        self.hintIcon.setFixedSize(16, 16)
        self.bottomLayout.setSpacing(10)
        self.bottomLayout.setContentsMargins(24, 15, 24, 20)
        self.bottomLayout.addWidget(self.hintIcon, 0, Qt.AlignLeft)
        self.bottomLayout.addWidget(self.hintLabel1, 0, Qt.AlignLeft)
        self.bottomLayout.addWidget(self.comboBox_selectID, 0, Qt.AlignLeft)
        self.bottomLayout.addWidget(self.hintLabel2, 0, Qt.AlignLeft)
        self.bottomLayout.addWidget(self.comboBox_selectNetInterface, 0, Qt.AlignLeft)
        self.bottomLayout.addStretch(1)
        self.bottomLayout.addWidget(self.signoutButton, 0, Qt.AlignRight)
        self.bottomLayout.addWidget(self.signinButton, 0, Qt.AlignRight)
        self.bottomLayout.setAlignment(Qt.AlignVCenter)

        # 添加组件到分组中
        self.addGroup(FluentIcon.INFO, "IPv4地址", "Unknown")
        self.addGroup(FluentIcon.IOT, "IPv6地址", "Unknown")
        self.addGroup(FluentIcon.INFO, "联网方式", "Unknown")
        self.addGroup(FluentIcon.INFO, "DNS", "Unknown")
        self.addGroup(FluentIcon.INFO, "MAC", "Unknown")
        group =  self.addGroup(FluentIcon.INFO, "用户", "Unknown")

        group.setSeparatorVisible(True)

        # 添加底部工具栏
        self.vBoxLayout.addLayout(self.bottomLayout)
    
    def format_info(self, netInfo):
        """ Format net info """

        empty_info = {
            "online_status": "Unknown",
            "IP": "Unknown",
            "IPv6": "Unknown",
            "MAC": "Unknown",
            "interface": "Unknown",
            "DNS": "Unknown",
            "id": "Unknown",
            "device": [
                {
                },
            ]
        }

        offline_info = {
            "online_status": "Offline",
            "IP": "Unknown",
            "IPv6": "Unknown",
            "MAC": "Unknown",
            "interface": "Unknown",
            "DNS": "Unknown",
            "id": "Unknown",
            "device": [
                {
                },
            ]
        }

        tmp_info = netInfo

        if tmp_info is None:
            self.netInfo = empty_info
            return empty_info
        
        if tmp_info['online_status'] == 'Offline':
            self.netInfo = offline_info

        self.netInfo = netInfo
        return self.netInfo

    def update_info(self, netInfo):
        """ Update net info """
        self.format_info(netInfo)

        self.groupWidgets[0].setContent(self.netInfo['IP'])
        if isinstance(self.netInfo['IPv6'], list):
            self.groupWidgets[1].setContent(self.netInfo['IPv6'][0])
        else:
            self.groupWidgets[1].setContent(self.netInfo['IPv6'])

        self.groupWidgets[2].setContent(self.netInfo['interface'])

        if isinstance(self.netInfo['DNS'], list):
            self.groupWidgets[3].setContent("; ".join(self.netInfo['DNS']))
        else:
            self.groupWidgets[3].setContent(self.netInfo['DNS'])
        self.groupWidgets[4].setContent(self.netInfo['MAC'].upper())
        self.groupWidgets[5].setContent(self.netInfo['id'])
    
    def signinClicked(self):

        uid = self.comboBox_selectID.currentText()

        try:
            password = self.uids[uid][0]
            logger.info(f"pass for {uid}: {password}")
        except Exception as e: 
            password = None
            logger.error(f"No Password for {uid}, for: {e}")

        net_interface = self.comboBox_selectNetInterface.currentText()

        logger.info(f"Sign in clicked, id: {uid}, interface: {net_interface}, password: {password}")

        url = f"https://xha.ouc.edu.cn:802/eportal/portal/login?callback=dr1003&login_method=1&user_account={uid}&user_password={password}&wlan_user_ip=0.0.0.0&wlan_user_ipv6=&wlan_user_mac=&wlan_ac_ip=&wlan_ac_name=&jsVersion=4.1&terminal_type=1&lang=zh-cn&v=5927&lang=zh"
        response = requests.get(url)
        # 检查响应状态
        if response.status_code == 200:
            logger.info("login action send successfully")
            logger.debug(f"replay: {response.text}")
            InfoBar.success(
                title='登录',
                content=f"已成功登录了{uid}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        else:
            logger.debug(f"login failed: {response.status_code}")

    def signoutClicked(self):

        uid = self.comboBox_selectID.currentText()

        currentuid = self.netInfo

        net_interface = self.comboBox_selectNetInterface.currentText()

        logger.info(f"Sign in clicked, id: {uid}, interface: {uid}")
        
        url = f"https://xha.ouc.edu.cn:802/eportal/portal/logout?callback=dr1006&login_method=1&user_account=drcom&user_password=123&ac_logout=0&register_mode=1&wlan_user_ip=0.0.0.0&wlan_user_ipv6=&wlan_vlan_id=1&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&jsVersion=4.1&bas_ip=xha.ouc.edu.cn&type=1&v=1798&lang=zh"
        response = requests.get(url)
        # 检查响应状态
        if response.status_code == 200:
            logger.info("login action send successfully")
            logger.debug(f"replay: {response.text}")
            InfoBar.success(
                title='注销',
                content=f"已注销了{self.netInfo['IP']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.window()
            )
        else:
            logger.debug(f"login failed: {response.status_code}")

    def updateuids(self, uids_dict:dict):

        self.uids = uids_dict
        self.comboBox_selectID.clear()
        self.comboBox_selectID.addItems(uids_dict.keys())
        try:
            self.comboBox_selectID.setText([key for key, value in uids_dict.items() if value[1] is True][0])
        except IndexError as e:
            logger.warning(f"No auto login id: {e}")
        except Exception as e:
            logger.error(f"Failed to set default id: {e}")

        logger.info(f"Get uids: {self.uids}")
        # self.comboBox_selectID.setText()
        
class IDManagerCard(GroupHeaderCardWidget):
    """ System requirements card """

    changed_uids = Signal(dict)

    def __init__(self, title, ids : dict = None, columns_num=1, parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setBorderRadius(8)

        self._postInit(columns_num = columns_num)

        if ids is None:
            self.ids = {}
        else:
            self.ids = ids
        
        self.user_data_path = os.path.join(os.path.expanduser("~"), "net_ids.json")
        self.load_data()

        self.changed_uids.emit(self.ids)

        self.line_uid = {}
        self.line_password = {}
        self.checkbox = {}
        self.line_delete = {}
        self.line_save = {}
        
        self.button_create = PrimaryPushButton(FluentIcon.ADD, "新建账号")
        self.button_save = PrimaryPushButton(FluentIcon.SAVE, "保存")
        self.button_reset = PushButton(FluentIcon.RETURN, "重置")
        self.button_create.clicked.connect(lambda: self.createClicked(index=None))
        self.button_save.clicked.connect(self.saveClicked)
        self.button_reset.clicked.connect(self.resetClicked)

        # 设置底部工具栏布局
        self.bottomLayout = QHBoxLayout()
        self.bottomLayout.setSpacing(10)
        self.bottomLayout.setContentsMargins(24, 15, 24, 20)
        self.bottomLayout.addStretch(1)
        self.bottomLayout.addWidget(self.button_create, 0, Qt.AlignRight)
        self.bottomLayout.addWidget(self.button_save, 0, Qt.AlignRight)
        self.bottomLayout.addWidget(self.button_reset, 0, Qt.AlignRight)
        self.bottomLayout.setAlignment(Qt.AlignVCenter)

        # 添加组件到分组中
        for index, (uid, values) in enumerate(self.ids.items()):
            password, auto = values
            self.createIDitem(index, uid, password, auto)

        # 添加底部工具栏
        self.vBoxLayout.addLayout(self.bottomLayout)

    def createIDitem(self, index, uid = '', password = '', auto = False):
        
        self.line_uid[index] = LineEdit()
        self.line_uid[index].setText(uid)

        self.line_password[index] = PasswordLineEdit()
        self.line_password[index].setText(password)

        self.checkbox[index] = CheckBox("自动登录")
        self.checkbox[index].setChecked(auto)
        self.checkbox[index].stateChanged.connect(self.on_checkbox_state_changed)

        self.line_delete[index] = PushButton(FluentIcon.DELETE, "删除")
        self.line_delete[index].clicked.connect(lambda: self.removeGroup(index))
        self.line_save[index] = PrimaryPushButton(FluentIcon.SAVE, "保存")

        return self.addGroup(FluentIcon.INFO, "账号","账号",[self.line_uid[index],self.line_password[index], self.checkbox[index], self.line_delete[index]],group_index=index )

    def on_checkbox_state_changed(self):
        # 获取当前状态改变的checkbox
        sender = self.sender()
        
        # 遍历所有的checkbox
        if sender.isChecked():
            # 遍历所有的checkbox
            for key, checkbox in self.checkbox.items():
                # 如果当前checkbox不是发送信号的checkbox，并且它被勾选，则取消勾选
                if checkbox != sender and checkbox.isChecked():
                    checkbox.setChecked(False)

    def resetClicked(self):
        """ Reset clicked """
        self.line_uid = {}
        self.line_password = {}
        self.checkbox = {}
        self.line_delete = {}
        self.line_save = {}
        self.removeAll()

        for index, (uid, values) in enumerate(self.ids.items()):
            password, auto = values 
            self.createIDitem(index, uid, password, auto)

    def createClicked(self, index = None ):
        logger.info(f"raw index: {index}, (type: {type(index)})")
        if index is None or not isinstance(index, int):
            logger.info(f"get index: {index}")
            index = self.groupCount()
        
        logger.info(f"Create clicked, new index: {index}")
        self.createIDitem(index = index)

    def saveClicked(self):
        """ Save clicked """
        ids = {}
        counts = self.groupCount()

        for i in range(counts):
            uid = self.line_uid[i].text()
            password = self.line_password[i].text()
            auto = self.checkbox[i].isChecked()
            ids[uid] = [password, auto]
        
        self.ids = ids
        self.save_data()
        self.changed_uids.emit(self.ids)
        logger.info(f"Save clicked, ids: {self.ids}")

        InfoBar.success(
            title='成功',
            content="已将账号和密码保存至本地",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )
    
    def save_data(self):
        """将数据保存到本地JSON文件"""
        try:
            with open(self.user_data_path, "w") as f:
                json.dump(self.ids, f)
            logger.info(f"Data saved to: {self.user_data_path}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_data(self, return_data = False):
        """从本地JSON文件读取数据"""
        try:
            if os.path.exists(self.user_data_path):
                with open(self.user_data_path, "r") as f:
                    self.ids = json.load(f)
                logger.info(f"Data loaded from: {self.user_data_path}")
                if return_data:return self.ids
            else:
                logger.info("No saved data found.")
                self.ids = {}
        except Exception as e:
            logger.info(f"Error loading data: {e}")
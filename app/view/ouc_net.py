# coding:utf-8
from PySide6.QtCore import Qt,  QTimer, QThread, Signal
from PySide6.QtWidgets import QCompleter
from qfluentwidgets import (LineEdit, SpinBox, DoubleSpinBox, TimeEdit, DateTimeEdit, DateEdit,
                            TextEdit, SearchLineEdit, PasswordLineEdit)

from .gallery_interface import GalleryInterface

from .net_info import NetInfoCard

import requests
import re
import json
from bs4 import BeautifulSoup
import subprocess
import yaml
import platform

from loguru import logger

class NetworkUpdateThread(QThread):
    """后台线程，用于更新网络信息"""
    update_signal = Signal(dict)  # 用信号发送网络信息到主线程

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def run(self):
        """在后台线程执行网络信息更新"""
        try:
                if self.parent.network_was_down:
                    logger.info(f"Network is down, skip fetching network data")
                    new_netinfo =  {
                                            "online_status": "Offline",
                                            "IP": "Unknown",
                                            "IPv6": "Unknown",
                                            "MAC": "Unknown",
                                            "interface": "Unknown",
                                            "DNS": "Unknown",
                                            "id": "Unknown",
                                            "device": []
                                        }
                else:
                    new_netinfo = self.fetchNetworkData()
                self.update_signal.emit(new_netinfo)
        except Exception as e:
            logger.error(f"Error fetching network data: {e}")
    
    def getDrcomUrl(self, type=None, id = None):
        if type == "id":
            return "https://xha.ouc.edu.cn"
        elif type == "devices":
            uid , _ = self.fetchUserID()
            return f"https://xha.ouc.edu.cn:802/eportal/portal/page/loadOnlineRecord?callback=dr1004&lang=zh-CN&program_index=ctshNw1713845951&page_index=V5fmKw1713845966&user_account={uid}&wlan_user_ip=0.0.0.0&wlan_user_mac=000000000000&start_time=2010-01-01&end_time=2100-01-01&start_rn=1&end_rn=5&jsVersion=4.1&v=3747&lang=zh"
        elif type == "bind":
            uid , _ = self.fetchUserID()
            return f"https://xha.ouc.edu.cn:802/eportal/portal/mac/custom?callback=dr1002&lang=zh-CN&program_index=ctshNw1713845951&page_index=V5fmKw1713845966&user_account={uid}&wlan_user_ip=0.0.0.0&wlan_user_mac=000000000000&jsVersion=4.1&v=8569&lang=zh"

    def fetchUserID(self):
        response = requests.get(self.getDrcomUrl("id"))

        if response.status_code == 200:
            # 使用 BeautifulSoup 解析 HTML 内容
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有的 <script> 标签
            scripts = soup.find_all('script')

            # 正则表达式用于提取 uid 和 v4ip
            uid_pattern = re.compile(r"uid='([^']+)'")
            v4ip_pattern = re.compile(r"v4ip='([^']+)'")

            # 从每个 <script> 中查找匹配的内容
            uid = None
            v4ip = None

            for script in scripts:
                # 搜索 uid 和 v4ip
                if not uid:
                    uid_match = uid_pattern.search(script.string if script.string else '')
                    if uid_match:
                        uid = uid_match.group(1)
                if not v4ip:
                    v4ip_match = v4ip_pattern.search(script.string if script.string else '')
                    if v4ip_match:
                        v4ip = v4ip_match.group(1)

                if uid and v4ip:
                    break
        return uid, v4ip

    def fetchDevices(self):
        response = requests.get(self.getDrcomUrl("devices"))
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            match = re.match(r"(dr\d+)(?=\()", soup.text)
            if match:
                cleaned_response = re.sub(r"^dr\d+\(|\);$", "", soup.text)
            else:
                print("未匹配到数据")

            json_data = json.loads(cleaned_response)
            records = json_data['records']
        return records
    
    def fetchIP(self):
        url = "http://ip.ouc.edu.cn"
        response = requests.get(url)

        if response.status_code == 200:
            # 使用 BeautifulSoup 解析 HTML 内容
            soup = BeautifulSoup(response.text, 'html.parser')
            ipv6_pattern = r'([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}'  # 匹配IPv6地址
            ipv4_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # 匹配IPv4地址
            
            # 查找IPv6和IPv4地址
            ipv6_match = re.search(ipv6_pattern, soup.text)
            ipv4_match = re.search(ipv4_pattern, soup.text)

            if ipv6_match:
                _ , ipv4 = self.fetchUserID()
                return ipv4, ipv6_match.group(1)  # 返回匹配的IPv6地址
            elif ipv4_match:
                return ipv4_match.group(1), None  # 返回匹配的IPv4地址
            else:
                return None, None    
            
    def get_network_info(self):
        if platform.system() == 'Darwin':
            result = subprocess.run(['system_profiler', 'SPNetworkDataType'], capture_output=True, text=True)
            result = yaml.safe_load(result.stdout)
            net_status = {}
            for type in result['Network'].keys():
                net_interface = result['Network'][type].get('BSD Device Name', 'Unknown')
                ipv4 = result['Network'][type].get('IPv4 Addresses', 'Unknown')
                ipv4_dns = result['Network'][type].get('DNS', {}).get('Server Addresses', '')
                ipv4_dns = [ip.strip() for ip in ipv4_dns.split(',')] if ipv4_dns else []
                ipv6 = result['Network'][type].get('IPv6', {}).get('Addresses', [])
                ipv6 = [ip.strip() for ip in ipv6.split(',')] if ipv6 else []
                mac = result['Network'][type].get('Ethernet', 'Unknown').get('MAC Address', 'Unknown')
                net_status[type] = {
                    'type': type,
                    'interface': net_interface,
                    'ipv4': ipv4,
                    'ipv4_dns': ipv4_dns,
                    'ipv6': ipv6,
                    'mac': mac
                }
        elif platform.system() == 'Windows':
            import psutil
            import socket
            
            # 获取网络接口地址
            net_if_addrs = psutil.net_if_addrs()
            
            # 获取网络接口状态
            net_if_stats = psutil.net_if_stats()
            
            def get_dns_info():
                try:
                    result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True)
                    infolists = result.stdout.splitlines()
                    validinfolist = []
                    for index, value in enumerate(infolists):
                        if '10.191.222.147' in value:
                            validinfolist = infolists[index: index+11]
                    pattern = re.compile(r'\d+.\d+.\d+.\d+')
                    match = 0
                    dnsserver = []
                    for info in validinfolist:
                        if 'DNS'in info:
                            dnsserver.append(re.findall(pattern, info)[0])
                            match = 1
                        if match:
                            dnsserver.append(re.findall(pattern, info)[0])
                            match = 0
                except:
                    dnsserver = []

                return dnsserver

            # 筛选以太网和WLAN接口并验证连接状态
            net_status = {}
            for interface, info in net_if_addrs.items():
                
                # 检查接口是否为以太网或WLAN
                if "以太网" in interface or "WLAN" in interface:
                    # 获取接口的网络状态
                    stats = net_if_stats.get(interface)
                    # 检查接口是否已连接
                    if stats and stats.isup:
                        
                        logger.info(f"{interface} is connected to the network.")
                        # 查找IPv4地址、IPv6地址、MAC地址
                        ipv4_address = None
                        ipv6_address = []
                        mac_address = None
                        
            
                        for addr in info:
                            if addr.family == socket.AddressFamily.AF_INET:
                                ipv4_address = addr.address
                            elif addr.family == socket.AddressFamily.AF_INET6:
                                # 排除链路本地地址和临时IPv6地址
                                if not addr.address.startswith("fe80::") and not addr.address.startswith("::"):
                                    ipv6_address.append(addr.address)
                            elif addr.family == psutil.AF_LINK:
                                mac_address = addr.address
                                
                        dns_info = get_dns_info()
                        
                        # 输出接口信息
                        if interface == "WLAN":interface = "Wi-Fi"
                        if interface == "以太网":interface = "Ethernet"
                        net_status[interface] = {
                            'type': interface,
                            'interface': interface,
                            'ipv4': ipv4_address if ipv4_address else 'Unknown',
                            'ipv4_dns': dns_info if dns_info else 'Unknown',
                            'ipv6': ipv6_address[0] if ipv6_address else 'Unknown',
                            'mac': mac_address if mac_address else 'Unknown'
                        }

        online_interface = []
        for net_type in net_status.keys():
            logger.debug(f"Checking network status for {net_type}, ipv4: {net_status[net_type]['ipv4']}")
            ipv4 = net_status[net_type]['ipv4']

            if ipv4 != 'Unknown':
                online_interface.append(net_type)

        return online_interface, net_status

    def fetchNetworkData(self):
        """模拟网络请求获取新数据"""
        
        # 验证网络通断
        # online_baidu, online_ouc, online_ouc_w = self.checkNetworkOnline()

        # if not online_baidu and not online_ouc and not online_ouc_w:
        #     logger.info(f"Network is offline")
        #     return {
        #         "online_status": "Offline",
        #         "IP": "Unknown",
        #         "IPv6": "Unknown",
        #         "MAC": "Unknown",
        #         "interface": "Unknown",
        #         "DNS": "Unknown",
        #         "id": "Unknown",
        #         "device": []
        #     }
        # elif online_baidu and online_ouc and online_ouc_w:
        #     logger.info(f"Network is online")
        # elif not online_baidu and online_ouc and online_ouc_w:
        #     logger.info(f"Network is offline but ouc is accessible, maybe need log in")

        logger.info(f"Fetching user data...")
        uid, uip = self.fetchUserID()
        logger.info(f"uid: {uid}, v4ip: {uip}")

        logger.info(f"Fetching network data...")
        ipv4, ipv6 = self.fetchIP()
        logger.info(f"IPv4: {ipv4}, IPv6: {ipv6}")

        logger.info(f"Fetching network status data...")
        online_interface, net_status = self.get_network_info()
        logger.debug(f"Online interface: {online_interface}, Net status: {net_status}")

        if len(online_interface) == 0:
            return {
                "online_status": "Offline",
                "IP": "Unknown",
                "IPv6": "Unknown",
                "MAC": [interface_info['mac'] for interface_info in net_status],
                "interface": [interface_info['interface'] for interface_info in net_status],
                "DNS": "Unknown",
                "id": "Unknown",
                "device": []
            }
        elif len(online_interface) == 1:
            if ipv4 is None:
                ipv4 = net_status[online_interface[0]]['ipv4']
            logger.debug(f"Final IPv4: {ipv4}")

            if ipv6 is None:
                ipv6 = net_status[online_interface[0]]['ipv6']
            logger.debug(f"Final IPv6: {ipv6}")
            
            mac = net_status[online_interface[0]]['mac']
            net_type = online_interface[0]
            dns = net_status[online_interface[0]]['ipv4_dns']

            return_res = {
                "online_status": "Online",
                "IP": ipv4,
                "IPv6": ipv6,
                "MAC": mac,
                "interface": net_type,
                "DNS": dns,
                "id": uid,
                "device": [
                    {
                        "name": "DESKTOP-AAAAAA",
                        "type": "PC",
                        "status": "Online",
                        "IP": "10.100.30.5"
                    },
                    {
                        "name": "DESKTOP-BBBBBB",
                        "type": "PC",
                        "status": "Offline",
                        "IP": "10.100.30.6"
                    },
                ]
            }
            logger.debug(f"Return data: {return_res}")
            return return_res

class NetworkOnline(QThread):

    network_status_signal = Signal(bool)  # 用信号发送网络是否正常的状态到主线程

    network_offline_signal = Signal(bool)

    network_change_signal = Signal(bool)  # 用信号发送网络状态变化到主线程

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.last_status = False

    def run(self):
        try:
            is_online = False
            online_baidu, online_ouc, online_ouc_w = self.checkNetworkOnline()
            if online_ouc and online_ouc_w:
                is_online = True
            else:
                is_online = False
                self.network_offline_signal.emit(is_online)

            self.network_status_signal.emit(is_online)
            if is_online != self.last_status:
                self.network_change_signal.emit(is_online)
                self.last_status = is_online
        except Exception as e:
            logger.error(f"Error check network status: {e}")
    
    def checkNetworkOnline(self):
        try:
            # ping baidu
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", "www.baidu.com"]  
            logger.info(f"Start ping Baidu")
            baidu_process  = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # ping ouc dns
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", "211.64.142.5"]
            logger.info(f"Start ping OUC")
            ouc_process  = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
            # ping ouc west
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", "192.168.101.201"]
            logger.info(f"Start ping OUC-W")
            ouc_w_process  = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            baidu_result = baidu_process.wait(timeout=5)
            ouc_result = ouc_process.wait(timeout=5)
            ouc_w_result = ouc_w_process.wait(timeout=5)

            if baidu_result == 0:
                online_baidu = True
            else:
                online_baidu = False
            logger.info(f"Finish ping Baidu: {online_baidu}")

            if ouc_result == 0:
                online_ouc = True
            else:
                online_ouc = False

            logger.info(f"Finish ping OUC: {online_ouc}")

            if ouc_w_result == 0:
                online_ouc_w = True
            else:
                online_ouc_w = False

            logger.info(f"Finish ping OUC-W: {online_ouc_w}")
        except Exception as e:
            logger.error(f"checkNetwork Failed: {e}")
            online_baidu = online_ouc = online_ouc_w = False
        return online_baidu, online_ouc, online_ouc_w



class OUCNet(GalleryInterface):

    def __init__(self, parent=None):
        super().__init__(
            title="OUC Net",
            subtitle="OUC校园网联网工具",
            parent=parent
        )

        self.setObjectName('OUCNet')

        self.netInfoCard = self.addNetInfoCard("网络状态")

        self.idManagerCard = self.addIDManagerCard("ID管理")
        self.update_uids()

        # 初始化uids信号
        self.idManagerCard.changed_uids.connect(self.update_uids)

        # 初始化网络更新线程
        self.threadUpdateNetInfo = NetworkUpdateThread(self)
        self.threadUpdateNetInfo.update_signal.connect(self.updateNetInfo)

        self.threadUpdateNetStatus = NetworkOnline(self)
        self.threadUpdateNetStatus.network_change_signal.connect(self.handleNetworkStatus)
        self.threadUpdateNetStatus.network_offline_signal.connect(self.startSignin)

        # 定时连接网络
        # self.signinTimer  = QTimer(self)
        # self.signinTimer.timeout.connect(self.startSignin)
        # self.signinTimer.start(5000) 

        # 定时更新网络通断
        self.netInfoUpdateTimer  = QTimer(self)
        self.netInfoUpdateTimer.timeout.connect(self.startNetworkUpdate)
        self.netInfoUpdateTimer.start(3000) 

        # 定时更新网络信息
        self.networkStatusCheckTimer  = QTimer(self)
        self.networkStatusCheckTimer.timeout.connect(self.startCheckNetworkOnline)
        self.networkStatusCheckTimer.start(5000)

        self.time_elapsed = 0
        self.network_was_down = False
        self.login_counts_limits = 5
    
    def update_uids(self, uids_dict: dict = None):
        try:
            if uids_dict is None:
                logger.info("uids is None")
                self.netInfoCard.updateuids(self.idManagerCard.load_data(return_data=True))
            else:
                logger.info("uids is changed, updating")
                self.netInfoCard.updateuids(uids_dict)
        except Exception as e:
            logger.error(f"Error updating uids: {e}")

    def startSignin(self):
        try:
            logger.info(f"Start sign in")
            self.netInfoCard.signinClicked()
        except Exception as e:
            logger.error(f"Auto sign in Failed: {e}")

    def startNetworkUpdate(self):
        """启动后台线程来更新网络信息"""

        logger.debug(f"Time elapsed: {self.time_elapsed}")

        if self.time_elapsed < 20:  # 前20秒每4秒更新一次
            self.threadUpdateNetInfo.start()
            self.time_elapsed += 5
        else:
            # 20秒过后，停止定时器并切换到网络检测模式
            logger.info(f"Switching to network status check mode")
    
    def startCheckNetworkOnline(self):
        """启动后台线程来检查网络通断"""
        self.threadUpdateNetStatus.start()

    def updateNetInfo(self, new_netinfo):
        """更新UI上的网络信息"""
        try:
            # 更新self.netinfo并刷新UI
            self.netInfoCard.update_info(new_netinfo)
        except Exception as e:
            logger.error(f"Error updating network info: {e}")
    
    def handleNetworkStatus(self, is_online):
        """根据网络状态决定是否继续更新"""

        logger.info(f"Network status changed: {is_online}")

        self.time_elapsed = 0  # 重置计时器
        self.networkStatusCheckTimer.start(5000) 

        if is_online:
            if self.network_was_down:
                self.network_was_down = False  # 标记网络已恢复
        else:
            self.signin()
            if not self.network_was_down:
                self.network_was_down = True




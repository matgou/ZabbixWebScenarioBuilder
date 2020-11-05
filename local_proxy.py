# -*- coding: utf-8 -*-
"""
local_proxy.py
~~~~~~~

This file references class to change proxy
"""
import logging
import winreg as winreg
import ctypes
import time


class WindowsProxy:
    """ This class can activate or unactive a proxy on windows """
    def set_key(self, name, value):
        _, reg_type = winreg.QueryValueEx(self.INTERNET_SETTINGS, name)
        winreg.SetValueEx(self.INTERNET_SETTINGS, name, 0, reg_type, value)

    def set_dword(self, name, value):
        winreg.SetValueEx(self.INTERNET_SETTINGS, name, 0, winreg.REG_SZ, value)

    def deleteKey(self, name):
        winreg.DeleteValue(self.INTERNET_SETTINGS, name)

    def activate_proxy(self):
        logging.debug('Activation du parametrage pour passer par le proxy')
        self.INTERNET_SETTINGS = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                                                0, winreg.KEY_ALL_ACCESS)
        self.set_key('ProxyEnable', 1)
        self.set_dword('ProxyServer', u'127.0.0.1:3128')
        winreg.CloseKey(self.INTERNET_SETTINGS)
        self.refreshWinCache()
        return

    def desactivate_proxy(self):
        logging.debug('Desactivation du parametrage pour passer par le proxy')
        self.INTERNET_SETTINGS = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                                                0, winreg.KEY_ALL_ACCESS)
        self.set_key('ProxyEnable', 0)
        self.deleteKey('ProxyServer')
        winreg.CloseKey(self.INTERNET_SETTINGS)
        time.sleep(1)
        self.refreshWinCache()
        return

    def refreshWinCache(self):
        INTERNET_OPTION_REFRESH = 37
        INTERNET_OPTION_SETTINGS_CHANGED = 39
        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        assert internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0), 'Erreur lors du refresh de cache internet'
        assert internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0),'Erreur lors du refresh de cache internet'


""" Main entrypoint """
if __name__ == '__main__':
    WindowsProxy().desactivate_proxy()

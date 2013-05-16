

# Tilde project: windows UI CEF loader
# tested with CEFPython v52 (CEF 1 branch 1364 rev. 1123)
# v130513

import os
import sys
import socket
import time
import platform
import traceback

sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../windows/cef/'))

if platform.architecture()[0] != "32bit": raise Exception("Only 32bit architecture is supported")

if sys.hexversion >= 0x02070000 and sys.hexversion < 0x03000000:
    import cefpython_py27 as cefpython
elif sys.hexversion >= 0x03000000 and sys.hexversion < 0x04000000:
    import cefpython_py32 as cefpython
else:
    raise Exception("Unsupported python version: %s" % sys.version)

import pywintypes
import cefwindow
import win32con
import win32gui

from settings import settings

reload_count = 0
ui_address = 'localhost'
conn_error = 'No answer from program core. Please, try to restart application.'

def ExceptHook(type, value, traceObject):
    error = "\n".join(traceback.format_exception(type, value, traceObject))
    cefpython.QuitMessageLoop()
    cefpython.Shutdown()
    raise Exception(error)

class ClientHandler:
    def OnLoadError(self, browser, frame, errorCode, failedURL, errorText):
        # this is to test whether the localhost is ready
        global reload_count
        reload_count += 1
        msg = '<b>' + conn_error + '</b>' if reload_count > 5 else '<html><meta http-equiv="refresh" content="1;url=http://' + ui_address + ":" + str( settings['webport'] ) + '"></html>'
        errorText[0] = (msg)
        return True

    def OnLoadEnd(self, browser, frame, httpStatusCode):
        if httpStatusCode == 200:
            global reload_count
            reload_count = 0
        return True

    def OnKeyEvent(self, browser, eventType, keyCode, modifiers, isSystemKey, isAfterJavascript):
        if eventType != cefpython.KEYEVENT_RAWKEYDOWN or isSystemKey:
            return False

        # Bind F5
        if keyCode == cefpython.VK_F5 and cefpython.IsKeyModifier(cefpython.KEY_NONE, modifiers):
            browser.ReloadIgnoreCache()
            return True

        return False

def CloseWindow(windowHandle, message, wparam, lparam):
    browser = cefpython.GetBrowserByWindowHandle(windowHandle)
    browser.CloseBrowser()
    return win32gui.DefWindowProc(windowHandle, message, wparam, lparam)

def QuitApplication(windowHandle, message, wparam, lparam):
    win32gui.PostQuitMessage(0)
    return 0

def CefInit(ui_address):
    sys.excepthook = ExceptHook
    ApplicationSettings={"graphics_implementation": 2}
    cefpython.Initialize(ApplicationSettings)
    wndproc = {
        win32con.WM_CLOSE: CloseWindow,
        win32con.WM_DESTROY: QuitApplication,
        win32con.WM_SIZE: cefpython.WindowUtils.OnSize,
        win32con.WM_SETFOCUS: cefpython.WindowUtils.OnSetFocus,
        win32con.WM_ERASEBKGND: cefpython.WindowUtils.OnEraseBackground }
    windowHandle = cefwindow.CreateWindow(title="tilde", className="tilde", width=1024, height=768, icon=os.path.realpath(os.path.dirname(__file__) + '/../htdocs/favicon.ico'), windowProc=wndproc)
    windowInfo = cefpython.WindowInfo()
    windowInfo.SetAsChild(windowHandle)
    browser = cefpython.CreateBrowserSync(windowInfo, browserSettings={}, navigateUrl=ui_address)
    browser.SetClientHandler(ClientHandler())
    cefpython.MessageLoop()
    cefpython.Shutdown()

if __name__ == "__main__":
    # this is to test whether the localhost is ready
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tries = 0
    while 1:
        tries += 1
        try:
            s.connect( (ui_address, settings['webport']) )
            s.shutdown(socket.SHUT_RDWR)
            break
        except:
            time.sleep(1)
        if tries > 20:
            s.close()
            raise Exception(conn_error)
    s.close()
    CefInit( "http://" + ui_address + ":" + str( settings['webport'] ) )

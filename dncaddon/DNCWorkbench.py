import os
import FreeCAD
import FreeCADGui

PACKAGE_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(PACKAGE_DIR, "resources", "dnc_icon.svg")
FALLBACK_ICON_PATH = os.path.join(PACKAGE_DIR, "dnc_icon.svg")

if not os.path.exists(ICON_PATH) and os.path.exists(FALLBACK_ICON_PATH):
    ICON_PATH = FALLBACK_ICON_PATH


class MainDNCCommand:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Open DNC Console",
            "ToolTip": "Open the DNC send/receive console with editor and machine profiles",
        }

    def Activated(self):
        try:
            import serial_dnc
        except Exception:
            from dncaddon import serial_dnc
        serial_dnc.run_dnc_console()

    def IsActive(self):
        return True


class DNCWorkbench(FreeCADGui.Workbench):
    MenuText = "DNC"
    ToolTip = "Send G-code to CNC machines"
    Icon = ICON_PATH

    def Initialize(self):
        FreeCADGui.addCommand("DNC_Main", MainDNCCommand())
        self.appendMenu("DNC", ["DNC_Main"])
        self.appendToolbar("DNC", ["DNC_Main"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"


def setupWorkbench():
    try:
        FreeCADGui.addWorkbench(DNCWorkbench())
    except Exception:
        pass

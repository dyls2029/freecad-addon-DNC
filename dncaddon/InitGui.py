import FreeCADGui

try:
    import DNCWorkbench
except Exception:
    from dncaddon import DNCWorkbench

try:
    FreeCADGui.addCommand("DNC_Main", DNCWorkbench.MainDNCCommand())
except Exception:
    pass

try:
    FreeCADGui.addWorkbench(DNCWorkbench.DNCWorkbench())
except Exception:
    pass

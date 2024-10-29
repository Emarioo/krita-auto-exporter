from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from pathlib import Path
import os
import datetime

exporter_crop_area = (0,0,-1,-1)

def get_plugin_location():
    abs_path = os.path.dirname(os.path.realpath(__file__))
    return abs_path

DATA_LOCATION = get_plugin_location() + "/user_data"
try:
    os.mkdir(DATA_LOCATION)
except:
    pass
EXPORT_SETTINGS_LOCATION = DATA_LOCATION + "/export_settings.txt"
LOG_LOCATION = DATA_LOCATION + "/log.txt"
KEYVALUE_DELIMITER = "\n"

DEFAULT_CROP_TEXT = "0 0 -1 -1"

global_docker = None

def log(msg):
    time = datetime.datetime.now()
    with open(LOG_LOCATION, "a") as file:
        file.write("["+str(time.hour)+":"+str(time.minute)+":"+str(time.second)+"] "+msg+"\n")

def set_data(key,value):
    key = key.strip()
    value = value.strip()
    # value cannot contain KEYVALUE_DELIMITER (newlines)

    content = ""
    try:
        with open(EXPORT_SETTINGS_LOCATION, "r") as file:
            content = file.read()
    except:
        # file not found
        pass
    
    lines = content.split(KEYVALUE_DELIMITER)
    content = ""
    found = False
    for i,v in enumerate(lines):
        if len(v) == 0:
            # we keep empty lines except for the last one
            if i != len(lines)-1:
                content += v + KEYVALUE_DELIMITER
            continue
        if v[0] == "#":
            # just append comment
            content += v + KEYVALUE_DELIMITER
            continue
        
        pair = v.split("=")
        if pair[0] == key:
            found = True
            content += key + "=" + value + KEYVALUE_DELIMITER
        else:
            content += pair[0] + "=" + pair[1] + KEYVALUE_DELIMITER
    
    if not found:
        content += key + "=" + value + KEYVALUE_DELIMITER
    
    with open(EXPORT_SETTINGS_LOCATION, "w") as file:
        file.write(content)

# return None if there is not data
def get_data(key):
    key = key.strip()
    
    content = ""
    try:
        with open(EXPORT_SETTINGS_LOCATION, "r") as file:
            content = file.read()
    except:
        # file not found
        return None
    
    lines = content.split(KEYVALUE_DELIMITER)
    for i,v in enumerate(lines):
        if len(v) == 0:
            continue
        if v[0] == "#":
            continue
        
        pair = v.split("=")
        if pair[0] == key:
            return pair[1]
    return None

# returns (x,y,w,h)
# returns None on bad format
def parse_crop_area(string):
    nums = string.strip().split(" ")
    if len(nums) != 4:
        return None
    try:
        for i in range(4):
            nums[i] = int(nums[i])
    except:
        return None
    
    return (nums[0],nums[1],nums[2],nums[3])

class AutoExporter(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.app_notifier = None
        self.win = None
        self.current_document = None
        
    def setup(self):
        pass
    
    def debug_message(self, msg):
        messageBox = QMessageBox()
        messageBox.setWindowTitle('Auto Exporter')
        messageBox.setText(msg);
        messageBox.setStandardButtons(QMessageBox.Close)
        messageBox.setIcon(QMessageBox.Information)
        messageBox.exec()
    
    def show_message(self, msg):
        window = Krita.instance().activeWindow()
        if window is None:
            return
        view = window.activeView()
        if view is None:
            return
        view.showFloatingMessage(msg, QIcon(), 2000, 1)
    
    def export_image(self, filename):
        doc = Krita.instance().activeDocument()
        is_export_enabled = get_data("export_enabled."+doc.name())
        if is_export_enabled is None or not bool(is_export_enabled):
            # not active
            return
        
        
        # don't export autosave (works in version 5.2.6)
        at = filename.rfind("-autosave.kra")
        if at != -1:
            return
        
        # replace extension from .kra to .png
        at = filename.rfind(".")
        if at == -1:
            self.show_message("Couldn't find file extension ('.') in '" + filename+"'")
            return
        export_path = filename[0:at+1] + "png"
        
        # TODO: set visibilty for layers that should be visible (set through auto exporter docker)
        # for node in doc.topLevelNodes():
            
        crop_area = (0,0,-1,-1)
        crop_text = get_data("crop_area."+doc.name())
        if crop_text is not None:
            crop = parse_crop_area(crop_text)
            if crop is None:
                self.show_message(f"Crop area has bad format '{crop_text}'")
                return
            crop_area = crop
        
        # Crop image to specified crop area
        prev_area = (-crop_area[0], -crop_area[1], doc.width(), doc.height())
        w = crop_area[2]
        if w < 0:
            w = doc.width()
        h = crop_area[3]
        if h < 0:
            h = doc.height()
        doc.resizeImage(crop_area[0],crop_area[1],w,h)
        
        # Export image
        config = InfoObject()
        config.setProperty("alpha", True)
        config.setProperty("compression", 5)
        config.setProperty("indexed", True)
        config.setProperty("interlaced", True)
        config.setProperty("saveSRGBProfile", False)
        config.setProperty("transparencyFIllcolor", [255,255,255])
        doc.setBatchmode(True)
        yes = doc.exportImage(export_path, config)
        doc.setBatchmode(False)
        
        # Undo crop area
        doc.resizeImage(prev_area[0],prev_area[1],prev_area[2],prev_area[3])
        
        # self.show_message(f"Prev area: {prev_area[0]} {prev_area[1]} {prev_area[2]} {prev_area[3]}, Crop area: {exporter_crop_area[0]} {exporter_crop_area[1]} {w} {h}")
        
        # TODO: Undo layer visibility
        
        if not yes:
            self.show_message("Couldn't export '" + export_path + "'")
            return
        
        self.show_message("Exporting " + export_path)
    
    def on_view_changed(self):
        doc = Krita.instance().activeDocument()
        if doc is None:
            log("view changed, no doc")
        else:
            log("view changed, " + doc.name())
        
        if doc == self.current_document:
            return
        
        self.show_message("Swap doc " + doc.name())
        
        if global_docker:
            global_docker.refresh_ui(doc)
        self.current_document = doc
        
    def on_window_created(self):
        # how to deal with multiple windows?
        self.win = Krita.instance().activeWindow()
        self.win.activeViewChanged.connect(self.on_view_changed)
        
        doc = Krita.instance().activeDocument()
        if doc is None:
            log("Created window, no doc")
        else:
            log("Created window, " + doc.name())
    
    def on_view_created(self):
        # win = Krita.instance().activeWindow()
        # win.activeViewChanged.connect(self.on_view_changed)
        
        doc = Krita.instance().activeDocument()
        if doc is None:
            log("Created view, no doc")
        else:
            log("Created view, " + doc.name())

    def createActions(self, window):
        self.app_notifier = Krita.instance().notifier()
        self.app_notifier.setActive(True)
        self.app_notifier.imageSaved.connect(self.export_image)
        self.app_notifier.windowCreated.connect(self.on_window_created)
        self.app_notifier.viewCreated.connect(self.on_view_created)
        
        # actwin = Krita.instance().activeWindow()
        # actwin.activeViewChanged.connect(self.on_view_changed)

class AutoExporterDocker(DockWidget):
    def __init__(self):
        super().__init__()
        global global_docker
        global_docker = self
        self.setWindowTitle("Auto Exporter")
        self.mainWidget = QWidget(self)
        self.mainWidget.setLayout(QVBoxLayout()) #  QHBoxLayout
        self.setWidget(self.mainWidget)
        
        # buttonExportDocument = QPushButton("Export Document", mainWidget)
        # mainWidget.layout().addWidget(buttonExportDocument)
        # buttonExportDocument.clicked.connect(self.exportDocument)
        
        self.enable_checkbox = QCheckBox("Export on save", self.mainWidget)
        self.enable_checkbox.toggled.connect(self.on_export_toggled)
        self.layout().addWidget(self.enable_checkbox)
        
        # home = Path.home()
        # log_textbox = QLineEdit(mainWidget)
        # log_textbox.setText(home+"export_log.txt")
        # mainWidget.layout().addWidget(log_textbox)
        
        crop_label = QLabel("Crop area", self.mainWidget)
        self.mainWidget.layout().addWidget(crop_label)
            
        self.crop_textbox = QLineEdit("0 0 -1 -1", self.mainWidget)
        self.crop_textbox.textChanged.connect(self.on_crop_changed)
        self.mainWidget.layout().addWidget(self.crop_textbox)
        
    def refresh_ui(self, doc):
        crop_text = get_data("crop_area."+doc.name())
        export_enabled = get_data("export_enabled."+doc.name())
        
        crop_text = crop_text if crop_text is not None else DEFAULT_CROP_TEXT
        export_enable = export_enabled is not None and bool(export_enabled)
        
        self.enable_checkbox.setChecked(export_enable)
        self.crop_textbox.setText(crop_text)
    
    def on_crop_changed(self, text):
        doc = Krita.instance().activeDocument()
        self.show_message("New crop: " + text)
        crop_area = parse_crop_area(text)
        if crop_area is None:
            self.show_message("Crop format in Auto Exporter should look like this: '0 0 64 64' not '" + text + "'")
        else:
            set_data("crop_area."+doc.name(), text)
        
    def show_message(self, msg):
        window = Krita.instance().activeWindow()
        if window is None:
            return
        view = window.activeView()
        if view is None:
            return
        view.showFloatingMessage(msg, QIcon(), 3000, 1)
    
    def on_export_toggled(self, enabled):
        doc = Krita.instance().activeDocument()
        # TODO: Make sure name doesn't contain \n or =
        set_data("export_enabled."+doc.name(), str(enabled))
        self.show_message("Export on save: " + str(enabled))
    

    def canvasChanged(self, canvas):
        pass


Krita.instance().addDockWidgetFactory(DockWidgetFactory("auto_exporter_docker", DockWidgetFactoryBase.DockRight, AutoExporterDocker))
        
Krita.instance().addExtension(AutoExporter(Krita.instance()))
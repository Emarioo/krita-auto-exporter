'''
Hello Python developer!

I keep all code in one file because it's super easy to navigate.
'''

from krita import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from pathlib import Path
import re
import os
import datetime

DATA_LOCATION = os.path.dirname(os.path.realpath(__file__)) + "/user_data"
EXPORT_SETTINGS_LOCATION = DATA_LOCATION + "/export_settings.txt"
LOG_LOCATION = DATA_LOCATION + "/log.txt"
KEYVALUE_DELIMITER = "\n"
DEFAULT_CROP_TEXT = "0 0 -1 -1"
try:
    os.mkdir(DATA_LOCATION)
except:
    pass

###############################
#   MAIN AUTO EXPORTER CODE   #
###############################

class AutoExporter(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.app_notifier = None
        self.win = None
        self.current_document = None
        self.disable = False
        self.timed_objects = []
        
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
        if self.disable:
            return
        
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
            show_message("Couldn't find file extension ('.') in '" + filename+"'")
            return
        export_path = filename[0:at+1] + "png"
        
            
        crop_area = (0,0,-1,-1)
        crop_text = get_data("crop_area."+doc.name())
        if crop_text is not None:
            crop = parse_crop_area(crop_text)
            if crop is None:
                show_message(f"Crop area has bad format '{crop_text}'")
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
            
        did_resize = False
        if crop_area[0] != 0 or crop_area[1] != 0 or w != doc.width() or h != doc.height():
            doc.resizeImage(crop_area[0],crop_area[1],w,h)
            did_resize = True
        
        # Change visibilty of layers
        layer_regex = get_data("layer_regex."+doc.name())
        layer_regex = layer_regex[1:-1] if layer_regex is not None else ""
        changed_nodes = []
        if len(layer_regex) != 0:
            pattern = re.compile(layer_regex)
            check_nodes = doc.topLevelNodes()
            while len(check_nodes) > 0:
                node = check_nodes.pop()
                check_nodes += node.childNodes()
                
                result = pattern.match(node.name())
                show = result is not None
                if node.visible() != show:
                    changed_nodes.append(node)
                    node.setVisible(show)
                # if show:
                #     log("SHOW " + node.name())
                # else:
                #     log("hide " + node.name())
        
        if len(changed_nodes) > 0:
            # Not refreshing makes us export without the layer visibility changes.
            doc.refreshProjection()
        
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
        if did_resize:
            doc.resizeImage(prev_area[0],prev_area[1],prev_area[2],prev_area[3])
        
        if len(changed_nodes) > 0:
            # log("undo layer visibility")
            for node in changed_nodes:
                node.setVisible(not node.visible())
            # Refresh because the canvas isn't rendered properly otherwise
            doc.refreshProjection()
        
        if not yes:
            show_message("Couldn't export '" + export_path + "'")
            return
        
        show_message("Exported " + export_path)
        
        # We want to save again because we resized the image which changed the document.
        # Auto exporting on save and resizing the image would result in a document that
        # can never be fully saved. You would have to undo the two resizes from undo history
        # or close Krita with unsaved changes (which is fine, document is saved just not the two resize actions by the export plugin)
        # Ideally we would have access to an undo command in Krita Python API but we
        # do not as far as I know.
        
        # Yup, this code is scuffed.
        # We can't call doc.save() directly in this function because Krita crashes.
        # Not sure why, some recursive business maybe or ownership/lock problems?
        # We can delay the save using QTimer. This helped me figure out that QTimer is a thing: https://github.com/silentorb/krita_auto_export/blob/master/plugins/autoexport/autoexport.py
        class TimeObj():
            def __init__(self, doc, docker):
                self.doc = doc
                self.docker = docker
                
            def tick(self):
                self.docker.disable = True # prevent infinite save/export loop
                self.doc.save()
                self.docker.disable = False
                self.docker.timed_objects.remove(self)
        
        obj = TimeObj(doc, self)
        self.timed_objects.append(obj) # we need to save timed_objects, garbage collector will delete it otherwise
        # We set 'msec' argument to singleShot to zero because we might as well save
        # as soon as possible. QTimer will execute once we have finished the current save (i am guessing our export_image function is called inside the doc.save function)
        QTimer.singleShot(0, obj.tick)
        
    def on_view_created(self):
        self.win = Krita.instance().activeWindow()
        self.win.activeViewChanged.connect(self.on_view_changed)
        
        # doc = Krita.instance().activeDocument()
        # if doc is None:
        #     log("Created view, no doc")
        # else:
        #     log("Created view, " + doc.name())

    def createActions(self, window):
        self.app_notifier = Krita.instance().notifier()
        self.app_notifier.setActive(True)
        self.app_notifier.imageSaved.connect(self.export_image)
        
        # Window has not been loaded yet and the window argument is
        # the wrong window.
        # self.win = Krita.instance().activeWindow()
        # self.win.activeViewChanged.connect(self.on_view_changed)

class AutoExporterDocker(DockWidget):
    def __init__(self):
        super().__init__()
        global global_docker
        global_docker = self
        
        self.setWindowTitle("Auto Exporter")
        mainWidget = QWidget()
        self.setWidget(mainWidget)
        
        v_layout = QVBoxLayout()
        mainWidget.setLayout(v_layout)
        v_layout.setContentsMargins(0,10,0,0)
        # v_layout.setSpacing(10)
            
        self.enable_checkbox = QCheckBox("Export on save")
        self.enable_checkbox.toggled.connect(self.on_export_toggled)
        v_layout.addWidget(self.enable_checkbox)
        
        h_layout = QHBoxLayout()
        v_layout.addLayout(h_layout)
        
        crop_label = QLabel("Crop area:")
        h_layout.addWidget(crop_label)
        
        self.crop_x = QSpinBox()
        self.crop_y = QSpinBox()
        self.crop_w = QSpinBox()
        self.crop_h = QSpinBox()
        max_value = 9999 # TODO: We should increase the limit, the reason I don't is because the docker minimum width of the docker becomes bigger since the QSpinBoxes takes up more space.
        self.crop_x.setRange(-max_value,max_value)
        self.crop_y.setRange(-max_value,max_value)
        self.crop_w.setRange(-1,max_value)
        self.crop_h.setRange(-1,max_value)
        self.crop_w.setValue(-1)
        self.crop_h.setValue(-1)
        self.crop_x.valueChanged.connect(self.on_crop_changed)
        self.crop_y.valueChanged.connect(self.on_crop_changed)
        self.crop_w.valueChanged.connect(self.on_crop_changed)
        self.crop_h.valueChanged.connect(self.on_crop_changed)
        h_layout.addWidget(self.crop_x)
        h_layout.addWidget(self.crop_y)
        h_layout.addWidget(self.crop_w)
        h_layout.addWidget(self.crop_h)
    
        h_layout = QHBoxLayout()
        v_layout.addLayout(h_layout)
        
        layer_regex_label = QLabel("Layer regex:")
        h_layout.addWidget(layer_regex_label)
        
        self.layer_regex = QLineEdit()
        self.layer_regex.setPlaceholderText("python regex")
        self.layer_regex.textChanged.connect(self.on_layer_regex_changed)
        h_layout.addWidget(self.layer_regex)
        
        v_layout.addStretch()
        
        self.app_notifier = Krita.instance().notifier()
        self.app_notifier.viewCreated.connect(self.on_view_created)
        self.current_document = None
        self.some_windows = []
        
    def refresh_ui(self, doc):
        export_enabled = get_data("export_enabled."+doc.name())
        crop_text = get_data("crop_area."+doc.name())
        layer_regex = get_data("layer_regex."+doc.name())
        
        export_enable = export_enabled is not None and bool(export_enabled)
        crop_text = crop_text if crop_text is not None else DEFAULT_CROP_TEXT
        layer_regex = layer_regex[1:-1] if layer_regex is not None else ""
        # layer_regex[1:-1] because we store regex with quotes to prevent stripping of whitespace
        
        crop_area = parse_crop_area(crop_text)
        if crop_area is None:
            crop_area = DEFAULT_CROP_TEXT
        
        self.enable_checkbox.setChecked(export_enable)
        self.crop_x.setValue(crop_area[0])
        self.crop_y.setValue(crop_area[1])
        self.crop_w.setValue(crop_area[2])
        self.crop_h.setValue(crop_area[3])
        self.layer_regex.setText(layer_regex)
    
    def on_view_changed(self):
        # Whenever we change view we need to check if we switched to a
        # different document, if so we must update the docker UI to 
        # reflect the crop and regex settings for the current document
        doc = Krita.instance().activeDocument()
        # if doc is None:
        #     log("view changed, no doc")
        # else:
        #     log("view changed, " + doc.name())
        
        if doc == self.current_document:
            return
        
        # show_message("Swap doc " + doc.name())
        
        self.refresh_ui(doc)
        self.current_document = doc
    
    def on_view_created(self):
        # To detect a view change we need the active window which
        # I don't know how to get in a good way. If we created a view
        # then we certainly have a window.
        # need to store windows because Python garbage collector will
        # delete the Window and the connection that window.
        # We need the connection to detect when the user switches the document.
        win = Krita.instance().activeWindow()
        if win not in self.some_windows:
            self.some_windows.append(win)
            win.activeViewChanged.connect(self.on_view_changed)
        
        # doc = Krita.instance().activeDocument()
        # if doc is None:
        #     log("Created view, no doc")
        # else:
        #     log("Created view, " + doc.name())
        
    def on_crop_changed(self, value):
        doc = Krita.instance().activeDocument()
        text = str(self.crop_x.value()) + " " + str(self.crop_y.value()) + " " + str(self.crop_w.value()) + " " + str(self.crop_h.value())
        # show_message("New crop: " + text)
        crop_area = parse_crop_area(text)
        if crop_area is None:
            show_message("Crop format in Auto Exporter should look like this: '0 0 64 64' not '" + text + "'")
        else:
            set_data("crop_area."+doc.name(), text)

    def on_layer_regex_changed(self, text):
        doc = Krita.instance().activeDocument()
        # show_message("New regex: " + text)
        set_data("layer_regex."+doc.name(), "'"+text+"'") # insert quotes because set_data will strip whitespace at the string's beginning at end otherwise
    
    def on_export_toggled(self, enabled):
        doc = Krita.instance().activeDocument()
        # TODO: Make sure name doesn't contain \n or =
        set_data("export_enabled."+doc.name(), str(enabled))
        # show_message("Export on save: " + str(enabled))
        
    
    def canvasChanged(self, canvas):
        pass

#########################
#   UTILITY FUNCTIONS   #
#########################

def log(msg):
    time = datetime.datetime.now()
    with open(LOG_LOCATION, "a") as file:
        file.write("["+str(time.hour)+":"+str(time.minute)+":"+str(time.second)+"] "+msg+"\n")

def show_message(msg):
    window = Krita.instance().activeWindow()
    if window is None:
        return
    view = window.activeView()
    if view is None:
        return
    view.showFloatingMessage(msg, QIcon(), 3000, 1)
    
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

######################
#   INITIALIZATION   #
######################
Krita.instance().addDockWidgetFactory(DockWidgetFactory("auto_exporter_docker", DockWidgetFactoryBase.DockRight, AutoExporterDocker))
Krita.instance().addExtension(AutoExporter(Krita.instance()))
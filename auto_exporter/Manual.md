# Auto exporter v1.0
Automatically exports .png files when a document is saved. The exported file will end up in the same directory as the document.

More information can be found here:
https://github.com/Emarioo/krita-auto-exporter

## Features
- Auto export .png file when document is saved. (ignores autosaves)
- A docker for controlling if and how the document is exported
- Ability to enable auto-export on a per document basis. Exporting is disabled on all documents by default.
- Ability to crop the exported image (full image by default)
- Ability to choose which layers to make visible and hidden before exporting. This is done using Python regex on the layers' names.

## Cropping an image
The number boxes beside the crop area label begin with X and Y offset and then the last two are for width and height. -1 means the current width/height.

## Layer regex
The regex on layers' names uses the Python `re` module. Empty text will do nothing, layers that are hidden and visible will remain as they are.

Here are some examples of regex.
- `Background` will match layers with names `Background`, `Background 1`, and `Backgroundhello` but not `Backgund`.
- `top mask$` will match layers which has the exact name `top mask` while `stop mask` and `top mask 5` will not match.
- `.*show$` will match layers that end with `show`.
- `(?!.*hide).*` will match all names that **DO NOT** contain `hide`.

## Minor inconveniences
When you save and the auto exporter resizes the image it will be registered in
the undo history. The Krita Python API doesn't have access to undo actions so you will have to deal with undo history littered with two resize image everytime you save an auto-exported document. Let me know if you have any ideas on how to solve it.
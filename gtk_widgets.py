__author__ = 'edz'
import pygtk
import gtk
import cairo

class button_gtk(object):

    def __init__(self,label, functionCall, width = 0, spacing = 10, sensitivity = True):
        self.button = gtk.HButtonBox()
        self.button.set_border_width(width)
        self.button.set_spacing(spacing)
        self.button.set_layout(gtk.BUTTONBOX_END)

        self.button.buttonProp = gtk.Button(label)
        self.button.buttonProp.connect("clicked",functionCall)
        self.button.buttonProp.set_sensitive(sensitivity)
        self.button.add(self.button.buttonProp)

    def get(self):
        return self.button




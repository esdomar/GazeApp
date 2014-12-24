#!/usr/bin/python
import sys
sys.path.append('C:\\SDK\\Python27\\Modules')
sys.path.append('C:\\gtk\\bin')
sys.path.append('C:\\Python27\\modules')
sys.path.append('C:\\Python27\\Lib\\site-packages')

import pygtk
from tobii.eye_tracking_io.basic import EyetrackerException
pygtk.require('2.0')
import gtk
import time
import math
#import cv2
from gtk_widgets import *
glib_idle_add = None
glib_timeout_add = None
try:
    import glib
    glib_idle_add = glib.idle_add
    glib_timeout_add = glib.timeout_add
except:
    glib_idle_add = gtk.idle_add
    glib_timeout_add = gtk.timeout_add


import os
import math
import tobii.eye_tracking_io.mainloop
import tobii.eye_tracking_io.browsing
import tobii.eye_tracking_io.eyetracker

from tobii.eye_tracking_io.types import Point2D, Blob

class Eye_tracker:
    def __init__(self, max_age = 1000):
        self.eyetracker = None
        self.eyetrackers = {}
        self.liststore = gtk.ListStore(str, str, str)
        self.max_age = max_age
        #TODO
        #Make sure that no samples are getting lost --> Create a list in gaze_temp
        self.gazedata_temp = None
        self.gaze_data = []

        # Setup Eyetracker stuff
        tobii.eye_tracking_io.init()
        self.mainloop_thread = tobii.eye_tracking_io.mainloop.MainloopThread()
        self.browser = tobii.eye_tracking_io.browsing.EyetrackerBrowser(self.mainloop_thread, lambda t, n, i: glib_idle_add(self.on_eyetracker_browser_event, t, n, i))

    def mod_parameters(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(5)
        self.window.set_title("Eye tracker connection")

        #packing
        self.box_main = gtk.VBox(True,10)

        self.treeview = gtk.TreeView(self.liststore)
        self.treeview.connect("row-activated", self.row_activated)

        self.pid_column = gtk.TreeViewColumn("PID")
        self.pid_cell = gtk.CellRendererText()
        self.treeview.append_column(self.pid_column)
        self.pid_column.pack_start(self.pid_cell, True)
        self.pid_column.set_attributes(self.pid_cell, text=0)

        self.model_column = gtk.TreeViewColumn("Model")
        self.model_cell = gtk.CellRendererText()
        self.treeview.append_column(self.model_column)
        self.model_column.pack_start(self.model_cell, True)
        self.model_column.set_attributes(self.model_cell, text=1)

        self.status_column = gtk.TreeViewColumn("Status")
        self.status_cell = gtk.CellRendererText()
        self.treeview.append_column(self.status_column)
        self.status_column.pack_start(self.status_cell, True)
        self.status_column.set_attributes(self.status_cell, text=2)

        self.treeview_label = gtk.Label()
        self.treeview_label.set_alignment(0.0, 0.5)
        self.treeview_label.set_markup("<b>Discovered Eyetrackers:</b>")

        self.eyetracker_label = gtk.Label()
        self.eyetracker_label.set_markup("<b>No eyetracker selected.</b>")
        self.eyetracker_label.set_alignment(0.0, 0.5)

        self.box_main.pack_start(self.treeview_label,False,False,0)
        self.box_main.pack_start(self.treeview,False,False,0)
        self.box_main.pack_start(self.eyetracker_label,False,False,0)

        self.window.add(self.box_main)

        self.window.show_all()

    def row_activated(self, treeview, path, user_data=None):
        # When an eyetracker is selected in the browser list we create a new
        # eyetracker object and set it as the active one
        model = treeview.get_model()
        iter = model.get_iter(path)
        self.eyetracker_info = self.eyetrackers[model.get_value(iter, 0)]
        print "Connecting to:", self.eyetracker_info
        tobii.eye_tracking_io.eyetracker.Eyetracker.create_async(self.mainloop_thread,
                                                     self.eyetracker_info,
                                                     lambda error, eyetracker: glib_idle_add(self.on_eyetracker_created, error, eyetracker))

    def set_eyetracker(self, eyetracker):
        if self.eyetracker is not None:
            self.eyetracker.StopTracking()
            self.eyetracker.events.OnGazeDataReceived -= self.on_gazedata

        self.eyetracker = eyetracker
        self.gazedata_temp = None
        self.framerate = self.eyetracker.GetFramerate()
        if self.eyetracker is not None:
            self.eyetracker.events.OnGazeDataReceived += self.on_gazedata
            self.eyetracker.StartTracking()

    def get_framerate(self):
        return self.framerate

    def get_eyetracker(self):
        return self.eyetracker

    def on_gazedata(self, error, gaze):

        gazedata_copy = { 'left': { 'validity':     gaze.LeftValidity,
                                    'camera_pos':   gaze.LeftEyePosition3DRelative,
                                    'part_pos':     gaze.LeftEyePosition3D,
                                    'screen_pos':   gaze.LeftGazePoint2D},
                          'right': { 'validity':    gaze.RightValidity,
                                     'camera_pos':  gaze.RightEyePosition3DRelative,
                                     'part_pos':     gaze.LeftEyePosition3D,
                                     'screen_pos':  gaze.RightGazePoint2D}}

        try:
            self.handle_gazedata(gazedata_copy)
        except Exception, ex:
            print "  Exception occured: %s" %(ex)



    def handle_gazedata(self, gazedata):
        self.gazedata_temp = gazedata
        self.gaze_data.append(self.gazedata_temp)
        if len(self.gaze_data) > self.max_age:
            self.gaze_data.pop(0)

    def get_data(self,samples):
       try:
            return self.gaze_data[-samples:]
       except:
           return self.gaze_data

    def on_eyetracker_created(self, error, eyetracker):
        if error:
            print "  Connection to %s failed because of an exception: %s" % (self.eyetracker_info, error)
            if error == 0x20000402:
                show_message_box(parent=self.window, message="The selected unit is too old, a unit which supports protocol version 1.0 is required.\n\n<b>Details:</b> <i>%s</i>" % error)
            else:
                show_message_box(parent=self.window, message="Could not connect to %s" % (self.eyetracker_info))
            return False

        self.eyetracker = eyetracker

        try:
            self.set_eyetracker(self.eyetracker)
            self.eyetracker_label.set_markup("<b>Connected to Eyetracker: %s</b>. <b>Frame rate: %d Hz</b>"  % (self.eyetracker_info, self.framerate) )
            print "   --- Connected!"
        except Exception, ex:
            print "  Exception occured: %s" %(ex)
            show_message_box(parent=self.window, message="An error occured during initialization of track status or fetching of calibration plot: %s" % (ex))
        return False

    def on_eyetracker_upgraded(self, error, protocol):
        try:
            self.set_eyetracker(self.eyetracker)
            self.eyetracker_label.set_markup("<b>Connected to Eyetracker: %s</b>. Frame rate: " + str(self.framerate) + " Hz" % (self.eyetracker_info))
            print "   --- Connected!"
        except Exception, ex:
            print "  Exception occured: %s" %(ex)
            show_message_box(parent=self.window, message="An error occured during initialization of track status or fetching of calibration plot: %s" % (ex))
        return False

    def on_eyetracker_browser_event(self, event_type, event_name, ei):
        # When a new eyetracker is found we add it to the treeview and to the
        # internal list of eyetracker_info objects
        if event_type == tobii.eye_tracking_io.browsing.EyetrackerBrowser.FOUND:
            self.eyetrackers[ei.product_id] = ei
            self.liststore.append(('%s' % ei.product_id, ei.model, ei.status))
            return False

        # Otherwise we remove the tracker from the treeview and the eyetracker_info list...
        del self.eyetrackers[ei.product_id]
        iter = self.liststore.get_iter_first()
        while iter is not None:
            if self.liststore.get_value(iter, 0) == str(ei.product_id):
                self.liststore.remove(iter)
                break
            iter = self.liststore.iter_next(iter)

        # ...and add it again if it is an update message
        if event_type == tobii.eye_tracking_io.browsing.EyetrackerBrowser.UPDATED:
            self.eyetrackers[ei.product_id] = ei
            self.liststore.append([ei.product_id, ei.model, ei.status])
        return False

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        self.window.destroy()

    def disconnect_et(self):
        self.browser.stop()
        self.browser = None
        self.mainloop_thread.stop() #Stops the instance of the eye tracker thread

class CalibPlot(gtk.DrawingArea):
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(300, 300)
        self.connect("expose_event", self.on_expose)
        self.calib = None

    def set_eyetracker(self, eyetracker):
        if eyetracker is None:
            return

        try:
            self.calib = eyetracker.GetCalibration(lambda error, calib: glib_idle_add(self.on_calib_response, error, calib))
        except Exception, ex:
            print "  Exception occured: %s" %(ex)
            self.calib = None
        self.redraw()

    def on_calib_response(self, error, calib):
        if error:
            print "on_calib_response: Error"
            self.calib = None
            self.redraw()
            return False

        self.calib = calib
        self.redraw()
        return False

    def redraw(self):
        if self.window:
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    def on_expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()

        rect = widget.get_allocation()
        context.scale(rect.width, rect.height)

        self.draw(context)

    def draw(self, ctx):
        ctx.rectangle(0, 0, 1, 1)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()

        if self.calib is None:
            ctx.move_to(0, 0)
            ctx.line_to(1, 1)
            ctx.move_to(0, 1)
            ctx.line_to(1, 0)
            ctx.set_source_rgb(0, 0, 0)
            ctx.set_line_width(0.001)
            ctx.stroke()
            return

        points = {}
        for data in self.calib.plot_data:
            points[data.true_point] = { 'left': data.left, 'right': data.right }

        if len(points) == 0:
            ctx.move_to(0, 0)
            ctx.line_to(1, 1)
            ctx.move_to(0, 1)
            ctx.line_to(1, 0)
            ctx.set_source_rgb(0, 0, 0)
            ctx.set_line_width(0.001)
            ctx.stroke()
            return

        for p, d in points.iteritems():
            ctx.set_line_width(0.001)
            if d['left'].status == 1:
                ctx.set_source_rgb(1.0, 0., 0.)
                ctx.move_to(p.x, p.y)
                ctx.line_to(d['left'].map_point.x, d['left'].map_point.y)
                ctx.stroke()

            if d['right'].status == 1:
                ctx.set_source_rgb(0., 1.0, 0.)
                ctx.move_to(p.x, p.y)
                ctx.line_to(d['right'].map_point.x, d['right'].map_point.y)
                ctx.stroke()

            ctx.set_line_width(0.005)
            ctx.set_source_rgba(0., 0., 0., 0.05)
            ctx.arc(p.x, p.y, 0.01, 0, 2 * math.pi)
            ctx.stroke ()
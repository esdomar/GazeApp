
import sys
import pygtk
from tobii.eye_tracking_io.basic import EyetrackerException
pygtk.require('2.0')
import gtk
import gtk_widgets
import time
#import cv2
import eye_tracker as et
import numpy as np
import pango
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
#from matplotlib.figure import Figure

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
import socket
socket.setdefaulttimeout(0.5)

class GazeContingency:
    def __init__(self, monitor_resolution, center, AOI_size, monitor_size_mm, fixation_length, min_gazepoints_in, distance_screen):

        self.hit_start = 0
        self.validity = 0
        self.gaze_point_x = 0
        self.gaze_point_y = 0
        self.min_gazepoints_in = min_gazepoints_in
        self.monitor_resolution_px = monitor_resolution #width, height
        self.monitor_resolution_mm = monitor_size_mm #Width - Height
        self.fixation_length = fixation_length
        self.set_AOI_coordinates(center, AOI_size, distance_screen)

    def set_AOI_coordinates(self, center, AOI_size, distance_screen):
        self.center = [center[0], center[1]]
        self.AOI_size_degrees = AOI_size
        self.distance_screen_mm = distance_screen
        #self.calculate_AOI_coordinates()

    def calculate_AOI_coordinates(self):

        self.AOI_size_mm = self.distance_screen_mm*(math.tan(math.radians(self.AOI_size_degrees)))
        print 'AOI size mm ', self.AOI_size_mm
        self.AOI_size_px = round(self.AOI_size_mm*self.monitor_resolution_px[0]/self.monitor_resolution_mm[0])
        print 'AOI size px ', self.AOI_size_px
        self.AOI_coordinates = [self.center[0]-self.AOI_size_px, self.center[1]-self.AOI_size_px, self.center[0]+self.AOI_size_px, self.center[1]+self.AOI_size_px,]
        print 'AOI coordinates ', self.AOI_coordinates

    def wait_for_fixation(self, gazedata):
        #wait until the participant fixates at least fixation_length inside the AOI. All the samples must be inside the AOI
        if gazedata:
            self.state = self.hit_AOI(gazedata)
            if self.state:
                if self.hit_start is 0: #start counting
                    self.hit_start = time.time()
                elif (time.time()-self.hit_start) >= self.fixation_length/1000:
                    self.hist_start = 0
                    return True
            else:
                self.hit_start = 0
        return False

    def check_gaze(self, gazedata):
        if gazedata:
            if self.hit_AOI(gazedata[-1]):
                gazedata.pop(-1)
                if gazedata:
                    number_gazepoints_in = 0
                    for gazepoint in reversed(gazedata):
                        if self.hit_AOI(gazepoint):
                            number_gazepoints_in += 1
                        if number_gazepoints_in >= self.min_gazepoints_in:
                            print self.distance_in_degrees
                            return True
        return False

    def hit_AOI(self,gaze_line):
        self.validity = 0
        self.gaze_point_x = 0
        self.gaze_point_y = 0

        if gaze_line['left']['validity'] == 0 and gaze_line['right']['validity'] == 0:
            self.validity = 0
            self.gaze_point_x = round(((gaze_line['right']['screen_pos'].x + gaze_line['left']['screen_pos'].x )/2)*self.monitor_resolution_px[0])
            self.gaze_point_y = round(((gaze_line['right']['screen_pos'].y + gaze_line['left']['screen_pos'].y )/2)*self.monitor_resolution_px[1])
        elif gaze_line['left']['validity'] < 2 and gaze_line['right']['validity'] > 2:
            self.validity = 0
            self.gaze_point_x = round(gaze_line['left']['screen_pos'].x*self.monitor_resolution_px[0]*self.monitor_resolution_px[0])
            self.gaze_point_y = round(gaze_line['left']['screen_pos'].y*self.monitor_resolution_px[1]*self.monitor_resolution_px[1])
        elif gaze_line['right']['validity'] < 2 and gaze_line['left']['validity'] > 2:
            self.validity = 0
            self.gaze_point_x = round(gaze_line['right']['screen_pos'].x*self.monitor_resolution_px[0])
            self.gaze_point_y = round(gaze_line['right']['screen_pos'].y*self.monitor_resolution_px[1])
        elif (gaze_line['right']['validity'] == 2 and gaze_line['left']['validity'] == 2) or (gaze_line['right']['validity'] == 4 and gaze_line['left']['validity'] == 4):
            self.validity = 4
            self.gaze_point_x = -1
            self.gaze_point_y = -1

        self.distance_px = round(self.distance_in_px(self.gaze_point_x, self.gaze_point_y, self.center[0], self.center[1]))
        #print self.distance_px

        self.distance_in_degrees =  self.pixels_to_degrees1(self.distance_px, self.monitor_resolution_px, self.monitor_resolution_mm, self.distance_screen_mm)
        #print self.distance_in_degrees

        if self.distance_in_degrees <= self.AOI_size_degrees:
            return True
        return False

    def distance_in_px(self,gaze_x,  gaze_y, center_x, center_y):
        return math.sqrt((gaze_x-center_x)**2 + (gaze_y-center_y)**2)

    def pixels_to_degrees1(self, distance_px, monitor_size_px, monitor_size_mm, distance_to_screen_mm):
        distance_mm = round((distance_px * monitor_size_mm[0])/monitor_size_px[0])
        return math.degrees(math.atan((distance_mm)/ distance_to_screen_mm))

class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.camera_on = 0

    def next_frame(self):
        # Capture frame-by-frame
        if self.camera_on:
            ret, frame = self.cap.read()
            if frame is not None:
                #self.video_writer.write(frame)
                # Our operations on the frame come here
                #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                color = cv2.cvtColor(frame, cv2.WINDOW_NORMAL)
                # Display the resulting frame
                cv2.imshow('Camera',color)
            return True
        else:
            self.cap.release()
            cv2.destroyAllWindows()
            return False

    def status(self,status):
        self.camera_on = status

#class ET_data_plot:
#    def __init__(self):



class Calibration:
    def __init__(self,connection):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(5)
        self.window.set_title("Calibration results")
        self.calib_plot = et.CalibPlot()
        self.connection = connection
        self.close_window = 0

        #Check buttons
        self.check_button = []
        for i in range(0,5):
            self.check_button.append(gtk.CheckButton(label=None))
            self.check_button[i].set_sensitive(True)

        self.box_check_calib = gtk.VBox(True,0)
        self.box_H1 = gtk.HBox(True,0)
        self.box_H1.pack_start(self.check_button[0],False,False,0)
        self.box_H1.pack_start(self.check_button[1],False,False,0)

        self.box_H2 = gtk.HBox(True,0)
        self.box_H2.pack_start(self.check_button[2],False,False,0)

        self.box_H3 = gtk.HBox(True,0)
        self.box_H3.pack_start(self.check_button[4],False,False,0)
        self.box_H3.pack_start(self.check_button[3],False,False,0)

        self.box_check_calib.pack_start(self.box_H1,False,False,0)
        self.box_check_calib.pack_start(self.box_H2,False,False,0)
        self.box_check_calib.pack_start(self.box_H3,False,False,0)

        #accept or recalibrate button
        self.button_accept_calib = gtk_widgets.button_gtk('Accept Calibration', self.on_accept_calibration_clicked)
        self.button_recalib = gtk_widgets.button_gtk('Recalibrate', self.on_recalibration_clicked)

        self.box_H2 = gtk.HBox(True)
        self.box_H2.pack_start(self.button_accept_calib.get(),False,False,0)
        self.box_H2.pack_start(self.button_recalib.get(),False,False,0)

        self.box_V1 = gtk.VBox(False,0)
        self.box_V1.pack_start(self.calib_plot,False,False,0)
        self.box_V1.pack_start(self.box_check_calib,False,False,0)
        self.box_V1.pack_start(self.box_H2,False,False,0)

        self.window.add(self.box_V1)
        self.window.show_all()

    def on_calib_done(self,eyetracker):
        self.button_accept_calib.get().set_sensitive(True)
        self.button_recalib.get().set_sensitive(True)
        self.calib_plot.set_eyetracker(eyetracker)
        self.set_check_button(True)
        self.window.show()

    def on_accept_calibration_clicked(self,button):
        self.connection.send_event('start')
        self.close_calib_window()

    def close_calib_window(self):
        self.close_window = 3
        self.window.destroy()

    def on_recalibration_clicked(self,button):
        self.calib_plot.set_eyetracker(None)

        msg = 'calibrate,11111'
        calib_points = ''
        for button in self.check_button:
            print button.get_active()
            if button.get_active():
                calib_points += '1'
            else:
                calib_points += '0'
        if calib_points != '00000':
            msg = 'calibrate,' + calib_points
        self.set_check_button(False)
        self.connection.send_event(msg)
        self.button_accept_calib.get().set_sensitive(False)
        self.button_recalib.get().set_sensitive(False)
        self.window.hide()

    def set_check_button(self,sensitive_state,active_state = False):
        for button in self.check_button:
            button.set_sensitive(sensitive_state)
            button.set_active(False)

    def delete_event(self, widget, event, data=None):
        self.close_window += 1
        if self.close_window >= 3:
            return False
        return True

    def destroy(self, widget, data=None):
        self.eyetracker = None
        self.calib_plot.set_eyetracker(None)

class Connection:
    def __init__(self):
        self.hostAddress= 'localhost'
        self.hostPort= 5447

    def connect_to_host(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.s.connect((self.hostAddress,self.hostPort))
            self.s.settimeout(2)
            print 'connected and waiting for event'
            self.event = self.read_event()
            self.s.settimeout(0.1)
            return 'connected'
        except:
            print'error'
            return 'disconnected'

    def disconnect(self):
        self.s.close()

    def send_event(self,msg):
        try:
            print 'sending:', msg
            self.s.sendall(msg)
        except:
            print 'Sending error. No connection to socket'

    def read_event(self):
        try:
            self.event = self.s.recv(1024)
        except:
            return None
        return self.event

    def mod_parameters(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(5)
        self.window.set_title("TCP/IP Connection")
        #V2_1_2
        #Connection to Socket
        self.box_main = gtk.HBox(False,10)
        self.box_V2_1_2_1 = gtk.VBox(True,0)
        self.box_V2_1_2_2 = gtk.VBox(True,0)
        self.box_V2_1_2_3 = gtk.VBox(True,0)

        #V2_1_2_1
        self.host_label = gtk.Label()
        self.host_label.set_alignment(0.0, 0.5)
        self.host_label.set_markup("<b>Host:</b>")
        self.port_label = gtk.Label()
        self.port_label.set_alignment(0.0, 0.5)
        self.port_label.set_markup("<b>Port:</b>")

        self.box_V2_1_2_1.pack_start(self.host_label,False,False,0)
        self.box_V2_1_2_1.pack_start(self.port_label,False,False,0)

        #V2_1_2_2
        self.host_entry = gtk.Entry()
        self.host_entry.set_max_length(50)
        self.host_entry.connect("activate", self.host_entry_callback,self.host_entry)
        self.host_entry.set_text(self.hostAddress)

        self.port_entry = gtk.Entry()
        self.port_entry.set_max_length(50)
        self.port_entry.connect("activate", self.port_entry_callback,self.port_entry)
        self.port_entry.set_text(str(self.hostPort))

        self.box_V2_1_2_2.pack_start(self.host_entry,False,False,0)
        self.box_V2_1_2_2.pack_start(self.port_entry,False,False,0)

        #V2_1_2_3
        #Connect Button
        self.buttonCon = gtk.HButtonBox()
        #self.create_button(self.buttonCon,'Connect', self.on_connect_button_clicked)

        self.connection_label = gtk.Label()
        self.connection_label.set_markup("<b>Not Connected</b>")
        self.connection_label.set_alignment(0.0, 0.5)

        self.box_V2_1_2_3.pack_start(self.connection_label,False,False,0)
        self.box_V2_1_2_3.pack_end(self.buttonCon,False,False,0)

        self.box_main.pack_start(self.box_V2_1_2_1,False,False,0)
        self.box_main.pack_start(self.box_V2_1_2_2,False,False,0)
        self.box_main.pack_start(self.box_V2_1_2_3,False,False,0)

        self.window.add(self.box_main)

        self.window.show_all()

    def host_entry_callback(self,widget,entry):
        self.hostAddress = entry.get_text()

    def port_entry_callback(self,widget,entry):
        self.hostPort = int(entry.get_text())

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        self.window.destroy()

class TrackStatus(gtk.DrawingArea):
    MAX_AGE = 30.0
    MAX_STORAGE = 60.0

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(300, 300)
        self.gaze_data = None
        self.connect("expose_event", self.on_expose)

    def redraw(self):
        if self.window:
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    def draw_eye(self, ctx, validity, camera_pos, screen_pos, age):
        screen_pos_x = screen_pos.x - .5
        screen_pos_y = screen_pos.y - .5

        eye_radius = 0.075
        iris_radius = 0.03
        pupil_radius = 0.01

        opacity = 1 - age * 1.0 / TrackStatus.MAX_AGE
        if validity <= 1:
            ctx.set_source_rgba(1, 1, 1, opacity)
            ctx.arc(1 - camera_pos.x, camera_pos.y, eye_radius, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgba(.5, .5, 1, opacity)
            ctx.arc(1 - camera_pos.x + ((eye_radius - iris_radius / 2) * screen_pos_x), camera_pos.y + ((eye_radius - iris_radius / 2) * screen_pos_y), iris_radius, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgba(0, 0, 0, opacity)
            ctx.arc(1 - camera_pos.x + ((eye_radius - iris_radius / 2) * screen_pos_x), camera_pos.y + ((eye_radius - iris_radius / 2) * screen_pos_y), pupil_radius, 0, 2 * math.pi)
            ctx.fill()

    def draw(self,ctx):
        ctx.set_source_rgb(0., 0., 0.)
        ctx.rectangle(0, 0, 1, .9)
        ctx.fill()

        try:
            self.gazedata_temp = self.gaze_data[-1]

        except:
            self.gazedata_temp = None

        # paint left rectangle
        if self.gazedata_temp is not None and self.gazedata_temp['left']['validity'] == 0:
            ctx.set_source_rgb(0, 1, 0)
        else:
            ctx.set_source_rgb(1, 0, 0)
        ctx.rectangle(0, .9, .5, 1)
        ctx.fill()

        # paint right rectangle
        if self.gazedata_temp is not None and self.gazedata_temp['right']['validity'] == 0:
            ctx.set_source_rgb(0, 1, 0)
        else:
            ctx.set_source_rgb(1, 0, 0)
        ctx.rectangle(.5, .9, 1, 1)
        ctx.fill()

        if self.gazedata_temp is None:
            return

        self.distance = []
        # paint eyes
        for eye in ('left', 'right'):
            (validity, age, camera_pos, screen_pos, part_pos) = self.find_gaze(eye)
            self.draw_eye(ctx, validity, camera_pos, screen_pos, age)
            self.distance.append(part_pos.z)

        ctx.select_font_face('Arial' , cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(0.08)

        #ctx.translate(0.5, 0.5)
        ctx.move_to(0.4,0.87)
        ctx.set_source_rgb(1, 1, 1)
        ctx.show_text(str(self.distance[0])[:3])#("Sans Italic 12", ctx, .5, .5, str(self.gaze_data_track_status['left']['camera_pos'].z[-1]))

    def find_gaze(self, eye):
        i = 0

        for gaze in reversed(self.gaze_data):
            if gaze[eye]['validity'] <= 1:
                return (gaze[eye]['validity'], i, gaze[eye]['camera_pos'], gaze[eye]['screen_pos'],gaze[eye]['part_pos'])
            i += 1
        return (gaze[eye]['validity'], 0, gaze[eye]['camera_pos'], gaze[eye]['screen_pos'],gaze[eye]['part_pos'])

    def on_expose(self, widget, event):
        ctx = widget.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        ctx.clip()

        rect = widget.get_allocation()
        ctx.scale(rect.width, rect.height)
        self.draw(ctx)
        return False

class GazePlot(gtk.DrawingArea):
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(300, 300)
        self.gaze_data = None
        self.connect("expose_event", self.on_expose)

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
        ctx.set_source_rgb(0.9, .9, 0.9)
        ctx.fill()

        for i in np.arange(0,1,0.1):
            ctx.move_to(0, i)
            ctx.line_to(1, i)
            ctx.move_to(i, 0)
            ctx.line_to(i, 1)
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(0.0005)
        ctx.stroke()

        try:
            self.gazedata_temp = self.gaze_data[-1]
        except:
            self.gazedata_temp = None

        if self.gazedata_temp is None:
            return

        if self.gazedata_temp['left']['validity'] == 4 and self.gazedata_temp['right']['validity'] == 4:
            return

        samples = []
        for gaze in self.gaze_data:
            if gaze['left']['validity'] != 4 and gaze['right']['validity'] != 4:
                samples.append(self.eyes_average(gaze))

        try:
            pointX = sum([pair[0] for pair in samples])/len(samples)
            pointY = sum([pair[1] for pair in samples])/len(samples)
        except:
            return

        ctx.arc(pointX, pointY, 0.01, 0, 2 * math.pi)
        ctx.set_source_rgb(1,0,0)
        ctx.fill()

    def eyes_average(self,gaze):
        if gaze['left']['validity'] == 0 and gaze['right']['validity'] == 0:
            return ((gaze['left']['screen_pos'].x+gaze['right']['screen_pos'].x)/2, (gaze['left']['screen_pos'].y+gaze['right']['screen_pos'].y)/2)
        if gaze['left']['validity'] == 4 and gaze['right']['validity'] == 0:
            return (gaze['right']['screen_pos'])
        if gaze['left']['validity'] == 0 and gaze['right']['validity'] == 4:
            return (gaze['left']['screen_pos'])
        return (gaze['left']['screen_pos'])

class Message:
    def __init__(self):
        self.msg_in = None
        self.msg_out = None

    def msg_split(self, msg):
       return  msg.split(',')

    def pseq(self,msg):
        seq = self.msg_split(msg)
        return [seq[0], seq[1], seq[2],(seq[3],seq[4]),seq[5]]

class main_thread:
    def __init__(self):

        self.menu_items = (
            ( "/_File",         None,         None, 0, "<Branch>" ),
            ( "/File/_Open",     "<control>O", 0, 0, None ),
            ( "/File/_Save",    "<control>S", 0, 0, None ),
            ("/_Tools",         None,         None, 0, "<Branch>" ),
            ( "/Tools/_TCPIP Connection",None, self.mod_connection_param, 0, None ),
            ( "/Tools/_Eye tracker Connection", None, self.mod_eye_tracker, 0, None ),
            ( "/Tools/_Camera",     None, self.on_camera_button_clicked, 0, None ),
            )

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(0)
        self.window.set_size_request(960, 460)
        self.window.set_title("Infant gaze monitor and control")
        self.eyetracker_ob = et.Eye_tracker()
        self.trackstatus = TrackStatus()
        self.gazeplot = GazePlot()
        self.message = Message()
        self.msg = None
        self.camera = None

        self.eyetracker = None
        self.eyetrackers = {}
        self.liststore = gtk.ListStore(str, str, str)

        self.gaze_video_flag = ''
        self.read_timeout =200
        self.gaze_contingency_timeout = 20
        self.gaze_contingency_fixation_length = 1000 #1 seg
        self.min_gazepoints_in = 12
        self.time_gaze_contingency_finishes  = time.clock()
        self.time_trigger_gaze_contingency = 3
        self.check_eyetracker_timeout = 1000
        self.draw_gaze_data_timeout = 100

        self.monitor_resolution = [1920, 1080]
        self.gaze_AOI_center = [400, 300]
        self.gaze_AOI_degrees = 4
        self.monitor_size_mm = [520, 300]
        self.distance_to_screen_mm = 700

        self.conn_status = 'disconnected' #'connected'
        self.gazeapp_status = 'standby' #'waiting', 'gaze_contingency'
        self.control_status = 'gaze_contingency' #'automatic'
        self.presentation_status = 'init' # 'nstr' 'strd' 'paus' 'stop' 'atgb'

        self.same_trial = 0
        self.trialno = 0
        self.sequence = []
        self.sequence_info = []
        self.msg_in = None
        self.calib_done = 0 #First calibration iteration = 0, rest = 1

        self.socket = Connection()
        self.gazecontingency = GazeContingency(self.monitor_resolution, self.gaze_AOI_center, self.gaze_AOI_degrees, self.monitor_size_mm,self.gaze_contingency_fixation_length,self.min_gazepoints_in, self.distance_to_screen_mm)

        self.close_window = 0

        #Menu bar
        self.menubar = self.get_main_menu()

        #FIRST LEVEL
        self.box_sub1 = gtk.HBox(True,0)

        self.box_sub1_1 = gtk.HBox(False,0)
        self.box_sub1_2 = gtk.HBox(False,0)
        self.box_sub1_3 = gtk.HBox(False,0)

        self.trialno_label = gtk.Label()#Trial number label
        self.trialno_label.set_markup('<span size="12000">Current trial:</span>')
        self.trialno_label.set_alignment(0.0, 0.5)
        self.button_connection = gtk.HButtonBox() #Connect Button
        self.create_button(self.button_connection,'Connect', self.on_connect_button_clicked)
        self.connection_label = gtk.Label()
        self.connection_label.set_markup('<b>Not Connected</b>')
        self.connection_label.set_alignment(0.0, 0.5)

        #PACK LEVEL
        #self.box_sub1_1.pack_start(self.time_label,False,True,10)
        #self.box_sub1_2.pack_start(self.trialno_label,False,True,0)

        self.box_sub1_1.pack_start(self.button_connection,False,False,0)
        self.box_sub1_1.pack_start(self.connection_label,False,False,10)
        self.box_sub1.pack_start(self.box_sub1_1,True,True,20)
        self.box_sub1.pack_start(self.box_sub1_2,True,True,10)
        self.box_sub1.pack_start(self.box_sub1_3,True,True,20)

        #SECOND LEVEL
        self.box_sub2 = gtk.HBox(False,10)

        #packing V2 left
        self.box_V2_1 = gtk.VBox(False,10)
        #TreeView for discoveral eye trackers
        self.box_V2_1_1 = gtk.VBox(False,10)
        self.treeview = gtk.TreeView(self.liststore)
        #self.treeview.connect("row-activated", self.row_activated)

        self.cond_column, self.cond_cell = self.new_tree_view_column('Condition', self.treeview, 0, width = 100)
        self.trial_column, self.trial_cell = self.new_tree_view_column('Trials:', self.treeview, 1, width = 70)
        self.presented_column, self.presented_cell = self.new_tree_view_column('ET data', self.treeview, 2, width = 70)
        #self.total_column, self.total_cell = self.new_tree_view_column('Total', self.treeview, 1, width = 40)
        #self.etdata_column, self.etdata_cell = self.new_tree_view_column('with ET data', self.treeview, 2, width = 70)

        self.current_trial_label = gtk.Label()
        self.current_trial_label.set_alignment(0.0, 0.5)
        self.current_trial_label.set_markup("  Current trial:")

        #scroll window
        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.scrolled_window.set_size_request(-1, 150)
        self.scrolled_window.add(self.treeview)

        self.experiment_info_label = gtk.Label('Experiment Info')
        self.experiment_info_label.modify_font(pango.FontDescription('Lucida Sans Bold %s' % 10))
        self.separator = gtk.HSeparator()
        self.participant_label = gtk.Label()
        self.participant_label.set_markup('  Participant: ')
        self.participant_label.modify_font(pango.FontDescription('Lucida Sans %s' % 8))
        self.participant_label.set_alignment(0.0, 0.5)

        self.presentation_label = gtk.Label()
        self.presentation_label.set_markup("  Presentation status: Disconnected")
        self.presentation_label.set_alignment(0.0, 0.5)

        self.total_trials_label = gtk.Label()
        self.total_trials_label.set_markup("  Trials presented:")
        self.total_trials_label.set_alignment(0.0, 0.5)

        self.frame_box = gtk.VBox(False,False)
        self.frame_box.pack_start(self.participant_label,False,False,5)
        self.frame_box.pack_start(self.current_trial_label,False,False,5)
        self.frame_box.pack_start(self.total_trials_label,False,False,5)
        self.frame_box.pack_start(self.presentation_label,False,False,5)

        self.time_label = gtk.Label() #Time label
        self.time_label.set_alignment(0.0, 0.5)
        font_description = pango.FontDescription('Lucida Sans bold %s' % 12)
        self.time_label.modify_font(font_description)

        self.time_label.set_text("00:00")

        self.box_V2_1_2 = gtk.HBox(False,0)
        self.box_V2_1_2.pack_start(self.frame_box, True, True)
        self.box_V2_1_2.pack_start(self.time_label, False,False)

        self.box_V2_1_1.pack_start(self.experiment_info_label,False,False,0)
        self.box_V2_1_1.pack_start(self.separator,False,False,0)
        self.box_V2_1_1.pack_start(self.box_V2_1_2,False,False,0)
        self.box_V2_1_1.pack_start(self.scrolled_window,False,False,0)



        #add everything to pack V2 left
        self.box_V2_1.pack_start(self.box_V2_1_1,False,False,0)
        #self.box_V2_1.pack_start(self.box_V2_1_2,False,False,0)
        #self.box_V2_1.pack_start(self.box_V2_1_4,False,False,0)

        self.calibplot_label = gtk.Label()
        self.calibplot_label.set_markup("<b>Calibration Plot:</b>")
        self.calibplot_label.set_alignment(0.0, 0.5)

        self.trackstatus_label = gtk.Label()
        self.trackstatus_label.set_markup("<b>Trackstatus:</b>")
        self.trackstatus_label.set_alignment(0.0, 0.5)

        #add everything to V2 packing box
        self.box_sub2.pack_start(self.box_V2_1,False,False,20)
        self.box_sub2.pack_start(self.gazeplot,False,False,0)
        self.box_sub2.pack_start(self.trackstatus,False,False,20)

        #Pack box V3
        self.box_sub3 = gtk.HBox(True,10)

        self.box_V3_1 = gtk.VBox(False,0)
        self.box_V3_1_1 = gtk.HBox(False,10)

        self.experimentmode_label = gtk.Label()
        self.experimentmode_label.set_markup("<b>Experiment mode:</b>")
        self.experimentmode_label.set_alignment(0.0, 0.5)

        #Radio button Gaze_contingencyy/Automatic
        self.radio_button_gaze_contingency = gtk.RadioButton(None,'Gaze contingency')
        self.radio_button_gaze_contingency.connect('toggled',self.on_toggle_button_gaze_contingency_clicked,'Gaze contingency')
        self.radio_button_gaze_contingency.set_active(True)
        self.box_V3_1_1.pack_start(self.radio_button_gaze_contingency,False,False,0)

        self.radio_button_automatic = gtk.RadioButton(self.radio_button_gaze_contingency,'Automatic')
        self.radio_button_automatic.connect('toggled',self.on_toggle_button_automatic_clicked,'Automatic')
        self.box_V3_1_1.pack_start(self.radio_button_automatic,False,False,0)

        self.box_V3_1.pack_start(self.experimentmode_label,False,False,0)
        self.box_V3_1.pack_start(self.box_V3_1_1,False,False,0)

        #Experiment  buttons
        self.box_V3_2 = gtk.VBox(False,0)
        self.box_V3_2_1 = gtk.HBox(False,0)

        self.experiment_control_label = gtk.Label()
        self.experiment_control_label.set_markup("<b>Experiment control:</b>")
        self.experiment_control_label.set_alignment(0.0, 0.5)
        #Start Button
        self.button_start = gtk.HButtonBox()
        self.create_button(self.button_start,'Start', self.on_start_button_clicked, sensitivity = True)
        #Pause Button
        self.button_pause = gtk.HButtonBox()
        self.create_button(self.button_pause,'Pause', self.on_pause_button_clicked, sensitivity = True)
        #Stop Button
        self.button_stop = gtk.HButtonBox()
        self.create_button(self.button_stop,'Stop', self.on_stop_button_clicked, sensitivity = True)
        #Calibration Button
        self.buttonCal = gtk.HButtonBox()
        self.create_button(self.buttonCal,'Calibration', self.on_calib_button_clicked,sensitivity = True)

        self.box_V3_2_1.pack_start(self.button_start,True,False,0)
        self.box_V3_2_1.pack_start(self.button_pause,False,False,0)
        self.box_V3_2_1.pack_start(self.button_stop,False,False,0)
        self.box_V3_2_1.pack_start(self.buttonCal,False,False,0)

        self.box_V3_2.pack_start(self.experiment_control_label,False,False,0)
        self.box_V3_2.pack_start(self.box_V3_2_1,False,False,0)

        #Trials  buttons
        self.box_V3_3 = gtk.VBox(False,0)
        self.box_H3_3_1 = gtk.HBox(False,0)

        self.experiment_trials_label = gtk.Label()
        self.experiment_trials_label.set_markup("<b>Trial control:</b>")
        self.experiment_trials_label.set_alignment(0.0, 0.5)

        #Next trial button
        self.button_next_trial = gtk.HButtonBox()
        self.create_button(self.button_next_trial,'Next Trial', self.on_next_trial_button_clicked, sensitivity = True)

        #Attention grabber button
        self.button_attentiongrabber = gtk.HButtonBox()
        self.create_button(self.button_attentiongrabber,'Attention graber', self.on_attentiongrabber_button_clicked, sensitivity = True)

        #add buttons to V3 packing box
        self.box_H3_3_1.pack_start(self.button_next_trial,False,False,0)
        self.box_H3_3_1.pack_start(self.button_attentiongrabber,False,False,0)

        self.box_V3_3.pack_start(self.experiment_trials_label,False,False,0)
        self.box_V3_3.pack_start(self.box_H3_3_1,False,False,0)

        #add buttons to sub3 packing box
        self.box_sub3.pack_start(self.box_V3_1,False,False,0)
        self.box_sub3.pack_start(self.box_V3_2,False,False,0)
        self.box_sub3.pack_start(self.box_V3_3,False,False,0)

        self.box_main = gtk.VBox(False,0)
        self.box_main.pack_start(self.menubar,False,True,0)

        self.box_main.pack_start(self.box_sub2,False,False,10)
        self.box_main.pack_start(self.box_sub3,False,False,10)
        self.box_main.pack_start(self.box_sub1,False,False,10)

        #Check if any eye tracker is connected to start showing eye tracker status and gazeplot
        glib.timeout_add(self.check_eyetracker_timeout,self.check_eyetracker)

        self.handle_interface_buttons()
        self.window.add(self.box_main)
        self.window.show_all()

        #debug
        #msg = '6,4,2,8,6,4,4,6,3,4,6,4,3,4,2,8,6,4,1,3,2,8,2,9,4,1,6,3,6,4,2,8,4,5,6,4,5,1,3,6,4,4,3,6,3,3,1,5,6,3,1,6,4,2,9,2,8,6,3,6,3,5,2,5,2,8,5,5,6,4,5,2,9,6,4,3,3,4,4,5,3,3,2,8,2,9,3,2,9,2,9,1,2,9,5,4,2,8,1,6,3,2,8,1,5,2,8,4,6,3,2,9,6,3,3,6,3,6,3,1,4,4,2,9,5,3,1,2,9,6,3,2,9,2,8,2,8,5,1,1,6,4,6,4'
        #path = "C:/Users/edz/OneDrive @ Tobii Technology AB/PhD\Monitoring tool/version 1.4/Matlab/stimuli_order/sequence_info.csv"
        #self.read_sequence_info(path)
        #self.init_presentation_sequence(msg)
        #print self.sequence_dict
        #self.treeview.columns_autosize()
        #self.trial_column.set_sort_order(0)
        #self.model_column.set_sort_indicator(3)
        #self.presentation_label.set_label('  Presentation status: Started')
        #glib.timeout_add(1000, self.count)
        #self.starttime = time.time()

    def get_main_menu(self,):
        accel_group = gtk.AccelGroup()
        # This function initializes the item factory.
        # Param 1: The type of menu - can be MenuBar, Menu,
        #          or OptionMenu.
        # Param 2: The path of the menu.
        # Param 3: A reference to an AccelGroup. The item factory sets up
        #          the accelerator table while generating menus.
        item_factory = gtk.ItemFactory(gtk.MenuBar, "<main>", accel_group)

        # This method generates the menu items. Pass to the item factory
        #  the list of menu items
        item_factory.create_items(self.menu_items)

        # Attach the new accelerator group to the window.
        self.window.add_accel_group(accel_group)

        # need to keep a reference to item_factory to prevent its destruction
        self.item_factory = item_factory
        # Finally, return the actual menu bar created by the item factory.
        return item_factory.get_widget("<main>")

    def mod_connection_param(self,w,data):
        self.socket.mod_parameters()

    def mod_eye_tracker(self,w,data):
        self.eyetracker_ob.mod_parameters()

    def check_eyetracker(self):
        if self.eyetracker_ob.get_eyetracker():
            self.eyetracker = self.eyetracker_ob.get_eyetracker()
            self.framerate = self.eyetracker_ob.get_framerate()
            glib.timeout_add(self.draw_gaze_data_timeout,self.draw_gaze_data)
            return False
        else:
            return True

    def new_tree_view_column(self, name, treeview, number, width = 50):
        column = gtk.TreeViewColumn(name)
        column_cell = gtk.CellRendererText()
        treeview.append_column(column)
        column.pack_start(column_cell, True)
        column.set_attributes(column_cell, text = number)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(width)
        return column, column_cell

    def draw_gaze_data(self):
        self.trackstatus.gaze_data = self.eyetracker_ob.get_data(1*self.framerate) #1 sec
        self.gazeplot.gaze_data = self.eyetracker_ob.get_data(int(np.ceil(0.05*self.framerate))) #50 ms
        self.gazeplot.redraw()
        self.trackstatus.redraw()
        return True

    def on_camera_button_clicked(self,w,data):
        if not self.camera:
            self.camera = Camera()
            self.camera.status(1)
            glib.timeout_add(100,self.camera.next_frame)
        else:
            self.camera.status(0)
            self.camera = None
    def on_calib_button_clicked(self,button):
        if self.presentation_status == 'nstr':
            self.send_event('calb')
        else:
            self.msg = 'calb'

    def on_connect_button_clicked(self,button):
        #Connect to the presentation software
        self.conn_status = self.socket.connect_to_host()
        print self.conn_status
        if self.conn_status is 'connected':
            self.connection_label.set_markup("<b>Connected!</b>")
            glib.timeout_add(self.read_timeout,self.check_msg) #Check if there is any msg every 200 ms
        else:
            self.connection_label.set_markup("<b>No connection</b>")

    def on_stop_button_clicked(self, button):
        d = gtk.Dialog()
        d.set_position(gtk.WIN_POS_CENTER)
        d.add_buttons(gtk.STOCK_YES, 1, gtk.STOCK_NO, 2)

        label = gtk.Label('Do you want to stop the presentation?')
        label.show()
        d.vbox.pack_start(label)
        answer = d.run()
        if answer:
            self.msg = 'stop'
            d.destroy()

    def on_pause_button_clicked(self, button):
        if self.presentation_status == 'paus':
            self.send_event('paus')
            return
        self.msg = 'paus'

    def on_attentiongrabber_button_clicked(self, button):
        if self.presentation_status == 'atgb':
            self.send_event('atgb')
            return
        self.msg = 'atgb'

    def on_next_trial_button_clicked(self, button):
        #self.show_next_trial(0)
        self.msg = 'next_trial'

    def on_start_button_clicked(self, button):
        if self.gazeapp_status is not 'waiting':
            self.send_event('start')

    def show_next_trial(self,gaze_contingency):
        print 'next trial'
        if gaze_contingency:
            self.send_event('Gnext_trial')
        else:
            self.send_event('next_trial')
        if self.eyetracker:
            trial = self.trial[:]
            glib.timeout_add(2000,self.et_data_assessment,trial)

    def et_data_assessment(self, trial):
        gaze_data = self.eyetracker_ob.get_data(1*self.framerate) #1 sec
        count = 0
        for gaze_line in gaze_data:
            if gaze_line['left']['validity'] != 4 and gaze_line['right']['validity'] != 4:
                count += 1
        perc = (float(count)/len(gaze_data))*100
        print self.trial
        print 'count' + str(count)
        print 'len' + str(len(gaze_data))
        print str(perc), '%'
        if perc > 80 and trial != '8':
            self.sequence_dict[trial][8] += 1
        self.sequence_dict[trial][9] =  int((self.sequence_dict[trial][9]*(self.sequence_dict[trial][7]-1)/float(self.sequence_dict[trial][7]) + perc/float(self.sequence_dict[trial][7])))
        self.update_list(trial, 2, self.sequence_dict[trial][8], self.sequence_dict[trial][9],'%' )
        return False


    def send_event(self, msg):
        self.gazeapp_status = 'waiting'
        self.socket.send_event(msg)
        glib.timeout_add(15000, self.handle_waiting_timeout)
        print '> ', msg
        print 'waiting'

    def handle_waiting_timeout(self):
        if self.gazeapp_status == 'waiting':
            self.gazeapp_status = 'standby'
            print 'not waiting anymore'
        return False

    def create_button(self,button,label, functionCall, width = 0, spacing = 10, sensitivity = True):
        button.set_border_width(width)
        button.set_spacing(spacing)
        button.set_layout(gtk.BUTTONBOX_END)

        button.buttonProp = gtk.Button(label)
        button.buttonProp.connect("clicked",functionCall)
        button.buttonProp.set_sensitive(sensitivity)
        button.add(button.buttonProp)

    #def time_gaze_contingengy_entry_callback(self, widget,entry):
    #    self.time_trigger_gaze_contingency = int(entry.get_text())

    def on_toggle_button_gaze_contingency_clicked(self,widget,data):
        self.control_status = 'gaze_contingency'

    def on_toggle_button_automatic_clicked(self, widget, data):
        self.control_status = 'automatic'

    def check_msg(self):
        #Read coming events:
        msg = self.socket.read_event()
        if msg is not None:
            print msg, '< '
            return self.handle_msg(msg)
        return True

    def handle_msg(self, msg):
        self.message.msg_in = msg.split('<>')
        print self.message.msg_in
        for msg in self.message.msg_in:
            if msg == 'next':
                if self.msg is None or self.msg == 'next_trial':
                    if not self.same_trial:
                        self.trialno += 1
                    #if str(self.sequence[self.trialno-1]) == '8' or str(self.sequence[self.trialno-1]) == '9':
                    #    self.trialno += 2
                    self.total_trials_label.set_label('  Trials presented: ' + str(self.trialno))
                    if self.trialno <= len(self.sequence):
                        self.trial = self.sequence[self.trialno-1]
                        self.current_trial_label.set_label('  Current trial: ' + str(self.sequence_dict[self.trial][0 ]))
                        if not self.same_trial:
                            self.sequence_dict[self.trial][7] += 1
                            self.update_list(self.trial, 1, self.sequence_dict[self.trial][7], self.sequence_dict[self.trial][6], '')
                        self.send_event('next' + str(self.trialno))
                        if self.same_trial:
                            self.same_trial = 0
                    else:
                        self.send_event('stop')
                else:
                    self.send_event(self.msg)
                self.msg = None

            elif msg[:4] == 'part':
                self.participant = msg[4:]
                self.participant_label.set_label('  Participant: ' + self.participant)
                print 'participant: ',self.participant

            elif msg[:4] == 'path':
                self.info_sequence_path = msg[4:]
                self.read_sequence_info(self.info_sequence_path)
            elif msg[:4] == 'pseq':
                self.init_presentation_sequence(msg[4:])

            elif msg == 'done':
                self.gazeapp_status = 'standby'
            elif msg[:4] == 'chck':
                if not self.msg:
                    if self.control_status == 'gaze_contingency':
                        print 'Gaze contingency starts  '
                        self.gazeapp_status = 'gaze_contingency'
                        self.gaze_AOI_center[0] = float(self.sequence_dict[self.trial][3])
                        self.gaze_AOI_center[1] = float(self.sequence_dict[self.trial][4])
                        self.gaze_AOI_degrees = float(self.sequence_dict[self.trial][5])
                        print 'center ', self.gaze_AOI_center
                        print 'degrees ', self.gaze_AOI_degrees
                        self.time_trigger_gaze_contingency = float(msg[4:])
                        #Put some label on the app to know that we are waiting for event...
                        self.time_gaze_contingency_finishes  = self.time_trigger_gaze_contingency + time.clock()
                        self.gazecontingency.set_AOI_coordinates(self.gaze_AOI_center, self.gaze_AOI_degrees, self.distance_to_screen_mm)
                        if self.check_gaze():
                            self.show_next_trial(1)
                        else:
                            self.send_event('fail')
                            glib.timeout_add(self.gaze_contingency_timeout, self.handle_gaze_contingency)
                    else:
                        self.show_next_trial(0)
                else:
                    self.send_event(self.msg)
                    self.msg = None

            elif msg == 'check_video':
                if not self.msg:
                    if self.control_status == 'gaze_contingency':
                        self.gazeapp_status = 'gaze_contingency'
                        self.gaze_AOI_center[0] = float(self.sequence_dict[self.trial][3])
                        self.gaze_AOI_center[1] = float(self.sequence_dict[self.trial][4])
                        print self.gaze_AOI_center
                        self.gaze_AOI_degrees = float(self.sequence_dict[self.trial][5])
                        print self.gaze_AOI_degrees
                        self.gazecontingency.set_AOI_coordinates(self.gaze_AOI_center, self.gaze_AOI_degrees, self.distance_to_screen_mm)
                        glib.timeout_add(1000, self.handle_gaze_contingency_video)
                else:
                    self.send_event(self.msg)
                    self.msg = None
            elif msg == 'close':
                self.gaze_video_flag = 'close'
            elif msg == 'calib_done':
                self.handle_calib_results()
            elif msg == 'strt' or msg == 'nstr' or msg == 'stop' or msg == 'paus' or msg == 'atgb':
                self.presentation_status = msg
                self.current_trial_label.set_label('  Current trial: ')
                if self.presentation_status == 'paus' or self.presentation_status == 'atgb':
                    self.same_trial = 1
                    self.presentation_label.set_label('  Presentation status: Pause')
                if self.presentation_status == 'stop':
                    self.disconnect_from_socket()
                    self.presentation_label.set_label('  Presentation status: Disconnected')
                    self.participant_label.set_label('  Participant:')
                    self.total_trials_label.set_label('  Trials presented:')

                    return False
                elif self.presentation_status == 'strt':
                    glib.timeout_add(1000, self.count)
                    self.starttime = time.time()
                    self.presentation_label.set_label('  Presentation status: Started')
                elif self.presentation_status == 'nstr':
                    self.presentation_label.set_label('  Presentation status: Not started')
                self.handle_interface_buttons()
                print 'gazeapp status: ', self.gazeapp_status
                print 'presentation status:', self.presentation_status
        return True

    def update_list(self, trial, column, first, second, f=''):
        for line in self.liststore:
            if line[0] == self.sequence_dict[trial][0]:
                line[column] = str(first) + '/' + str(second) + f
                return False

    def count(self):
        # Split time into minutes and seconds
        if self.presentation_status != 'nsrt' or self.presentation_status != 'init':
            timediff = time.time() - self.starttime
            (self.m, self.s) = divmod(timediff, 60.0)
            self.time_label.set_text("%02i:%02i"% (self.m , self.s))
            return True
        else:
            self.time_label.set_text("00:00")
            return False

    def init_presentation_sequence(self, msg):
        self.sequence = msg.split(',')
        for seq in self.sequence:
            self.sequence_dict[seq][6]+=1
        print self.sequence_dict


        for k, v in self.sequence_dict.items():
            self.liststore.append((v[0], '0' + '/' + str(v[6]), '0' + '/' + '0%'))

    def read_sequence_info(self, path):
        self.sequence_dict = {}
        self.sequence_info = []
        data = open(path)
        next(data)
        for line in data:
            line = line[:-1]
            l = line.split(';')
            self.sequence_dict.update({l[0]: [l[1], l[2], l[3], l[4], l[5], l[6], 0, 0, 0, 0]})

    def handle_calib_results(self):
        if self.calib_done == 0:
            self.calib_window = Calibration(self.socket)
            self.calib_done = 1
        self.calib_window.on_calib_done(self.eyetracker)
        self.calib_window.set_check_button(True)

    def handle_interface_buttons(self):
        if self.presentation_status == 'init' or self.presentation_status == 'stop':
            self.button_sensitivity(False, False, False, False, False, True, False)
        elif self.presentation_status == 'nstr':
            self.button_sensitivity(True, False, False, False, False, False, True)
        elif self.presentation_status == 'strt':
            self.button_sensitivity(False, True, True, True, True, False, True)
        elif self.presentation_status == 'paus':
            self.button_sensitivity(False, True, False, False, True, False, True)

    def disconnect_from_socket(self):
        if self.conn_status is 'connected':
            self.socket.disconnect()
            self.conn_status = 'disconnected'
        self.handle_interface_buttons()
        self.connection_label.set_markup("<b>Not Connected</b>")
        self.gazeapp_status = 'standby'
        self.presentation_status = 'init'

    def button_sensitivity(self, start_b, stop_b, next_t_b, att_grabber_b, pause_b, connect_b, cal_b):
        self.button_start.set_sensitive(start_b)
        self.button_pause.set_sensitive(pause_b)
        self.button_stop.set_sensitive(stop_b)
        self.button_next_trial.set_sensitive(next_t_b)
        self.button_attentiongrabber.set_sensitive(att_grabber_b)
        self.button_connection.set_sensitive(connect_b)
        self.buttonCal.set_sensitive(cal_b)

    def check_gaze(self):
        self.gaze_data_contingency = self.eyetracker_ob.get_data(60)
        self.gc_result = self.gazecontingency.check_gaze(self.gaze_data_contingency)
        return self.gc_result


    def handle_gaze_contingency_video(self):
        if self.gaze_video_flag == 'close':
            return False
        if self.check_gaze():
            self.send_event('in__')
        else:
            self.send_event('out_')
        self.et_data_assessment(self.trial)
        return True

    def handle_gaze_contingency(self):
        #Regular gaze contingency -- look for a while at the cross
        #self.gc_result = self.gazecontingency.wait_for_fixation(self.trackstatus.gaze_data_contingency)
        #self.trackstatus.gaze_data_contingency = []
        #Infant gaze contingency - check if the infant is looking at this moment
        self.time_now = time.clock()
        if self.msg:
            self.send_event(self.msg)
            self.msg = None
            return False
        if self.check_gaze():
            self.show_next_trial(1)
            return False
        if self.time_gaze_contingency_finishes < self.time_now:
            self.show_next_trial(0)
            return False
        if self.presentation_status != 'strt':
            return False
        return True

    def delete_event(self, widget, event, data=None):
        # Change FALSE to TRUE and the main window will not be destroyed
        # with a "delete_event".
        self.close_window += 1
        if self.camera:
            #self.camera_win.video_writer.release()
            self.camera.cap.release()
        if self.conn_status is 'disconnected' or self.close_window == 3:
            return False
        return True

    def destroy(self, widget, data=None):
        self.disconnect_from_socket()
        self.eyetracker = None
        self.eyetracker_ob.disconnect_et()

        gtk.main_quit()

    def main(self):
        # All PyGTK applications must have a gtk.main(). Control ends here
        # and waits for an event to occur (like a key press or mouse event).
        gtk.gdk.threads_init()
        gtk.main()

# If the program is run directly or passed as an argument to the python
# interpreter then create a HelloWorld instance and show it
if __name__ == "__main__":
    eb = main_thread()
    eb.main()

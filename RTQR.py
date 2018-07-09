from pyzbar.pyzbar import decode
from PIL import Image, ImageTk
import cv2
import tkinter as tk
import mysql.connector
from tkinter.constants import *
import datetime
import calendar
import time

database_name = 'VBS'

def now():
    return datetime.datetime.now()
def day():
    return calendar.day_name[now().weekday()]
cnx = mysql.connector.connect(user='pma', password='YouW!llNeverGuess',host='127.0.0.1', database='VBS')
cur = cnx.cursor(buffered=True)
print("Init")
status_action = {
    0:"Signed-In",
    1:"Signed-out"}
status_short = {
    0:"In",
    1:"Out"}
opposite = {
    0: 1,
    1: 0}
class VideoCapture:
    def __init__(self, video_source=1):
        # Open the video source
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)
        # Get video source width and height
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
    def get_frame(self):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                return (ret, None)
        else:
            return (ret, None)
    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
class VBSAttendance:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.columnconfigure(0, weight=1)
        self.vid = VideoCapture()

        self.canvas = tk.Canvas(window, width = self.vid.width/3, height = self.vid.height/3)
        self.canvas.grid(row=2, column=0)

        self.last_name = ""
        self.delay = 10
        self.title = tk.Label(self.window, text="VBS Sign-in/Sign-out", font=("Arial", 40))
        self.title.grid(row=0, column=0)
        self.label = tk.Label(self.window, text="Please place the QR Code for your kid below the camera\nFor help please see Katrina B", font=("Arial", 20))
        self.label.grid(row=1, column=0)

        self.app = tk.Label(self.window)
        self.app.destroy()

        self.update()
        self.process()
        self.window.mainloop()
    def update(self):

        self.data = None
        ret, frame = self.vid.get_frame()
        if ret:
            self.photo = ImageTk.PhotoImage(image = Image.fromarray(frame))
            self.canvas.create_image(0, 0, image = self.photo, anchor = tk.NW)
        # Converts image to grayscale.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Uses PIL to convert the grayscale image into a ndary array that ZBar can understand.
        image = Image.fromarray(gray)
        d = decode(image)
        self.window.after(self.delay, self.update)
        if d: #Only return once a valid QR code is decoded
            self.data = d[0].data.decode("utf-8")
    def process(self):
        self.window.after(25, self.process)
        if self.data and self.app.winfo_exists()==0:
            who, name, group = decode_data(self.data)
            if self.last_name==name: return
            if who=="PARENT":
                self.last_name = name
                print(who, name, group)
                current_status = get_status(name, group) #To get at their status need convert iter to a single number
                print(current_status)
                #Spawn a simple window to confirm the signin/signout
                self.app = Comfirm(name, current_status, who, master=self.window)
                self.app.grid(row=3, column=0)
            elif who=="ADMIN":
                print(who)
                temp = tk.Frame()
                self.app = Admin(master=self.window)
                self.app.grid(row=3, column=0)
                self.last_name = ""
def get_status(name, group):
    cur.execute("SELECT Status FROM {} WHERE Name='{}' and Group_name='{}'".format(database_name, name, group))
    return list(cur)[0][0]
def get_kids(group):
    cur.execute("SELECT Name, Status FROM {} WHERE Group_name='{}'".format(database_name, group))
    return list(cur)
def change_status(name, who, status):
    cur.execute("UPDATE {} SET Status=%s WHERE Name=%s".format(database_name), (opposite[status], name)) #Expand later to timestamp, and store who
    cur.execute("UPDATE {} SET {}=%s WHERE Name=%s".format(database_name, day()+status_short[status]), (now().isoformat()+who, name)) #Expand later to timestamp, and store who
    cnx.commit()
def decode_data(data):
    return data.split(":")
def kill(buttons):
    for button in buttons:
        button.destroy()
class Admin(tk.Frame):
    #TODO: Make font size better and center on screen
    def __init__(self, master=None):
        super().__init__(master)
        self.grid()
        self.master = master
        self.group_names = ["Ducks", "Turtles", "Frogs", "Strainers"]
        self.quit = tk.Button(self, text="Exit", fg="red", command=self.destroy, font=("Arial", 14))
        self.quit.grid(row=100)
        self.label = tk.Label(self, text="Please select a group", font=("Arial", 10))
        self.label.grid(row=2)
        self.groups()
    #TODO: make buttons bigger
    def groups(self):
        self.group_buttons = list()
        for r, group in enumerate(self.group_names):
            self.group_buttons.append(tk.Button(master=self, text=group, command= lambda g=group:self.get_group(g), font=("Arial", 12)))
            self.group_buttons[-1].grid(row=r+3)
    def get_group(self, group):
        self.kid_buttons = list()
        print(group, get_kids(group))
        self.total_signed_in = 0
        for id, kid in enumerate(get_kids(group)):
            print(kid)
            self.kid_buttons.append(tk.Button(master=self, text="Sign-" + status_short[kid[1]] + ": " + kid[0], command= lambda n=kid[0], s=kid[1], i=id: self.changeStatus(n, s, i), font=("Arial", 10)))
            self.total_signed_in += kid[1]
            self.kid_buttons[-1].grid(row=id+3)
        self.label["text"] = "{}\nHas {} people signed in right now.".format(group, self.total_signed_in)
        self.back = tk.Button(master=self, text="Back",  fg="blue", command=self.uplevel, font=("Arial", 14))
        self.back.grid(row=99)
        kill(self.group_buttons)
        self.current_active_group = group
    def uplevel(self):
        kill(self.kid_buttons)
        self.label["text"] = "Please select a group"
        self.back.destroy()
        self.groups()
    def changeStatus(self, name, status ,id):
        change_status(name, "ADMIN", status)
        self.kid_buttons[id]["text"] = "Sign-" + status_short[opposite[status]] + ": " + name
        self.kid_buttons[id]["command"] = lambda n=name, s=opposite[status], i=id: self.changeStatus(n, s, i)
        if opposite[status] == 0:
            self.total_signed_in -= 1
        else:
            self.total_signed_in += 1
        self.label["text"] = "{}\nHas {} people signed in right now.".format(self.current_active_group, self.total_signed_in)
class Comfirm(tk.Frame):
    #TODO: Make font size better and center on screen
    def __init__(self, name, status, who, master=None):
        super().__init__(master)
        self.grid()
        self.master = master
        self.name = name
        self.status = status
        self.action = status_action[status]
        self.who = who
        self.create_widgets()
    def create_widgets(self):
        self.label = tk.Label(self, text="{} is about to be {}.  Is this correct?".format(self.name, self.action), font=("arial", 30))
        self.label.grid(row=2)
        self.label2 = tk.Label(self, text="Hit space to confirm", font=("arial", 30))
        self.label2.grid(row=6)
        self.yes = tk.Button(self, font=("arial", 30), text="YES", command=self.changeStatus, fg="green")
        self.yes.grid(row=3)
        self.yes.focus()
        self.bind('<space>', (lambda e, s=self: s.changeStatus()))
        self.quit = tk.Button(self, text="NO", fg="red", command=self.destroy, font=("arial", 30))
        self.quit.grid(row=4)
    def changeStatus(self):
        change_status(self.name, self.who, self.status)
        self.destroy()

VBSAttendance(tk.Tk(), "VBS")
cur.close()
cnx.close()

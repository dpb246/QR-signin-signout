from pyzbar.pyzbar import decode
from PIL import Image
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
cnx = mysql.connector.connect(user='pma', password='YouW!llNeverGuess',host='127.0.0.1', database='VBSTesting')
cur = cnx.cursor(buffered=True)

print("Init")
status_action = {
    0:"Signed-In",
    1:"Signed-out"
}
status_short = {
    0:"In",
    1:"Out"
}
opposite = {
    0: 1,
    1: 0
}
def waitAndDecode(capture):
    """
    A simple function that captures webcam video utilizing OpenCV. The video is then broken down into frames which
    are constantly displayed. The frame is then converted to grayscale for better contrast. Afterwards, the image
    is transformed into a numpy array using PIL. This is needed to create zbar image. This zbar image is then scanned
    utilizing zbar's image scanner and will then return the decodeed message of any QR or bar code.
    :return:
    """
    # Begin capturing video. You can modify what video source to use with VideoCapture's argument. It's currently set
    # to be your webcam.
    while True:
        # To quit this program press q.
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        # Breaks down the video into frames
        ret, frame = capture.read()
        # Displays the current frame
        cv2.imshow('Current', frame)
        # Converts image to grayscale.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Uses PIL to convert the grayscale image into a ndary array that ZBar can understand.
        image = Image.fromarray(gray)
        d = decode(image)
        if d: #Only return once a valid QR code is decoded
            return d[0].data.decode("utf-8")
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
def main():
    capture = cv2.VideoCapture(0)
    last_name = "" #don't want to get spammed with the current
    Admin_last_frame = False #Sketchy
    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'): #'q' to exit program
            break
        data = waitAndDecode(capture)
        who, name, group = decode_data(data)
        if last_name==name: continue
        if who=="PARENT":
            last_name = name
            print(who, name, group)
            current_status = get_status(name, group) #To get at their status need convert iter to a single number
            print(current_status)
            #Spawn a simple window to confirm the signin/signout
            root = tk.Tk()
            app = Comfirm(name, current_status, who, master=root)
            app.mainloop()
            Admin_last_frame = False
        elif who=="ADMIN" and not Admin_last_frame:
            Admin_last_frame = True
            print(who)
            root = tk.Tk()
            app = Admin(master=root)
            app.mainloop()
            last_name = ""
        else:
            Admin_last_frame = False

    #Close everything
    cur.close()
    cnx.close()
    capture.release()
def kill(buttons):
    for button in buttons:
        button.destroy()
class Admin(tk.Frame):
    #TODO: Make font size better and center on screen
    def __init__(self, master=None):
        super().__init__(master)
        self.master.geometry("500x500")
        self.master.resizable(0, 0)
        self.pack(fill="both")
        self.master = master
        self.group_names = ["Ducks", "Turtles", "Frogs"]
        self.quit = tk.Button(self, text="Exit", fg="red", command=self.master.destroy)
        self.quit.pack(side="bottom")
        self.label = tk.Label(self)
        self.label.pack(fill=X, expand=1)
        self.label["text"] = "Please select a group"
        self.groups()
    #TODO: make buttons bigger
    def groups(self):
        self.group_buttons = list()
        for group in self.group_names:
            self.group_buttons.append(tk.Button(master=self, text=group, command= lambda g=group:self.get_group(g)))
            self.group_buttons[-1].pack(side="top")
    def get_group(self, group):
        self.kid_buttons = list()
        print(group, get_kids(group))
        self.total_signed_in = 0
        for id, kid in enumerate(get_kids(group)):
            print(kid)
            self.kid_buttons.append(tk.Button(master=self, text="Sign-" + status_short[kid[1]] + ": " + kid[0], command= lambda n=kid[0], s=kid[1], i=id: self.changeStatus(n, s, i)))
            self.total_signed_in += kid[1]
            self.kid_buttons[-1].pack(side="top")
        self.label["text"] = "{}\nHas {} people signed in right now.".format(group, self.total_signed_in)
        self.back = tk.Button(master=self, text="Back",  fg="blue", command=self.uplevel)
        self.back.pack(side="bottom")
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
        self.master.geometry("500x500")
        self.master.resizable(0, 0)
        self.pack(fill="both")
        self.master = master
        self.name = name
        self.status = status
        self.action = status_action[status]
        self.who = who
        self.create_widgets()
    #TODO: make buttons bigger
    def create_widgets(self):
        self.label = tk.Label(self, text="{} is about to be {}.  Is this correct?".format(self.name, self.action))
        self.label.pack(fill=X, expand=1)
        self.yes = tk.Button(self)
        self.yes["text"] = "YES"
        self.yes["command"] = self.changeStatus
        self.yes.pack(side="top")
        self.yes.focus()
        self.quit = tk.Button(self, text="NO", fg="red", command=self.master.destroy)
        self.quit.pack(side="bottom")
    def changeStatus(self):
        change_status(self.name, self.who, self.status)
        self.master.destroy()

main()

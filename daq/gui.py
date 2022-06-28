#!/usr/bin/env python3
import tkinter
import customtkinter
import os
import subprocess
import datetime
import time



#use_current_time = "no"

customtkinter.set_appearance_mode("Dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green



app = customtkinter.CTk()  # create CTk window like you do with the Tk window
app.geometry("576x288")
app.title("Today's Data")

    
def stop():
    proc.terminate()
    print("Data collected halted!")
    start_button.configure(state=tkinter.NORMAL)


def start():
    
    global proc
    start_button.configure(state=tkinter.DISABLED)
    stop_button.configure(state=tkinter.NORMAL)
    
    user = customtkinter.CTkEntry.get(uName)
    sLocation = customtkinter.CTkEntry.get(locName)
    trial = customtkinter.CTkEntry.get(tName)
    date = customtkinter.CTkEntry.get(dName)
    time = customtkinter.CTkEntry.get(curTime)
    tDay = combobox.get()
    #make sure the location does not have spaces
    location = sLocation.replace(" ", "-")
    date = date.replace("/", ".")
    directory = user+"_"+location+"_"+date+"_"+trial+"_"+time+"_"+tDay
    print(directory)
    
    #set the time
    #sudo date -s "2006-08-14T02:34:56"
    #change the month to have 2
    month, day, year = date.split(".")
    
    if(len(month) == 1):
        month= "0"+month
    
    if(len(day) ==1):
        day = "0"+day
    
    if(len(year) == 2):
        "20"+year


    hour, minute = time.split(":")
    #we needed to add the seconds onto the time
    if(tDay == "pm"):
        if(hour != "12"):
            t = int(hour)+12
            hour = str(t)
            print("hour is "+hour)
            time = hour+":"+minute
        
    if(len(hour) == 1):
        time = "0"+hour+":"+minute
        print("time is "+time)
        
    time = time+":00"
    change_date = "sudo date -s \""+year+"-"+month+"-"+day+"T"+time+"\""
    os.system(change_date)
    
    #creating a directory to store the data. This should only happen once
    home_name = os.path.expanduser('~')
    data_directory = home_name+'/data'
    if((os.path.isdir(data_directory)) == False):
        os.mkdir(data_directory, mode = 0o1777)
        print("Directory '% s' is built!" % data_directory)
    else:
        print("file already exists")
      
    main_dir = data_directory+'/'+directory
    if(os.path.isdir(main_dir) == False):
        os.mkdir(main_dir, mode = 0o1777)
        print("Directory '% s' is built!" % main_dir)
    else:
        err = customtkinter.CTk()  # create CTk window like you do with the Tk window
        err.geometry("576x288")
        err.title("ERROR")
        label = customtkinter.CTkLabel(master=err,
                               text="File "+main_dir+" already exists.",
                               text_font = 28,
                                width=100,
                               height=25,
                               fg_color=("gray", "red"),
                               corner_radius=5)
        label.place(relx=0.3, rely=0.2, anchor=tkinter.W)
        label = customtkinter.CTkLabel(master=err,
                               text="Change the time and trial number before clicking start.",
                               text_font = 28,
                                width=100,
                               height=25,
                               fg_color=("gray", "red"),
                               corner_radius=5)
        label.place(relx=0.1, rely=0.4, anchor=tkinter.W)
        start_button.configure(state=tkinter.NORMAL)
        stop_button.configure(state=tkinter.DISABLED)
        return
    
    
    
    print("did not work")
    dirsUse = str(data_directory)+'/'+str(directory)
    print(dirsUse)

    
    
    print("saving the new parameters")
    print(freq_i_in)
    #freq_i
    #freq_f
    #int_time
    #nint
     #(customtkinter.CTkEntry.get(freq_i_in), customtkinter.CTkEntry.get(freq_f_in), customtkinter.CTkEntry.get(int_time_in), )
    freq_i = customtkinter.CTkEntry.get(freq_i_in)
    freq_f = customtkinter.CTkEntry.get(freq_f_in)
    int_time = customtkinter.CTkEntry.get(int_time_in)
    nint = customtkinter.CTkEntry.get(nint_in)
    if not freq_i:
        freq_i = "1419"
    if not freq_f:
        freq_f = "1419.2"
        
    if not int_time:
        int_time = "0.5"
        
    if not nint:
        nint = "100"
        
    
    print(freq_i)
    
    sCopy = 'python freq_and_time_scan.py --freq_i='+freq_i+' --freq_f='+freq_f+' --int_time='+int_time+' --nint='+nint+' --data_dir='+dirsUse

    
    sCopy = sCopy.split(' ')
    proc = subprocess.Popen(sCopy)


## writing to the file - file_Object = open("file_Name","mode")

def combobox_callback(choice):
    print("combobox dropdown clicked:", choice)

    
def current_date_time():
    current_time = datetime.datetime.now()
    
    dName.configure(state=tkinter.NORMAL)
    curTime.configure(state=tkinter.NORMAL)
    combobox.configure(state=tkinter.NORMAL)
    
    if (system_date_time_switch.get() == "on"):
        date_entry = str(current_time.month)+"."+str(current_time.day)+"."+str(current_time.year)
        time_day_hour = current_time.hour
        if(time_day_hour >= 12):
            if(time_day_hour > 12): 
                time_day_hour = time_day_hour - 12
                combobox.set("pm")
            else:
                combobox.set("pm")
            
        time_entry = str(time_day_hour)+":"+str(current_time.minute)
        
        dName.configure(textvariable= date_entry)
        dName.clear_placeholder()
        dName.placeholder_text = date_entry
        dName.set_placeholder()
        curTime.configure(textvariable= time_entry)
        curTime.clear_placeholder()
        curTime.placeholder_text = time_entry
        curTime.set_placeholder()
        
        
        
        dName.configure(state=tkinter.DISABLED)
        curTime.configure(state=tkinter.DISABLED)
        combobox.configure(state=tkinter.DISABLED)
        
        app.after(10000, current_date_time)
       
    print("switch toggled, current value:", system_date_time_switch.get())
    if (system_date_time_switch.get() == "off"):
        dName.configure(state=tkinter.NORMAL)
        curTime.configure(state=tkinter.NORMAL)
        combobox.configure(state=tkinter.NORMAL)
        
    print("The attributes of now() are :")
    
    print("Year :", current_time.year)
 
    print("Month : ", current_time.month)
 
    print("Day : ", current_time.day)
 
    print("Hour : ", current_time.hour)
 
    print("Minute : ", current_time.minute)

label = customtkinter.CTkLabel(master=app,
                               text="Initial Frequency:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.1, rely=0.26, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

freq_i_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="1419",
                               width=60,
                               height=25,
                               border_width=2,
                               corner_radius=10)
freq_i_in.place(relx=0.3, rely=0.26, anchor=tkinter.W)
    
label = customtkinter.CTkLabel(master=app,
                               text="Final Frequency:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.1, rely=0.36, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

freq_f_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="1419.2",
                               width=60,
                               height=25,
                               border_width=2,
                               corner_radius=10)
freq_f_in.place(relx=0.3, rely=0.36, anchor=tkinter.W)
    
label = customtkinter.CTkLabel(master=app,
                               text="Integration Time:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.1, rely=0.46, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

int_time_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="0.5",
                               width=60,
                               height=25,
                               border_width=2,
                               corner_radius=10)
int_time_in.place(relx=0.3, rely=0.46, anchor=tkinter.W)
    
label = customtkinter.CTkLabel(master=app,
                               text="Number of Integrations:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.07, rely=0.56, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

nint_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="100",
                               width=60,
                               height=25,
                               border_width=2,
                               corner_radius=10)
nint_in.place(relx=0.34, rely=0.56, anchor=tkinter.W)
    
    
    #saving = ((customtkinter.CTkEntry.get(freq_i_in)), (customtkinter.CTkEntry.get(freq_f_in)), (customtkinter.CTkEntry.get(int_time_in)), (customtkinter.CTkEntry.get(nint_in)))
#button = customtkinter.CTkButton(master=app, text="Save", command=save)
#button.place(relx=0.5, rely=.8, anchor=tkinter.CENTER)


# Use CTkButton instead of tkinter Button
start_button = customtkinter.CTkButton(master=app, text="Start", command=start)
start_button.place(relx=0.5, rely=.8, anchor=tkinter.CENTER)
start_button.configure(state=tkinter.NORMAL)


stop_button = customtkinter.CTkButton(master=app, text="Stop", command=stop)
stop_button.place(relx=0.5, rely=.9, anchor=tkinter.CENTER)
stop_button.configure(state=tkinter.DISABLED)
#start with it dissabled so you cannot click stop before start


label = customtkinter.CTkLabel(master=app,
                               text="Username:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.1, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

uName = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
uName.place(relx=0.7, rely=0.1, anchor=tkinter.W)



label = customtkinter.CTkLabel(master=app,
                               text="Location:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.2, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

locName = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
locName.place(relx=0.7, rely=0.2, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Trial:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.3, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

tName = customtkinter.CTkEntry(master=app,
                               placeholder_text="00",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
tName.place(relx=0.7, rely=0.3, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Date:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.4, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

dName = customtkinter.CTkEntry(master=app,
                               placeholder_text="MM.DD.YYYY",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
dName.place(relx=0.7, rely=0.4, anchor=tkinter.W)





label = customtkinter.CTkLabel(master=app,
                               text="Time:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.5, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

curTime = customtkinter.CTkEntry(master=app,
                               placeholder_text="00:00",
                               width=60,
                               height=25,
                               border_width=2,
                               corner_radius=10)
curTime.place(relx=0.7, rely=0.5, anchor=tkinter.W)



combobox = customtkinter.CTkComboBox(master=app,
                                     values=["am", "pm"],
                                     command=combobox_callback, height = 25, width = 55, variable = "")
combobox.pack(padx=5, pady=5)
combobox.set("am")  # set initial value
combobox.place(relx=0.81, rely=0.5, anchor=tkinter.W)

system_date_time_switch = customtkinter.CTkSwitch(master=app, text="use system date and time", command=current_date_time, onvalue="on", offvalue="off")
system_date_time_switch.pack(padx=20, pady=10)
system_date_time_switch.place(relx=0.7, rely=.6, anchor=tkinter.CENTER)

app.mainloop()
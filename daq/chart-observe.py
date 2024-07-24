#!/usr/bin/python3
import tkinter #you do need tkinter and customtkinter
import customtkinter
import os #this allows you to use the command line to change the date
import subprocess #this allows you to run and stop the program without using os
import datetime #this allows you to get the system date and time
import time #this allows you to use "after" to call the date_time method and update the date and time
import glob #for compressing the zip files to import into jupyter hub
import shutil
import webbrowser
from tkinter import messagebox

customtkinter.set_appearance_mode("Light")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green

#create CTk window like you do with the Tk window
app = customtkinter.CTk()
app.geometry("786x480")
app.title("Today's Data")
customtkinter.set_widget_scaling(1.1)

global biasT
biasT = False
global proc
#the stop method from the stop_button allows you to stop the program running
def stop():
    global proc
    proc.terminate()
    print("Data collection halted!")
    start_button.configure(state=tkinter.NORMAL)
    stop_button.configure(state=tkinter.DISABLED)
    del proc



#the start method from the start_button allows you to run the program
    #it runs the method current_date_time to make sure that they are using the correct time
    #disables the start_button so that you cannot start twice and enables the stop_button
    #creates the directory data and a new directory from their input
    #does not allow a creation of the same directory so there is an error window
    #uses the papameters entered to take data or uses the default shown on the gui
    #runs the program with the directory created
def start():
    #global variables that also align with the method current_date_time
    global proc
    global date
    global time
    global data_directory
    global directory
    global biasT

    create_zip()
    #this is the call to the method so that even after the second start it can check the time and date correctly if system time is used
    current_date_time()

    #diabled start so that the user cannot click start twice and they can now click stop
    start_button.configure(state=tkinter.DISABLED)
    stop_button.configure(state=tkinter.NORMAL)

    #the variables taken from the entry inputs
    sUser = customtkinter.CTkEntry.get(user_name)
    sLocation = customtkinter.CTkEntry.get(location_name)
    trial = customtkinter.CTkEntry.get(time_name)
    date_name.configure(state=tkinter.NORMAL)

    #checking if date was empty so that it knows to use the input from entry or the one from the system time and date
    if (system_date_time_switch.get() == "off"):
        date = customtkinter.CTkEntry.get(date_name)
        time = customtkinter.CTkEntry.get(curr_time)

    #checking for empty trials
    if not trial:
        trial = '1'


    tDay = combobox.get()
    #make sure the location does not have spaces or slashes that many people accidentally do
    location = sLocation.replace(" ", "-")
    date = date.replace("/", ".")
    user = sUser.replace("_", ".")

    #set the time
    #the format to chang the date and time = sudo date -s "2006-08-14T02:34:56"
    #change the month to have 2
    month, day, year = date.split(".")

    date_y_m_d = year+"."+month+"."+day

    #changed the date to be the correct formal
    directory = user+"_"+location+"_"+date_y_m_d+"_"+trial+"_"+time.replace(":", ".")+"_"+tDay
    print(directory)

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
    #making sure there is a 0 if the hour is a signle digit to be the correct format
    if(len(hour) == 1):
        time = "0"+hour+":"+minute
        print("time is "+time)

    #adding seconds
    time = time+":00"
    change_date = "sudo date -s \""+year+"-"+month+"-"+day+"T"+time+"\""
    os.system(change_date)

    #creating a directory called data to store the data. This only happens once
    home_name = os.path.expanduser('~')
    data_directory = home_name+'/data'

    #checking to see if the directory data exists and if it does then nothing happens
    if((os.path.isdir(data_directory)) == False):
        os.mkdir(data_directory, mode = 0o1777)
        print("Directory '% s' is built!" % data_directory)
    else:
        print("directory data already exists")

    #this is the main direcotry
    main_dir = data_directory+'/'+directory

    #check if the directory does not exists made from the users input
    if(os.path.isdir(main_dir) == False):
        os.mkdir(main_dir, mode = 0o1777)
        print("Directory '% s' is built!" % main_dir)
    else:
        # create error window to show that there was an error when they did not change the inputs so they know what to change
        messagebox.showerror('ERROR', 'File already exists.\nChange the time and/or trial number before clicking start.')

        #allow for the start button to be clicked because then they can change the trial number and continue
        start_button.configure(state=tkinter.NORMAL)
        stop_button.configure(state=tkinter.DISABLED)
        #returns so that the files do not write to that old diecotry
        return


    #getting the directory to be used
    use_directory = str(data_directory)+'/'+str(directory)
    print("directory being used: "+use_directory)


    freq_i = customtkinter.CTkEntry.get(freq_i_in)
    freq_f = customtkinter.CTkEntry.get(freq_f_in)
    int_time = customtkinter.CTkEntry.get(int_time_in)
    nint = customtkinter.CTkEntry.get(nint_in)

    #checking each parameter to see if anyone entered a variable or if the default numbers should be used
    if not freq_i:
        freq_i = "1390"

    if not freq_f:
        freq_f = "1450"

    if not int_time:
        int_time = "0.5"

    if not nint:
        nint = "20"

    if biasT:
        copy_command = 'freq_and_time_scan.py --freq_i='+freq_i+' --freq_f='+freq_f+' --int_time='+int_time+' --nint='+nint+' --data_dir='+use_directory+' --biasT=True'
    else:
        copy_command = 'freq_and_time_scan.py --freq_i='+freq_i+' --freq_f='+freq_f+' --int_time='+int_time+' --nint='+nint+' --data_dir='+use_directory

    copy_command = copy_command.split(' ')

    proc = subprocess.Popen(copy_command)


#the method default_parameters allows the user to use the default parameters set
    #they can either enter new parameters or they can use what is already displayed in the entry
    #the entry is disabled when they chose to use the default
def default_parameters():
    print("using default parameters")
    freq_i_in.configure(state=tkinter.NORMAL)
    freq_f_in.configure(state=tkinter.NORMAL)
    int_time_in.configure(state=tkinter.NORMAL)
    nint_in.configure(state=tkinter.NORMAL)
    if (default_parameters_switch.get() == "on"):
        freq_i_in.configure(state=tkinter.DISABLED)
        freq_f_in.configure(state=tkinter.DISABLED)
        int_time_in.configure(state=tkinter.DISABLED)
        nint_in.configure(state=tkinter.DISABLED)



#the method current_date_time from the switch system_date_time_switch
    #gets the system time if the switch is on and disables the entry boxes for date, time, and time of day(am/pm)
    #the method after being called once runs every 10000 miliseconds to update the time and show the correct system time on the gui if the switch is on
    #saves the date and time in a global variable so that it can be used in the start metod to create a directory
def current_date_time():
    current_time = datetime.datetime.now()
    #you have to set them to normal and then change them
    date_name.configure(state=tkinter.NORMAL)
    curr_time.configure(state=tkinter.NORMAL)
    combobox.configure(state=tkinter.NORMAL)

    if (system_date_time_switch.get() == "on"):
        date_entry = str(current_time.month)+"."+str(current_time.day)+"."+str(current_time.year)
        time_day_hour = current_time.hour
        #sets the time of day to pm when it is 12 or after 12 and corrects for mulitary time
        if(time_day_hour >= 12):
            if(time_day_hour > 12):
                time_day_hour = time_day_hour - 12
                combobox.set("pm")
            else:
                combobox.set("pm")

        min_entry = str(current_time.minute)
        #makes sure there is a 0 when there is a minute before 10 like 2 - 02
        if (len(min_entry) == 1):
            min_entry = "0"+min_entry
        #adds the times togethere including the :
        time_entry = str(time_day_hour)+":"+min_entry
        #print("This is the date entry: "+date_entry)
        #print("This is the time entry: "+time_entry)
        date_name.configure(textvariable=date_entry)

        #global date and time to use in the start method
        global date
        date = date_entry
        global time
        time = time_entry

        #setting the placeholders so that the user knows what time and date is being used
        date_name.clear_placeholder()
        date_name.placeholder_text = date_entry
        date_name.set_placeholder()
        curr_time.clear_placeholder()
        curr_time.placeholder_text = time_entry
        curr_time.set_placeholder()


        #disable the entry so that they cannot enter a different date and time
        date_name.configure(state=tkinter.DISABLED)
        curr_time.configure(state=tkinter.DISABLED)
        combobox.configure(state=tkinter.DISABLED)
        #this calls the method after 10000 miliseconds to check the time is correct
        app.after(10000, current_date_time)

    #print("switch toggled, current value:", system_date_time_switch.get())

    if (system_date_time_switch.get() == "off"):
        date_name.configure(state=tkinter.NORMAL)
        curr_time.configure(state=tkinter.NORMAL)
        combobox.configure(state=tkinter.NORMAL)
    #below you can uncomment and use the print statements to make sure the correct date and time are being used
    #print("The attributes of now() are :")
    #print("Year :", current_time.year)
    #print("Month : ", current_time.month)
    #print("Day : ", current_time.day)
    #print("Hour : ", current_time.hour)
    #print("Minute : ", current_time.minute)

def create_zip():
    global proc
    global data_direcotry
    global direcotry
    app.after(10000, create_zip)
    try:
        if proc.poll() is not None and proc.poll() == 0:
            print("creating text file")
            desc = customtkinter.CTkEntry.get(description)
            with open(data_directory+'/'+directory+'/description.txt', 'w') as f:
                f.write(desc)
            print("Creating zip file")
            home_name = os.path.expanduser('~')
            shutil.make_archive(data_directory+'/'+directory, "zip", data_directory, directory)
            print("done")
            stop()
    except NameError:
        pass


def open_jupyter():
    webbrowser.open_new('https://radiolab.winona.edu/')

def open_local_jupyter():
    os.system('jupyter notebook --notebook-dir=~')

def biasT_switch():
    global biasT
    biasT = False
    if (biasT_switch.get() == "on"):
        biasT = True
        messagebox.showwarning('WARNING', 'Only have this on if you know FOR SURE the BIAS-T is being used. \nIf the Bias-T is NOT connected to your radio, this option WILL BREAK your radio')

        return

#change the display to be able to see better
def mode():
    if (mode_switch.get() == "on"):
        customtkinter.set_appearance_mode("Dark")
    else:
        customtkinter.set_appearance_mode("Light")



mode_switch = customtkinter.CTkSwitch(master=app, text="Dark Mode", command=mode, onvalue="on", offvalue="off")
mode_switch.pack(padx=20, pady=10)
mode_switch.place(relx=0.1, rely=.03, anchor=tkinter.CENTER)

#this is the start of the gui design where everything is layed out
label = customtkinter.CTkLabel(master=app,
                               text="Initial Frequency:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=8)

label.place(relx=0.1, rely=0.1, anchor=tkinter.W)

freq_i_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="1390",
                               width=80,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

freq_i_in.place(relx=0.3, rely=0.1, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Final Frequency:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.1, rely=0.2, anchor=tkinter.W)

freq_f_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="1450",
                               width=80,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

freq_f_in.place(relx=0.3, rely=0.2, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Integration Time:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.1, rely=0.3, anchor=tkinter.W)

int_time_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="0.5",
                               width=80,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

int_time_in.place(relx=0.3, rely=0.3, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Number of Integrations:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.07, rely=0.4, anchor=tkinter.W)

nint_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="20",
                               width=80,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

nint_in.place(relx=0.34, rely=0.4, anchor=tkinter.W)

default_parameters_switch = customtkinter.CTkSwitch(master=app, text="Use Default Parameters", command=default_parameters, onvalue="on", offvalue="off")
default_parameters_switch.pack(padx=20, pady=10)
default_parameters_switch.place(relx=0.25, rely=.5, anchor=tkinter.CENTER)

biasT_switch = customtkinter.CTkSwitch(master=app, text="Enable Bias-T", command=biasT_switch, onvalue="on", offvalue="off")
biasT_switch.pack(padx=20, pady=10)
biasT_switch.place(relx=0.25, rely=.57, anchor=tkinter.CENTER)

description = customtkinter.CTkEntry(master=app,
                               placeholder_text="Describe what you are looking at.",
                               width=310,
                               height=30,
                               border_width=2,
                               corner_radius=10
                               )

description.place(relx=0.05, rely=0.67, anchor=tkinter.W)


#below is the right side layout in the GUI
start_button = customtkinter.CTkButton(master=app, text="Start", command=start)
start_button.place(relx=0.5, rely=.8, anchor=tkinter.CENTER)
start_button.configure(state=tkinter.NORMAL)


stop_button = customtkinter.CTkButton(master=app, text="Stop", command=stop)
stop_button.place(relx=0.5, rely=.9, anchor=tkinter.CENTER)
stop_button.configure(state=tkinter.DISABLED)
#start with stop disabled so you cannot click stop before start

jupyter_button = customtkinter.CTkButton(master=app, text="Open Jupyter Hub to Upload", command=open_jupyter)
jupyter_button.place(relx=0.8, rely=.8, anchor=tkinter.CENTER)
jupyter_button.configure(state=tkinter.NORMAL)

local_jupyter_button = customtkinter.CTkButton(master=app, text="Open LOCAL Jupyter Notebook", command=open_local_jupyter)
local_jupyter_button.place(relx=0.8, rely=.9, anchor=tkinter.CENTER)
local_jupyter_button.configure(state=tkinter.NORMAL)

label = customtkinter.CTkLabel(master=app,
                               text="Username:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.5, rely=0.1, anchor=tkinter.W)

user_name = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=210,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

user_name.place(relx=0.7, rely=0.1, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Location:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.5, rely=0.2, anchor=tkinter.W)

location_name = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=210,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

location_name.place(relx=0.7, rely=0.2, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Trial:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius= 5
                               )

label.place(relx=0.5, rely=0.3, anchor=tkinter.W)

time_name = customtkinter.CTkEntry(master=app,
                               placeholder_text="00",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

time_name.place(relx=0.7, rely=0.3, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Date:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.5, rely=0.4, anchor=tkinter.W)

date_name = customtkinter.CTkEntry(master=app,
                               placeholder_text="MM.DD.YYYY",
                               width=150,
                               height=25,
                               border_width=2,
                               corner_radius=10
                               )

date_name.place(relx=0.7, rely=0.4, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Time:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5
                               )

label.place(relx=0.5, rely=0.5, anchor=tkinter.W)

curr_time = customtkinter.CTkEntry(master=app,
                               placeholder_text="00:00",
                               width=70,
                               height=25,
                               border_width=2,
                               corner_radius=10
                              )

curr_time.place(relx=0.7, rely=0.5, anchor=tkinter.W)

combobox = customtkinter.CTkComboBox(master=app,
                                     values=["am", "pm"],
                                     height = 25, width = 55, variable = "")
combobox.pack(padx=5, pady=5)
combobox.set("am")  # set initial value
combobox.place(relx=0.81, rely=0.5, anchor=tkinter.W)

#here are the two switches at the bottom of each side. You can view the location with relx and rely
system_date_time_switch = customtkinter.CTkSwitch(master=app, text="Use System Date and Time", command=current_date_time, onvalue="on", offvalue="off")
system_date_time_switch.pack(padx=20, pady=10)
system_date_time_switch.place(relx=0.7, rely=.6, anchor=tkinter.CENTER)

app.mainloop()

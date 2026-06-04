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
app.title("CHART Data Collection")
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
    sLongitude = customtkinter.CTkEntry.get(longitude_name) #getting the longitude from the entry
    sLatitude = customtkinter.CTkEntry.get(latitude_name)  #getting the latitude from the entry
    date_name.configure(state=tkinter.NORMAL)

    #checking if date was empty so that it knows to use the input from entry or the one from the system time and date
    if (system_date_time_switch.get() == "off"):
        date = customtkinter.CTkEntry.get(date_name)
        time = customtkinter.CTkEntry.get(curr_time)

    tDay = combobox.get()
    #make sure the location does not have spaces or slashes that many people accidentally do
    date = date.replace("/", ".")
    user = sUser.replace("_", ".")

    #set the time
    #the format to chang the date and time = sudo date -s "2006-08-14T02:34:56"
    #change the month to have 2
    month, day, year = date.split(".")

    date_y_m_d = year+"."+month+"."+day

    # New format without location and with latitude and longitude
    # I used f strings here for clarity
    directory = f"{user}_lon{sLongitude}_lat{sLatitude}_{date_y_m_d}_{time.replace(':', '.')}_{tDay}"
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
        freq_i = default_freq_i

    if not freq_f:
        freq_f = default_freq_f

    if not int_time:
        int_time = default_int_time

    if not nint:
        nint = default_nint

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

default_freq_i = '1415'
default_freq_f = '1425'
default_int_time = '5'
default_nint = '10'

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
        messagebox.showwarning('WARNING', 'Only have this on if you know FOR SURE the BIAS-T is being used. \nIf you are following the CHART tutorial with the recommended LNA, it should be ON')

        return

#change the display to be able to see better
def mode():
    if (mode_switch.get() == "on"):
        customtkinter.set_appearance_mode("Dark")
    else:
        customtkinter.set_appearance_mode("Light")


# below is the layout in the GUI
mode_switch = customtkinter.CTkSwitch(master=app, text="Dark Mode", command=mode, onvalue="on", offvalue="off")
mode_switch.pack(padx=20, pady=(10, 0), anchor="w")

# Scrollable Frame for all widgets
scroll_frame = customtkinter.CTkScrollableFrame(master=app, width=760, height=440)
scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Configure flexible grid layout
for i in range(12):
    scroll_frame.rowconfigure(i, weight=1)
for j in range(2):
    scroll_frame.columnconfigure(j, weight=1)

# Store references to all fields for responsive layout
responsive_widgets = []

# === Input Fields (Adaptive Grid) ===

# Row 0 — Username
label_user = customtkinter.CTkLabel(scroll_frame, text="Username:")
label_user.grid(row=0, column=0, sticky="w", padx=10, pady=10)
user_name = customtkinter.CTkEntry(scroll_frame, placeholder_text="Enter Here", width=180)
user_name.grid(row=0, column=1, sticky="w", padx=10, pady=10)

# Row 0 (right side) — Longitude
label_long = customtkinter.CTkLabel(scroll_frame, text="Longitude:")
label_long.grid(row=0, column=2, sticky="w", padx=10, pady=10)
longitude_name = customtkinter.CTkEntry(scroll_frame, placeholder_text="e.g., -91.64", width=120)
longitude_name.grid(row=0, column=3, sticky="w", padx=10, pady=10)

# Row 1 — Latitude
label_lat = customtkinter.CTkLabel(scroll_frame, text="Latitude:")
label_lat.grid(row=1, column=0, sticky="w", padx=10, pady=10)
latitude_name = customtkinter.CTkEntry(scroll_frame, placeholder_text="e.g., 44.05", width=120)
latitude_name.grid(row=1, column=1, sticky="w", padx=10, pady=10)

# Row 1 (right side) — Date
label_date = customtkinter.CTkLabel(scroll_frame, text="Date:")
label_date.grid(row=1, column=2, sticky="w", padx=10, pady=10)
date_name = customtkinter.CTkEntry(scroll_frame, placeholder_text="MM.DD.YYYY", width=120)
date_name.grid(row=1, column=3, sticky="w", padx=10, pady=10)

# Row 2 — Time + AM/PM combo
label_time = customtkinter.CTkLabel(scroll_frame, text="Time:")
label_time.grid(row=2, column=0, sticky="w", padx=10, pady=10)
time_frame = customtkinter.CTkFrame(scroll_frame)
time_frame.grid(row=2, column=1, sticky="w", padx=10, pady=10)
curr_time = customtkinter.CTkEntry(time_frame, placeholder_text="00:00", width=80)
curr_time.grid(row=0, column=0, sticky="w", padx=(0, 5))
combobox = customtkinter.CTkComboBox(time_frame, values=["am", "pm"], width=60)
combobox.grid(row=0, column=1)
combobox.set("am")

# Row 2 (right side) — Initial Frequency
label_freq_i = customtkinter.CTkLabel(scroll_frame, text="Initial Frequency (MHz):")
label_freq_i.grid(row=2, column=2, sticky="w", padx=10, pady=10)
freq_i_in = customtkinter.CTkEntry(scroll_frame, placeholder_text="1415", width=100)
freq_i_in.grid(row=2, column=3, sticky="w", padx=10, pady=10)

# Row 3 — Final Frequency
label_freq_f = customtkinter.CTkLabel(scroll_frame, text="Final Frequency (MHz):")
label_freq_f.grid(row=3, column=0, sticky="w", padx=10, pady=10)
freq_f_in = customtkinter.CTkEntry(scroll_frame, placeholder_text="1425", width=100)
freq_f_in.grid(row=3, column=1, sticky="w", padx=10, pady=10)

# Row 3 (right side) — Integration Time
label_int_time = customtkinter.CTkLabel(scroll_frame, text="Integration Time (s):")
label_int_time.grid(row=3, column=2, sticky="w", padx=10, pady=10)
int_time_in = customtkinter.CTkEntry(scroll_frame, placeholder_text="5", width=100)
int_time_in.grid(row=3, column=3, sticky="w", padx=10, pady=10)

# Row 4 — Number of Integrations
label_nint = customtkinter.CTkLabel(scroll_frame, text="Number of Integrations:")
label_nint.grid(row=4, column=0, sticky="w", padx=10, pady=10)
nint_in = customtkinter.CTkEntry(scroll_frame, placeholder_text="10", width=100)
nint_in.grid(row=4, column=1, sticky="w", padx=10, pady=10)

# Row 4 (right side) — Description
label_desc = customtkinter.CTkLabel(scroll_frame, text="Description:")
label_desc.grid(row=4, column=2, sticky="w", padx=10, pady=10)
description = customtkinter.CTkEntry(scroll_frame, placeholder_text="Describe observation", width=280)
description.grid(row=4, column=3, sticky="w", padx=10, pady=10)

# Fix minimum label widths so text never disappears
MIN_LABEL_WIDTH = 150

all_labels = [
    label_user, label_long, label_lat, label_date, label_time,
    label_freq_i, label_freq_f, label_int_time, label_nint, label_desc
]

for lbl in all_labels:
    lbl.configure(width=MIN_LABEL_WIDTH)


# Row 5 — Switches
switch_frame = customtkinter.CTkFrame(scroll_frame)
switch_frame.grid(row=5, column=0, columnspan=4, pady=10, sticky="w")

default_parameters_switch = customtkinter.CTkSwitch(
    switch_frame,
    text="Use Default Parameters",
    command=default_parameters,
    onvalue="on",
    offvalue="off"
)

biasT_switch = customtkinter.CTkSwitch(
    switch_frame,
    text="Enable Bias-T",
    command=biasT_switch,
    onvalue="on",
    offvalue="off"
)

system_date_time_switch = customtkinter.CTkSwitch(
    switch_frame,
    text="Use System Date and Time",
    command=current_date_time,
    onvalue="on",
    offvalue="off"
)

default_parameters_switch.grid(row=0, column=0, padx=10)
biasT_switch.grid(row=0, column=1, padx=10)
system_date_time_switch.grid(row=0, column=2, padx=10)


# Row 6 — Buttons
button_frame = customtkinter.CTkFrame(scroll_frame)
button_frame.grid(row=6, column=0, columnspan=4, pady=(15, 5), sticky="w")
start_button = customtkinter.CTkButton(button_frame, text="Start", command=start)
stop_button = customtkinter.CTkButton(button_frame, text="Stop", command=stop)
jupyter_button = customtkinter.CTkButton(button_frame, text="Open Jupyter Hub", command=open_jupyter, corner_radius=0)
local_jupyter_button = customtkinter.CTkButton(button_frame, text="Open Local Jupyter", command=open_local_jupyter)
start_button.grid(row=0, column=0, padx=10)
stop_button.grid(row=0, column=1, padx=10)
jupyter_button.grid(row=0, column=2, padx=10)
local_jupyter_button.grid(row=0, column=3, padx=10)


# Enhanced hint label
active_hint_label = None
HINT_MODE = "below"   # this will dynamically switch based on window width

def add_hint_label(entry_widget, hint_text):

    global active_hint_label
    hint_label = customtkinter.CTkLabel(
        master=scroll_frame,
        text=hint_text,
        text_color="gray50",
        font=("Arial", 10)
    )
    hint_label.place_forget()

    def show_hint(event):
        global active_hint_label, HINT_MODE

        # Hide previous hint
        if active_hint_label and active_hint_label != hint_label:
            active_hint_label.place_forget()

        # Get widget coords relative to scroll_frame
        entry_x = entry_widget.winfo_x()
        entry_y = entry_widget.winfo_y()

        if HINT_MODE == "side":
            # Side placement
            hint_label.place(
                x=entry_x + entry_x/2,
                y=entry_y
            )
        else:
            # Below placement
            hint_label.place(
                x=entry_x,
                y=entry_y + entry_widget.winfo_height()/2
            )

        active_hint_label = hint_label

    def hide_hint(event):
        hint_label.place_forget()

    entry_widget.bind("<Enter>", show_hint)
    entry_widget.bind("<Leave>", hide_hint)



#here are the two switches at the bottom of each side. You can view the location with relx and rely
# system_date_time_switch = customtkinter.CTkSwitch(master=app, text="Use System Date and Time", command=current_date_time, onvalue="on", offvalue="off")
# system_date_time_switch.pack(padx=20, pady=10)
# system_date_time_switch.place(relx=0.7, rely=.6, anchor=tkinter.CENTER)

# Add hint labels for all entries with appropriate positions
# Position can be "below" or "beside" as needed
add_hint_label(user_name, "Your WSU username or observer name")
add_hint_label(longitude_name, "Longitude in decimal degrees (East/West)")
add_hint_label(latitude_name, "Latitude in decimal degrees (North/South)")
add_hint_label(date_name, "Format: MM.DD.YYYY")
add_hint_label(curr_time, "Format: HH:MM with am/pm toggle")
add_hint_label(freq_i_in, "Start frequency in MHz")
add_hint_label(freq_f_in, "End frequency in MHz")
add_hint_label(int_time_in, "Integration time in seconds")
add_hint_label(nint_in, "Number of integrations")
add_hint_label(description, "Short description of observation")

# Make window responsive
# Responsive layout: switch between 2-column and 1-column when resizing
def on_resize(event):
    width = app.winfo_width()

    # Making the hint global to adjust its position
    global HINT_MODE
    if width < 900:
        HINT_MODE = "side"
    else:
        HINT_MODE = "below"
    if width < 900:

        # Reflow input fields (already working)
        label_user.grid_configure(row=0, column=0)
        user_name.grid_configure(row=0, column=1)

        label_long.grid_configure(row=1, column=0)
        longitude_name.grid_configure(row=1, column=1)

        label_lat.grid_configure(row=2, column=0)
        latitude_name.grid_configure(row=2, column=1)

        label_date.grid_configure(row=3, column=0)
        date_name.grid_configure(row=3, column=1)

        label_time.grid_configure(row=4, column=0)
        time_frame.grid_configure(row=4, column=1)

        label_freq_i.grid_configure(row=5, column=0)
        freq_i_in.grid_configure(row=5, column=1)

        label_freq_f.grid_configure(row=6, column=0)
        freq_f_in.grid_configure(row=6, column=1)

        label_int_time.grid_configure(row=7, column=0)
        int_time_in.grid_configure(row=7, column=1)

        label_nint.grid_configure(row=8, column=0)
        nint_in.grid_configure(row=8, column=1)

        label_desc.grid_configure(row=9, column=0)
        description.grid_configure(row=9, column=1)

        switch_frame.grid_configure(row=10, column=0, columnspan=2, sticky="w", padx=10, pady=(20, 10))

        button_frame.grid_configure(row=11, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 20))
    else:

        label_user.grid_configure(row=0, column=0)
        user_name.grid_configure(row=0, column=1)

        label_long.grid_configure(row=0, column=2)
        longitude_name.grid_configure(row=0, column=3)

        label_lat.grid_configure(row=1, column=0)
        latitude_name.grid_configure(row=1, column=1)

        label_date.grid_configure(row=1, column=2)
        date_name.grid_configure(row=1, column=3)

        label_time.grid_configure(row=2, column=0)
        time_frame.grid_configure(row=2, column=1)

        label_freq_i.grid_configure(row=2, column=2)
        freq_i_in.grid_configure(row=2, column=3)

        label_freq_f.grid_configure(row=3, column=0)
        freq_f_in.grid_configure(row=3, column=1)

        label_int_time.grid_configure(row=3, column=2)
        int_time_in.grid_configure(row=3, column=3)

        label_nint.grid_configure(row=4, column=0)
        nint_in.grid_configure(row=4, column=1)

        label_desc.grid_configure(row=4, column=2)
        description.grid_configure(row=4, column=3)

        switch_frame.grid_configure(row=5, column=0, columnspan=4, sticky="w", padx=10, pady=10)

        button_frame.grid_configure(row=6, column=0, columnspan=4, sticky="w", padx=10, pady=10)

# Bind the handler
app.bind("<Configure>", on_resize)

app.rowconfigure(0, weight=1)
app.columnconfigure(0, weight=1)


app.mainloop()

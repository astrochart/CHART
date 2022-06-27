import tkinter
import customtkinter
import os
import subprocess



customtkinter.set_appearance_mode("Dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green



app = customtkinter.CTk()  # create CTk window like you do with the Tk window
app.geometry("576x288")
app.title("Today's Data")

    
def stop():
    proc.terminate()
    print("Data collected halted!")


def start():
    
    global proc
    start_button.configure(state=tkinter.DISABLED)
    stop_button.configure(state=tkinter.NORMAL)
    
    user = customtkinter.CTkEntry.get(uName)
    date = customtkinter.CTkEntry.get(dName)
    trial = customtkinter.CTkEntry.get(tName)
    sLocation = customtkinter.CTkEntry.get(locName)
    time = customtkinter.CTkEntry.get(curTime)
    tDay = combobox.get()
    #make sure the location does not have spaces
    location = sLocation.replace(" ", "_")
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
    os.mkdir(main_dir, mode = 0o1777)
    print("Directory '% s' is built!" % main_dir)
    
    dirsUse = str(data_directory)+'/'+str(directory)
    print(dirsUse)

    
    
    print("saving the new parameters")
    print(freq_i_in)
    
     #(customtkinter.CTkEntry.get(freq_i_in), customtkinter.CTkEntry.get(freq_f_in), customtkinter.CTkEntry.get(int_time_in), )
    freq_i = customtkinter.CTkEntry.get(freq_i_in)
    freq_f = customtkinter.CTkEntry.get(freq_f_in)
    int_time = customtkinter.CTkEntry.get(int_time_in)
    nint = customtkinter.CTkEntry.get(nint_in)
    
    print(freq_i)
    
    print(freq_i)
    
    sCopy = 'python freq_and_time_scan.py --freq_i='+freq_i+' --freq_f='+freq_f+' --int_time='+int_time+' --nint='+nint+' --data_dir='+dirsUse

    
    sCopy = sCopy.split(' ')
    proc = subprocess.Popen(sCopy)


## writing to the file - file_Object = open("file_Name","mode")

def combobox_callback(choice):
    print("combobox dropdown clicked:", choice)



label = customtkinter.CTkLabel(master=app,
                               text="Parameters:",
                               width=100,
                               height=25,
                               fg_color=("white", "orange"),
                               corner_radius=5)
label.place(relx=0.2, rely=0.16, anchor=tkinter.W)



label = customtkinter.CTkLabel(master=app,
                               text="Initial Frequency:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.1, rely=0.26, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

freq_i_in = customtkinter.CTkEntry(master=app,
                               placeholder_text="1390",
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
                               placeholder_text="1450",
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
                               placeholder_text="20",
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
label.place(relx=0.5, rely=0.2, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

uName = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
uName.place(relx=0.7, rely=0.2, anchor=tkinter.W)


label = customtkinter.CTkLabel(master=app,
                               text="Date:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.3, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

dName = customtkinter.CTkEntry(master=app,
                               placeholder_text="MM.DD.YYYY",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
dName.place(relx=0.7, rely=0.3, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Location:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.4, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

locName = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
locName.place(relx=0.7, rely=0.4, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Trial:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.5, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

tName = customtkinter.CTkEntry(master=app,
                               placeholder_text="00",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
tName.place(relx=0.7, rely=0.5, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Time:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.5, rely=0.6, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

curTime = customtkinter.CTkEntry(master=app,
                               placeholder_text="00:00",
                               width=60,
                               height=25,
                               border_width=2,
                               corner_radius=10)
curTime.place(relx=0.7, rely=0.6, anchor=tkinter.W)



combobox = customtkinter.CTkComboBox(master=app,
                                     values=["am", "pm"],
                                     command=combobox_callback, height = 25, width = 70, variable = "")
combobox.pack(padx=5, pady=5)
combobox.set("pm")  # set initial value
combobox.place(relx=0.81, rely=0.6, anchor=tkinter.W)


app.mainloop()
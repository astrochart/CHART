import tkinter
import customtkinter
import os



customtkinter.set_appearance_mode("Dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green

app = customtkinter.CTk()  # create CTk window like you do with the Tk window
app.geometry("576x288")
app.title("Today's Data")


def button_function():
    user = customtkinter.CTkEntry.get(uName)
    date = customtkinter.CTkEntry.get(dName)
    trial = customtkinter.CTkEntry.get(tName)
    location = customtkinter.CTkEntry.get(locName)
    time = customtkinter.CTkEntry.get(curTime)
    tDay = combobox.get()
    directory = user+"_"+location+"_"+date+"_"+trial+"_"+time+"_"+tDay
    print(directory)
    
    main_dir = directory
    os.mkdir(main_dir, mode = 0o1777)
    print("Directory '% s' is built!" % main_dir)
    
    dirsUse = '/home/winona/CHART/daq/'+str(directory)
    print(dirsUse)
   
    sCopy = 'python freq_and_time_scan.py --freq_i=1390 --freq_f=1450 --int_time=0.5 --nint=20 --data_dir='+dirsUse

    os.system(sCopy)
    
    #cmd = "python freq_and_time_scan.py --freq_i=1390 --freq_f=1450 --int_time=0.5 --nint=20 --data_dir --"+main_dir
    #os.system(cmd)    
    

## writing to the file - file_Object = open("file_Name","mode")

def combobox_callback(choice):
    print("combobox dropdown clicked:", choice)

# Use CTkButton instead of tkinter Button
button = customtkinter.CTkButton(master=app, text="Start", command=button_function)
button.place(relx=0.5, rely=.8, anchor=tkinter.CENTER)


label = customtkinter.CTkLabel(master=app,
                               text="Username:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.3, rely=0.1, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

uName = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
uName.place(relx=0.5, rely=0.1, anchor=tkinter.W)


label = customtkinter.CTkLabel(master=app,
                               text="Date:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.3, rely=0.2, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

dName = customtkinter.CTkEntry(master=app,
                               placeholder_text="MM.DD.YYYY",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
dName.place(relx=0.5, rely=0.2, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Location:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.3, rely=0.3, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

locName = customtkinter.CTkEntry(master=app,
                               placeholder_text="Enter Here",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
locName.place(relx=0.5, rely=0.3, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Trial:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.3, rely=0.4, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

tName = customtkinter.CTkEntry(master=app,
                               placeholder_text="00",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
tName.place(relx=0.5, rely=0.4, anchor=tkinter.W)

label = customtkinter.CTkLabel(master=app,
                               text="Time:",
                               width=100,
                               height=25,
                               fg_color=("white", "gray"),
                               corner_radius=5)
label.place(relx=0.3, rely=0.5, anchor=tkinter.W)
##n, ne, e, se, s, sw, w, nw, or center

curTime = customtkinter.CTkEntry(master=app,
                               placeholder_text="00:00",
                               width=120,
                               height=25,
                               border_width=2,
                               corner_radius=10)
curTime.place(relx=0.5, rely=0.5, anchor=tkinter.W)



combobox = customtkinter.CTkComboBox(master=app,
                                     values=["am", "pm"],
                                     command=combobox_callback, height = 25, width = 70, variable = "")
combobox.pack(padx=5, pady=5)
combobox.set("pm")  # set initial value
combobox.place(relx=0.75, rely=0.5, anchor=tkinter.W)


app.mainloop()
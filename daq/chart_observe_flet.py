#!/usr/bin/python3
import os
import subprocess
import datetime
import shutil
import threading
import webbrowser
import time as time_mod

import flet as ft  # Flet for GUI to become modern and responsive

# Defaults (same as our old Tk app)
DEFAULT_FREQ_I = "1415"
DEFAULT_FREQ_F = "1425"
DEFAULT_INT_TIME = "5"
DEFAULT_NINT = "10"



# Backend helpers (preserve behavior)
def _normalize_date(date_str: str) -> str:
    # Your original code replaces "/" with "." and expects MM.DD.YYYY
    return (date_str or "").replace("/", ".")


def _normalize_user(user: str) -> str:
    # Your original code replaced "_" with "."
    return (user or "").replace("_", ".")


def _ensure_data_dir() -> str:
    home = os.path.expanduser("~")
    data_dir = os.path.join(home, "data")
    if not os.path.isdir(data_dir):
        os.mkdir(data_dir, mode=0o1777)
        print(f"Directory '{data_dir}' is built!")
    else:
        print("directory data already exists")
    return data_dir


def _make_observation_dir_name(user: str, lon: str, lat: str, date_str: str, time_str: str, ampm: str) -> str:
    # Matches our existing naming pattern (no "location", no "trial")
    # directory = f"{user}_lon{lon}_lat{lat}_{year}.{month}.{day}_{time.replace(':','.')}_{ampm}"
    month, day, year = date_str.split(".")
    date_y_m_d = f"{year}.{month}.{day}"
    return f"{user}_lon{lon}_lat{lat}_{date_y_m_d}_{time_str.replace(':', '.')}_{ampm}"


def _apply_system_date_time(date_str: str, time_str: str, ampm: str) -> None:
    """
    Preserve your behavior:
    - Convert date MM.DD.YYYY and time HH:MM with am/pm into sudo date -s "YYYY-MM-DDTHH:MM:SS"
    - Add seconds ":00"
    """
    month, day, year = date_str.split(".")
    if len(month) == 1:
        month = "0" + month
    if len(day) == 1:
        day = "0" + day
    if len(year) == 2:
        year = "20" + year  # Assuming 21st century for 2-digit years

    hour, minute = time_str.split(":")
    if ampm == "pm" and hour != "12":
        hour = str(int(hour) + 12)
    if len(hour) == 1:
        hour = "0" + hour

    # Add seconds
    hhmmss = f"{hour}:{minute}:00"
    cmd = f'sudo date -s "{year}-{month}-{day}T{hhmmss}"'
    os.system(cmd)


# Flet App
def main(page: ft.Page):
    page.title = "CHART Data Collection"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 16

    # State
    state = {
        "biasT": False,
        "proc": None,
        "data_directory": None,
        "directory": None,
        "stop_requested": False,
    }

    # UI Controls
    # Inputs (structure matches our old app)
    user_tf = ft.TextField(
        label="Username",
        hint_text="Enter Here",
        helper_text="Your WSU username or observer name",
        width=320,
    )
    lon_tf = ft.TextField(
        label="Longitude",
        hint_text="e.g., -91.64",
        helper_text="Longitude in decimal degrees (East/West)",
        width=220,
    )
    lat_tf = ft.TextField(
        label="Latitude",
        hint_text="e.g., 44.05",
        helper_text="Latitude in decimal degrees (North/South)",
        width=220,
    )

    date_tf = ft.TextField(
        label="Date",
        hint_text="MM.DD.YYYY",
        helper_text="Format: MM.DD.YYYY",
        width=220,
    )
    time_tf = ft.TextField(
        label="Time",
        hint_text="HH:MM",
        helper_text="Format: HH:MM (use am/pm selector)",
        width=140,
    )
    ampm_dd = ft.Dropdown(
        label="AM/PM",
        options=[ft.dropdown.Option("am"), ft.dropdown.Option("pm")],
        value="am",
        width=120,
    )

    freq_i_tf = ft.TextField(
        label="Initial Frequency (MHz)",
        hint_text=DEFAULT_FREQ_I,
        helper_text="Start frequency in MHz",
        width=220,
    )
    freq_f_tf = ft.TextField(
        label="Final Frequency (MHz)",
        hint_text=DEFAULT_FREQ_F,
        helper_text="End frequency in MHz",
        width=220,
    )
    int_time_tf = ft.TextField(
        label="Integration Time (s)",
        hint_text=DEFAULT_INT_TIME,
        helper_text="Integration time in seconds",
        width=220,
    )
    nint_tf = ft.TextField(
        label="Number of Integrations",
        hint_text=DEFAULT_NINT,
        helper_text="Number of integrations",
        width=240,
    )

    desc_tf = ft.TextField(
        label="Description",
        hint_text="Describe observation",
        helper_text="Short description of observation",
        width=520,
    )

    # Switches (keep same behaviors)
    use_defaults_sw = ft.Switch(label="Use Default Parameters", value=False)
    biasT_sw = ft.Switch(label="Enable Bias-T", value=False)
    use_system_dt_sw = ft.Switch(label="Use System Date and Time", value=False)
    dark_mode_sw = ft.Switch(label="Dark Mode", value=False)

    # Status / logging
    status_text = ft.Text(value="Ready.", selectable=True)
    snack = ft.SnackBar(content=ft.Text(""))

    page.snack_bar = snack

    # Buttons
    start_btn = ft.ElevatedButton(text="Start")
    stop_btn = ft.ElevatedButton(text="Stop", disabled=True)
    open_jupyter_btn = ft.OutlinedButton(text="Open documentation")

    # Helpers
    def _toast(msg: str):
        page.snack_bar.content = ft.Text(msg)
        page.snack_bar.open = True
        page.update()

    def _set_status(msg: str):
        status_text.value = msg
        page.update()

    def _set_running(running: bool):
        start_btn.disabled = running
        stop_btn.disabled = not running
        page.update()

    def _refresh_system_datetime_fields():
        now = datetime.datetime.now()
        date_entry = f"{now.month}.{now.day}.{now.year}"
        hour = now.hour
        ampm = "am"
        if hour >= 12:
            ampm = "pm"
            if hour > 12:
                hour -= 12
        minute = f"{now.minute:02d}"
        time_entry = f"{hour}:{minute}"

        # Fill hints/values similarly to your placeholder approach
        date_tf.value = date_entry
        time_tf.value = time_entry
        ampm_dd.value = ampm

        # Disable/enable fields to match the switch behavior
        locked = use_system_dt_sw.value is True
        date_tf.disabled = locked
        time_tf.disabled = locked
        ampm_dd.disabled = locked

        page.update()

    # If system datetime is enabled, keep updating every 10 seconds
    def _system_dt_loop():
        while True:
            time_mod.sleep(10)  #this can be increased or decreased
            if use_system_dt_sw.value:
                _refresh_system_datetime_fields()

    threading.Thread(target=_system_dt_loop, daemon=True).start()

    def _create_zip_watcher():
        """
        Here the Tk version calls create_zip() periodically and if proc ends successfully:
        - writes description.txt
        - zips the directory
        - stops
        """
        while True:
            time_mod.sleep(10)
            proc = state.get("proc")
            if not proc:
                continue
            # If process ended with code 0
            if proc.poll() is not None and proc.poll() == 0:
                try:
                    data_dir = state["data_directory"]
                    directory = state["directory"]
                    if not data_dir or not directory:
                        continue

                    _set_status("Creating description.txt and zip archive...")

                    desc = desc_tf.value or ""
                    with open(os.path.join(data_dir, directory, "description.txt"), "w") as f:
                        f.write(desc)

                    shutil.make_archive(os.path.join(data_dir, directory), "zip", data_dir, directory)
                    _set_status("Zip created. Data collection halted.")
                    # Auto-stop behavior matches your original
                    _do_stop(silent=True)
                except Exception as e:
                    _toast(f"Zip creation error: {e}")

    threading.Thread(target=_create_zip_watcher, daemon=True).start()

    # Actions
    def _do_stop(silent: bool = False):
        proc = state.get("proc")
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
        state["proc"] = None
        _set_running(False)
        if not silent:
            _set_status("Data collection halted!")

    def _do_start(e=None):
        # Gather inputs
        user = _normalize_user(user_tf.value.strip() if user_tf.value else "")
        lon = (lon_tf.value or "").strip()
        lat = (lat_tf.value or "").strip()

        # Use datetime depending on switch
        if use_system_dt_sw.value:
            # Ensure latest values are present
            _refresh_system_datetime_fields()

        date_str = _normalize_date(date_tf.value.strip() if date_tf.value else "")
        time_str = (time_tf.value or "").strip()
        ampm = (ampm_dd.value or "am").strip()

        # Validate minimum required
        if not user:
            _toast("Username is required.")
            return
        if not lon or not lat:
            _toast("Longitude and Latitude are required.")
            return
        if not date_str or not time_str:
            _toast("Date and Time are required.")
            return

        # Handle defaults switch
        freq_i = (freq_i_tf.value or "").strip()
        freq_f = (freq_f_tf.value or "").strip()
        itime = (int_time_tf.value or "").strip()
        nint = (nint_tf.value or "").strip()

        if use_defaults_sw.value:
            freq_i, freq_f, itime, nint = DEFAULT_FREQ_I, DEFAULT_FREQ_F, DEFAULT_INT_TIME, DEFAULT_NINT
            freq_i_tf.value = freq_i
            freq_f_tf.value = freq_f
            int_time_tf.value = itime
            nint_tf.value = nint

            # Disable fields when using defaults (like the old Tk behavior)
            freq_i_tf.disabled = True
            freq_f_tf.disabled = True
            int_time_tf.disabled = True
            nint_tf.disabled = True
        else:
            # Enable fields
            freq_i_tf.disabled = False
            freq_f_tf.disabled = False
            int_time_tf.disabled = False
            nint_tf.disabled = False

            # Fill missing with defaults
            if not freq_i:
                freq_i = DEFAULT_FREQ_I
            if not freq_f:
                freq_f = DEFAULT_FREQ_F
            if not itime:
                itime = DEFAULT_INT_TIME
            if not nint:
                nint = DEFAULT_NINT

        page.update()

        # Apply system date/time to OS (same as the old script)
        try:
            _apply_system_date_time(date_str, time_str, ampm)
        except Exception as ex:
            _toast(f"Date/time apply failed: {ex}")
            return

        # Create data directory and observation directory
        data_dir = _ensure_data_dir()
        directory = _make_observation_dir_name(user, lon, lat, date_str, time_str, ampm)
        main_dir = os.path.join(data_dir, directory)

        if os.path.isdir(main_dir):
            _toast("File already exists. Change the time before clicking Start.")
            return

        os.mkdir(main_dir, mode=0o1777)
        state["data_directory"] = data_dir
        state["directory"] = directory

        use_directory = os.path.join(data_dir, directory)
        print("directory being used:", use_directory)

        # Build command (Tried to have the exact behavior as the old one. But not sure everything is same)
        biasT = bool(biasT_sw.value)
        state["biasT"] = biasT

        if biasT:
            cmd = [
                "freq_and_time_scan.py",
                f"--freq_i={freq_i}",
                f"--freq_f={freq_f}",
                f"--int_time={itime}",
                f"--nint={nint}",
                f"--data_dir={use_directory}",
                "--biasT=True",
            ]
        else:
            cmd = [
                "freq_and_time_scan.py",
                f"--freq_i={freq_i}",
                f"--freq_f={freq_f}",
                f"--int_time={itime}",
                f"--nint={nint}",
                f"--data_dir={use_directory}",
            ]

        try:
            proc = subprocess.Popen(cmd)
            state["proc"] = proc
        except Exception as ex:
            _toast(f"Failed to start scan: {ex}")
            return

        _set_running(True)
        _set_status(f"Running. Output directory: {directory}")

    def _toggle_defaults(e):
        # If turning on defaults, disable and fill. else enable
        if use_defaults_sw.value:
            freq_i_tf.value = DEFAULT_FREQ_I
            freq_f_tf.value = DEFAULT_FREQ_F
            int_time_tf.value = DEFAULT_INT_TIME
            nint_tf.value = DEFAULT_NINT
            freq_i_tf.disabled = True
            freq_f_tf.disabled = True
            int_time_tf.disabled = True
            nint_tf.disabled = True
        else:
            freq_i_tf.disabled = False
            freq_f_tf.disabled = False
            int_time_tf.disabled = False
            nint_tf.disabled = False
        page.update()

    def _toggle_system_dt(e):
        _refresh_system_datetime_fields()

    def _toggle_dark_mode(e):
        page.theme_mode = ft.ThemeMode.DARK if dark_mode_sw.value else ft.ThemeMode.LIGHT
        page.update()

    def _open_jupyter(e):
        webbrowser.open_new("https://adampbeardsley.github.io/research.html#chart")     # It is going to the documentation of the project
                                                                        # We can change it to the Jupyter Hub link if needed

    # Wire handlers
    start_btn.on_click = _do_start
    stop_btn.on_click = lambda e: _do_stop()
    open_jupyter_btn.on_click = _open_jupyter
    use_defaults_sw.on_change = _toggle_defaults
    use_system_dt_sw.on_change = _toggle_system_dt
    dark_mode_sw.on_change = _toggle_dark_mode

    # Initial state of system datetime fields
    _refresh_system_datetime_fields()

    # Responsive Layout
    # ResponsiveRow wraps controls naturally (no manual resize code required). This part was my favorite.
    # We keep the structure similar to our existing GUI: observer info + time/date + parameters + description + switches + buttons.
    form = ft.ResponsiveRow(
        columns=12,
        spacing=12,
        run_spacing=12,
        controls=[
            ft.Container(user_tf, col={"sm": 12, "md": 6, "lg": 6}),
            ft.Container(lon_tf, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(lat_tf, col={"sm": 12, "md": 3, "lg": 3}),

            ft.Container(date_tf, col={"sm": 12, "md": 4, "lg": 4}),
            ft.Container(time_tf, col={"sm": 6, "md": 4, "lg": 4}),
            ft.Container(ampm_dd, col={"sm": 6, "md": 4, "lg": 4}),

            ft.Container(freq_i_tf, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(freq_f_tf, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(int_time_tf, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(nint_tf, col={"sm": 12, "md": 3, "lg": 3}),

            ft.Container(desc_tf, col={"sm": 12, "md": 12, "lg": 12}),
        ],
    )

    switches = ft.ResponsiveRow(
        columns=12,
        spacing=12,
        controls=[
            ft.Container(dark_mode_sw, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(use_defaults_sw, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(biasT_sw, col={"sm": 12, "md": 3, "lg": 3}),
            ft.Container(use_system_dt_sw, col={"sm": 12, "md": 3, "lg": 3}),
        ],
    )

    buttons = ft.ResponsiveRow(
        columns=12,
        spacing=12,
        controls=[
            ft.Container(start_btn, col={"sm": 6, "md": 3, "lg": 2}),
            ft.Container(stop_btn, col={"sm": 6, "md": 3, "lg": 2}),
            ft.Container(open_jupyter_btn, col={"sm": 12, "md": 6, "lg": 8}),
        ],
    )

    # Scrollable page content
    page.add(
        ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("CHART Data Collection", size=20, weight=ft.FontWeight.BOLD),
                form,
                switches,
                buttons,
                ft.Divider(),
                ft.Text("Status", weight=ft.FontWeight.BOLD),
                status_text,
            ],
        )
    )


if __name__ == "__main__":
    ft.app(target=main)

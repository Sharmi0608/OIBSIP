import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from weather_api import get_weather

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None
    letter = None

try:
    from weather_api import get_forecast
except Exception:
    get_forecast = None

try:
    from weather_api import get_air_quality
except Exception:
    get_air_quality = None

try:
    from weather_api import get_uv_index
except Exception:
    get_uv_index = None


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("WeatherVision")
root.geometry("980x900")
root.minsize(820, 760)

try:
    root.iconbitmap("assets/app_icon.ico")
except Exception:
    pass


DEGREE = "°"
search_history = []
current_weather = None
current_forecast = []
current_style = "default"
animation_index = 0

WEATHER_DATA = {
    "clear": {
        "words": ("clear", "sun"),
        "emojis": ("☀️", "🌞"),
        "card": "#FFF3CD",
        "gradient": ("#FFE7A3", "#B9E6FF"),
        "tip": "Bright and sunny outside. Wear sunglasses, use sunscreen, and drink enough water.",
    },
    "rain": {
        "words": ("rain", "drizzle"),
        "emojis": ("🌧️", "💧"),
        "card": "#DDEBFF",
        "gradient": ("#D9E7FF", "#7C98B3"),
        "tip": "Rain is likely. Carry an umbrella, wear safer footwear, and leave a little early.",
    },
    "cloud": {
        "words": ("cloud",),
        "emojis": ("☁️", "🌥️"),
        "card": "#E8EEF3",
        "gradient": ("#F3F7FA", "#AAB7C4"),
        "tip": "Cloudy weather today. It should feel comfortable, but keep a light layer nearby.",
    },
    "storm": {
        "words": ("storm", "thunder"),
        "emojis": ("⛈️", "⚡"),
        "card": "#E6E0F8",
        "gradient": ("#D8D2EA", "#5F6475"),
        "tip": "Stormy conditions possible. Stay indoors if you can and avoid open areas.",
    },
    "snow": {
        "words": ("snow",),
        "emojis": ("❄️", "☃️"),
        "card": "#EAF7FF",
        "gradient": ("#FFFFFF", "#BFE7F8"),
        "tip": "Cold and snowy conditions. Dress warmly and be careful on slippery paths.",
    },
    "mist": {
        "words": ("mist", "fog", "haze"),
        "emojis": ("🌫️", "☁️"),
        "card": "#EDF1F2",
        "gradient": ("#F6F8F8", "#B8C3C6"),
        "tip": "Visibility may be low. Travel carefully and allow extra time.",
    },
    "default": {
        "words": (),
        "emojis": ("🌤️", "🌟"),
        "card": "#EAF4EA",
        "gradient": ("#EAF4EA", "#CFE0F0"),
        "tip": "Check the sky before leaving and plan your day with a little flexibility.",
    },
}

AQI_TEXT = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}


def style_for(condition):
    condition = condition.lower()
    for name, data in WEATHER_DATA.items():
        if any(word in condition for word in data["words"]):
            return name
    return "default"


def get_value(data, names, default=None):
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return default


def call_api(function, *args):
    if function is None:
        return None
    try:
        return function(*args)
    except Exception:
        return None


def temperature_text(celsius):
    if unit_var.get() == "Fahrenheit":
        return f"{(float(celsius) * 9 / 5) + 32:.1f} {DEGREE}F"
    return f"{float(celsius):.1f} {DEGREE}C"


def set_loading(is_loading):
    search_btn.configure(
        text="Searching..." if is_loading else "Search",
        state="disabled" if is_loading else "normal",
    )
    root.configure(cursor="watch" if is_loading else "")


def hex_to_rgb(color):
    color = color.replace("#", "")
    return [int(color[i:i + 2], 16) for i in (0, 2, 4)]


def draw_gradient(top, bottom):
    gradient.delete("all")
    width = max(root.winfo_width(), 1)
    height = max(root.winfo_height(), 1)
    top_rgb, bottom_rgb = hex_to_rgb(top), hex_to_rgb(bottom)

    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = [
            int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * ratio)
            for i in range(3)
        ]
        gradient.create_line(0, y, width, y, fill=f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}")


def refresh_background(event=None):
    top, bottom = WEATHER_DATA[current_style]["gradient"]
    draw_gradient(top, bottom)


def update_clock():
    clock_label.configure(text=datetime.now().strftime("%I:%M:%S %p"))
    root.after(1000, update_clock)


def animate_icon():
    global animation_index
    emojis = WEATHER_DATA[current_style]["emojis"]
    animation_index = (animation_index + 1) % len(emojis)
    size = 56 if animation_index == 0 else 62
    weather_icon.configure(text=emojis[animation_index], font=("Segoe UI Emoji", size))
    root.after(700, animate_icon)


def update_unit(choice=None):
    if current_weather:
        temp_label.configure(text=temperature_text(current_weather["temperature"]))
    show_forecast(current_forecast)


def show_forecast(forecast):
    for widget in forecast_frame.winfo_children():
        widget.destroy()

    if not forecast:
        ctk.CTkLabel(
            forecast_frame,
            text="5-day forecast is not available from weather_api.py yet.",
            font=("Segoe UI", 14),
        ).pack(pady=10)
        return

    for day in forecast[:5]:
        condition = str(day.get("condition", "Weather"))
        temp = day.get("temperature", day.get("temp", day.get("max_temp", 0)))
        style = style_for(condition)
        data = WEATHER_DATA[style]

        box = ctk.CTkFrame(forecast_frame, width=118, height=112, corner_radius=14, fg_color=data["card"])
        box.pack(side="left", padx=6, pady=8)
        box.pack_propagate(False)

        ctk.CTkLabel(box, text=str(day.get("date", "Day")), font=("Segoe UI", 12, "bold")).pack(pady=(8, 2))
        ctk.CTkLabel(box, text=data["emojis"][0], font=("Segoe UI Emoji", 26)).pack()
        ctk.CTkLabel(box, text=temperature_text(temp), font=("Segoe UI", 13)).pack()
        ctk.CTkLabel(box, text=condition.title(), font=("Segoe UI", 11), wraplength=96).pack()


def show_air_quality(value):
    if value is None:
        aqi_label.configure(text="AQI: Not available")
        return

    try:
        number = int(value)
        aqi_label.configure(text=f"AQI: {number} - {AQI_TEXT.get(number, 'Available')}")
    except Exception:
        aqi_label.configure(text=f"AQI: {value}")


def show_uv_index(value):
    if value is None:
        uv_label.configure(text="UV Index: Not available")
        return

    try:
        number = float(value)
        if number < 3:
            level = "Low"
        elif number < 6:
            level = "Moderate"
        elif number < 8:
            level = "High"
        elif number < 11:
            level = "Very High"
        else:
            level = "Extreme"
        uv_label.configure(text=f"UV Index: {number:.1f} - {level}")
    except Exception:
        uv_label.configure(text=f"UV Index: {value}")


def set_map_link(weather):
    lat = get_value(weather, ("lat", "latitude"))
    lon = get_value(weather, ("lon", "longitude"))

    if lat and lon:
        map_btn.map_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=10/{lat}/{lon}"
    else:
        city = weather.get("city", city_entry.get().strip())
        country = weather.get("country", "")
        map_btn.map_url = f"https://www.openstreetmap.org/search?query={city}%20{country}"


def open_weather_map():
    if not map_btn.map_url:
        messagebox.showinfo("Weather Map", "Search for a city first.")
        return
    webbrowser.open(map_btn.map_url)


def report_lines():
    lines = [
        "WeatherVision Report",
        f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
        f"Location: {current_weather.get('city')}, {current_weather.get('country')}",
        f"Condition: {current_weather.get('condition')}",
        f"Temperature: {temperature_text(current_weather.get('temperature', 0))}",
        f"Humidity: {current_weather.get('humidity')}%",
        f"Wind: {current_weather.get('wind')} m/s",
        f"Feels Like: {current_weather.get('feels_like')} {DEGREE}C",
        f"Pressure: {current_weather.get('pressure')} hPa",
        aqi_label.cget("text"),
        uv_label.cget("text"),
        tip_label.cget("text"),
        "",
        "5-Day Forecast:",
    ]

    if current_forecast:
        for day in current_forecast[:5]:
            temp = day.get("temperature", day.get("temp", 0))
            lines.append(f"{day.get('date', 'Day')}: {day.get('condition', 'Weather')} - {temperature_text(temp)}")
    else:
        lines.append("Forecast is not available.")

    return lines


def export_report():
    if not current_weather:
        messagebox.showinfo("Export Report", "Search for a city before exporting.")
        return

    if canvas is None:
        messagebox.showerror("Export Report", "Install reportlab to export PDF:\npip install reportlab")
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF file", "*.pdf")],
        title="Save Weather Report",
    )
    if not path:
        return

    pdf = canvas.Canvas(path, pagesize=letter)
    y = 750
    for line in report_lines():
        pdf.setFont("Helvetica-Bold" if y == 750 else "Helvetica", 16 if y == 750 else 11)
        pdf.drawString(50, y, str(line))
        y -= 24
    pdf.save()
    messagebox.showinfo("Export Report", "Weather report exported successfully.")


def update_history(city):
    if city in search_history:
        search_history.remove(city)
    search_history.append(city)
    del search_history[:-10]
    history_box.configure(values=search_history[-5:])
    history_box.set(city)


def validate_weather(weather):
    fields = ("temperature", "city", "country", "condition", "humidity", "wind", "feels_like", "pressure", "sunrise", "sunset")
    return all(field in weather for field in fields)


def search_weather(event=None):
    global current_weather, current_forecast, current_style

    city = city_entry.get().strip()
    if not city:
        messagebox.showwarning("Input Error", "Please enter a city name.")
        city_entry.focus_set()
        return

    set_loading(True)
    root.update_idletasks()

    try:
        weather = get_weather(city)
    except Exception as error:
        weather = None
        messagebox.showerror("Weather Error", f"Could not get weather details right now.\n\n{error}")
    finally:
        set_loading(False)

    if not weather:
        messagebox.showerror("Error", "City not found. Please check the spelling.")
        city_entry.focus_set()
        city_entry.select_range(0, "end")
        return

    if not validate_weather(weather):
        messagebox.showerror("Weather Error", "The weather service returned incomplete data. Please try again.")
        return

    current_weather = weather
    current_style = style_for(weather["condition"])
    data = WEATHER_DATA[current_style]

    update_history(city.title())
    card.configure(fg_color=data["card"])
    refresh_background()

    sunrise = datetime.fromtimestamp(weather["sunrise"]).strftime("%I:%M %p")
    sunset = datetime.fromtimestamp(weather["sunset"]).strftime("%I:%M %p")

    weather_icon.configure(text=data["emojis"][0], font=("Segoe UI Emoji", 58))
    temp_label.configure(text=temperature_text(weather["temperature"]))
    location_label.configure(text=f"{weather['city']}, {weather['country']}")
    condition_label.configure(text=f"{data['emojis'][0]} {weather['condition'].title()}")
    details_label.configure(
        text=(
            f"Humidity: {weather['humidity']}%   |   Wind: {weather['wind']} m/s\n"
            f"Feels Like: {weather['feels_like']} {DEGREE}C   |   Pressure: {weather['pressure']} hPa"
        )
    )
    sunrise_label.configure(text=f"🌅 Sunrise: {sunrise}")
    sunset_label.configure(text=f"🌇 Sunset: {sunset}")
    tip_label.configure(text=f"💡 Tip: {data['tip']}")

    current_forecast = call_api(get_forecast, city) or []
    show_forecast(current_forecast if isinstance(current_forecast, list) else [])
    show_air_quality(get_value(weather, ("aqi", "air_quality")) or call_api(get_air_quality, city))
    show_uv_index(get_value(weather, ("uv", "uv_index")) or call_api(get_uv_index, city))
    set_map_link(weather)

    city_entry.focus_set()
    city_entry.select_range(0, "end")


def search_selected_city(city):
    city_entry.delete(0, "end")
    city_entry.insert(0, city)
    search_weather()


def toggle_theme():
    dark = theme_switch.get() == 1
    ctk.set_appearance_mode("dark" if dark else "light")
    theme_switch.configure(text="Dark Mode" if dark else "Light Mode")


gradient = ctk.CTkCanvas(root, highlightthickness=0)
gradient.place(x=0, y=0, relwidth=1, relheight=1)

content = ctk.CTkScrollableFrame(root, fg_color="transparent")
content.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.96, relheight=0.96)

top_bar = ctk.CTkFrame(content, fg_color="transparent")
top_bar.pack(fill="x", pady=(4, 6))

ctk.CTkLabel(top_bar, text="WeatherVision", font=("Segoe UI", 34, "bold")).pack(side="left", padx=18)

clock_label = ctk.CTkLabel(top_bar, text="", font=("Segoe UI", 18, "bold"))
clock_label.pack(side="right", padx=18)

theme_switch = ctk.CTkSwitch(top_bar, text="Light Mode", command=toggle_theme)
theme_switch.pack(side="right", padx=12)

ctk.CTkLabel(content, text=datetime.now().strftime("%d %B %Y"), font=("Segoe UI", 17)).pack(pady=(0, 8))

search_frame = ctk.CTkFrame(content, corner_radius=18)
search_frame.pack(pady=(6, 12), padx=20)
search_frame.grid_columnconfigure((0, 1, 2), weight=1)

ctk.CTkLabel(search_frame, text="Enter City Name", font=("Segoe UI", 18)).grid(
    row=0, column=0, columnspan=3, padx=20, pady=(14, 6)
)

city_entry = ctk.CTkEntry(
    search_frame,
    width=300,
    height=38,
    font=("Segoe UI", 17),
    justify="center",
    placeholder_text="Example: Chennai",
)
city_entry.grid(row=1, column=0, padx=(20, 10), pady=(4, 14))
city_entry.bind("<Return>", search_weather)

unit_var = ctk.StringVar(value="Celsius")
unit_menu = ctk.CTkOptionMenu(search_frame, values=["Celsius", "Fahrenheit"], variable=unit_var, command=update_unit, width=150)
unit_menu.grid(row=1, column=1, padx=10, pady=(4, 14))

search_btn = ctk.CTkButton(search_frame, text="Search", width=130, height=38, font=("Segoe UI", 17, "bold"), command=search_weather)
search_btn.grid(row=1, column=2, padx=(10, 20), pady=(4, 14))

history_box = ctk.CTkComboBox(search_frame, values=[], width=220, command=search_selected_city)
history_box.grid(row=2, column=0, columnspan=3, pady=(0, 14))
history_box.set("Recent Searches")

card = ctk.CTkFrame(content, width=700, height=430, corner_radius=22, fg_color=WEATHER_DATA["default"]["card"])
card.pack(pady=(4, 10))
card.pack_propagate(False)

location_label = ctk.CTkLabel(card, text="Location", font=("Segoe UI", 22))
location_label.pack(pady=(16, 3))

weather_icon = ctk.CTkLabel(card, text=WEATHER_DATA["default"]["emojis"][0], font=("Segoe UI Emoji", 58))
weather_icon.pack(pady=0)

temp_label = ctk.CTkLabel(card, text="Temperature", font=("Segoe UI", 28, "bold"))
temp_label.pack(pady=(0, 2))

condition_label = ctk.CTkLabel(card, text="Condition", font=("Segoe UI", 18))
condition_label.pack(pady=2)

details_label = ctk.CTkLabel(card, text="", font=("Segoe UI", 17), justify="center")
details_label.pack(pady=(8, 4))

sun_frame = ctk.CTkFrame(card, fg_color="transparent")
sun_frame.pack(pady=4)

sunrise_label = ctk.CTkLabel(sun_frame, text="Sunrise", font=("Segoe UI", 16))
sunrise_label.pack(side="left", padx=20)

sunset_label = ctk.CTkLabel(sun_frame, text="Sunset", font=("Segoe UI", 16))
sunset_label.pack(side="left", padx=20)

index_frame = ctk.CTkFrame(card, fg_color="transparent")
index_frame.pack(pady=(6, 2))

aqi_label = ctk.CTkLabel(index_frame, text="AQI: Not available", font=("Segoe UI", 15, "bold"))
aqi_label.pack(side="left", padx=18)

uv_label = ctk.CTkLabel(index_frame, text="UV Index: Not available", font=("Segoe UI", 15, "bold"))
uv_label.pack(side="left", padx=18)

tip_label = ctk.CTkLabel(card, text="Weather Tip", text_color="#2E7D32", font=("Segoe UI", 17, "bold"), wraplength=620, justify="center")
tip_label.pack(pady=(12, 12), padx=24)

actions_frame = ctk.CTkFrame(content, fg_color="transparent")
actions_frame.pack(pady=(0, 10))

ctk.CTkButton(actions_frame, text="Export PDF", width=150, command=export_report).pack(side="left", padx=8)

map_btn = ctk.CTkButton(actions_frame, text="Weather Map", width=150, command=open_weather_map)
map_btn.pack(side="left", padx=8)
map_btn.map_url = None

ctk.CTkLabel(content, text="5-Day Forecast", font=("Segoe UI", 22, "bold")).pack(pady=(4, 2))

forecast_frame = ctk.CTkFrame(content, fg_color="transparent")
forecast_frame.pack(pady=(0, 8))
show_forecast([])

ctk.CTkLabel(content, text="Developed by Sharmila R", font=("Segoe UI", 14)).pack(pady=(0, 10))

city_entry.focus_set()
root.bind("<Configure>", refresh_background)
refresh_background()
update_clock()
animate_icon()

root.mainloop()

#!/usr/bin/env python3
import gi
import subprocess
import json
import os
import tempfile

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Adw, GLib, WebKit

class TimezoneSelectPage(Adw.Bin):
    """
    Timezone selection page with interactive Leaflet map + timezone list.
    This version DOES NOT write timezone files; it only sets self.selected_timezone.
    """
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.selected_timezone = None
        self.map_file_path = None
        self._selecting_from_map = False
        self.expander_rows = []
        self.selected_row = None

        # timezone coordinates (full list from your example)
        self.timezone_coordinates = {
            # North America
            "America/New_York": [40.7128, -74.0060],
            "America/Chicago": [41.8781, -87.6298],
            "America/Denver": [39.7392, -104.9903],
            "America/Los_Angeles": [34.0522, -118.2437],
            "America/Vancouver": [49.2827, -123.1207],
            "America/Toronto": [43.651070, -79.347015],
            "America/Mexico_City": [19.4326, -99.1332],
            "America/Sao_Paulo": [-23.5558, -46.6396],
            "America/Buenos_Aires": [-34.6118, -58.3960],
            "America/Lima": [-12.0464, -77.0428],
            "America/Bogota": [4.7110, -74.0721],
            # Europe
            "Europe/London": [51.5074, -0.1278],
            "Europe/Paris": [48.8566, 2.3522],
            "Europe/Berlin": [52.5200, 13.4050],
            "Europe/Rome": [41.9028, 12.4964],
            "Europe/Madrid": [40.4168, -3.7038],
            "Europe/Amsterdam": [52.3676, 4.9041],
            "Europe/Warsaw": [52.2297, 21.0122],
            "Europe/Moscow": [55.7558, 37.6173],
            "Europe/Vienna": [48.2082, 16.3738],
            "Europe/Stockholm": [59.3293, 18.0686],
            "Europe/Athens": [37.9838, 23.7275],
            "Europe/Kiev": [50.4501, 30.5234],
            "Europe/Zurich": [47.3769, 8.5417],
            # Asia
            "Asia/Tokyo": [35.6762, 139.6503],
            "Asia/Shanghai": [31.2304, 121.4737],
            "Asia/Hong_Kong": [22.3193, 114.1694],
            "Asia/Singapore": [1.3521, 103.8198],
            "Asia/Mumbai": [19.0760, 72.8777],
            "Asia/Dubai": [25.2048, 55.2708],
            "Asia/Bangkok": [13.7563, 100.5018],
            "Asia/Jakarta": [-6.2088, 106.8456],
            "Asia/Seoul": [37.5665, 126.9780],
            "Asia/Manila": [14.5995, 120.9842],
            "Asia/Karachi": [24.8607, 67.0011],
            "Asia/Tehran": [35.6892, 51.3890],
            "Asia/Baghdad": [33.3152, 44.3661],
            "Asia/Riyadh": [24.7136, 46.6753],
            # Africa
            "Africa/Cairo": [30.0444, 31.2357],
            "Africa/Lagos": [6.5244, 3.3792],
            "Africa/Johannesburg": [-26.2041, 28.0473],
            "Africa/Nairobi": [-1.2921, 36.8219],
            "Africa/Casablanca": [33.5731, -7.5898],
            "Africa/Tunis": [36.8065, 10.1815],
            "Africa/Algiers": [36.7538, 3.0588],
            # Australia / Pacific
            "Australia/Sydney": [-33.8688, 151.2093],
            "Australia/Melbourne": [-37.8136, 144.9631],
            "Australia/Perth": [-31.9505, 115.8605],
            "Australia/Brisbane": [-27.4698, 153.0251],
            "Australia/Adelaide": [-34.9285, 138.6007],
            "Pacific/Auckland": [-36.8485, 174.7633],
            "Pacific/Fiji": [-18.1248, 178.4501],
            "Pacific/Honolulu": [21.3099, -157.8581],
            # Other
            "UTC": [51.4769, -0.0005],
            "GMT": [51.4769, -0.0005],
        }

        # Layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_valign(Gtk.Align.FILL)
        box.set_halign(Gtk.Align.FILL)
        self.set_child(box)

        title = Gtk.Label(label="🕒 <big><b>Select your timezone</b></big>", use_markup=True)
        title.set_halign(Gtk.Align.CENTER)
        box.append(title)

        # Paned layout: map left, list right
        clamp = Adw.Clamp(margin_start=12, margin_end=12, maximum_size=1000)
        clamp.set_vexpand(True)
        box.append(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        clamp.set_child(content_box)

        subtitle = Gtk.Label(label="Choose a city in your region. This will be used to set the clock.")
        subtitle.add_css_class("dim-label")
        subtitle.set_halign(Gtk.Align.CENTER)
        content_box.append(subtitle)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search for your city or region...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        content_box.append(self.search_entry)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(400)
        paned.set_vexpand(True)
        content_box.append(paned)

        # Map container (left)
        map_frame = Gtk.Frame()
        map_frame.set_size_request(400, 300)
        paned.set_start_child(map_frame)

        # WebView (Leaflet map)
        self.web_view = WebKit.WebView()
        self.web_view.connect("load-changed", self.on_map_load_changed)
        map_frame.set_child(self.web_view)

        # List container (right)
        list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        list_container.set_margin_start(10)
        paned.set_end_child(list_container)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_has_frame(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        list_container.append(scrolled_window)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.get_style_context().add_class("boxed-list")
        scrolled_window.set_child(self.list_box)

        # Populate list + load map
        self.populate_timezones()
        # Register message handler now if possible; else on_map_load_changed will attempt it
        self._try_register_message_handler()
        self.load_timezone_map()

        # Bottom navigation
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        box.append(button_box)

        self.btn_back = Gtk.Button(label="← Back")
        button_box.append(self.btn_back)
        self.btn_back.connect("clicked", self.on_back)

        self.btn_proceed = Gtk.Button(label="Next →")
        self.btn_proceed.add_css_class("suggested-action")
        self.btn_proceed.set_sensitive(False)
        self.btn_proceed.connect("clicked", self.on_continue_clicked)
        button_box.append(self.btn_proceed)

    # -------------------------
    # Map HTML generation & load
    # -------------------------
    def create_map_html(self):
        markers_js = []
        for timezone, coords in self.timezone_coordinates.items():
            lat, lng = coords
            city = timezone.split('/')[-1].replace('_', ' ')
            markers_js.append(f"""
                L.marker([{lat}, {lng}])
                    .addTo(map)
                    .bindPopup('<b>{city}</b><br>{timezone}')
                    .on('click', function(e) {{
                        selectTimezone('{timezone}');
                    }});
            """)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Timezone Map</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
<style>
    html,body,#map {{ height:100%; margin:0; padding:0; }}
    #map {{ width:100%; }}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>
<script>
var map = L.map('map').setView([20, 0], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors'
}}).addTo(map);

function selectTimezone(tz) {{
    try {{
        window.webkit.messageHandlers.timezoneSelected.postMessage(tz);
    }} catch (err) {{
        console.log('messageHandlers not available', err);
    }}
}}

{''.join(markers_js)}

// approximate click -> choose nearest marker
var timezoneCoords = {json.dumps(self.timezone_coordinates)};
map.on('click', function(e) {{
    var lat = e.latlng.lat, lng = e.latlng.lng;
    var closest = null, minD = Infinity;
    Object.entries(timezoneCoords).forEach(function(kv) {{
        var tz = kv[0], c = kv[1];
        var d = Math.pow(lat - c[0],2) + Math.pow(lng - c[1],2);
        if (d < minD) {{ minD = d; closest = tz; }}
    }});
    if (closest) selectTimezone(closest);
}});
</script>
</body>
</html>
"""
        return html_content

    def load_timezone_map(self):
        html = self.create_map_html()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html)
            self.map_file_path = f.name
        try:
            self.web_view.load_uri(f"file://{self.map_file_path}")
        except Exception:
            try:
                self.web_view.load_html(html, "file:///")
            except Exception as e:
                print(f"[TimezoneSelectPage] Could not load map HTML: {e}")

    # -------------------------
    # WebKit message handler registration (try early, fallback later)
    # -------------------------
    def _try_register_message_handler(self):
        """
        Try to register script message handler now. If web_view.get_user_content_manager()
        returns a manager, register and connect. Otherwise, we'll try again after load.
        """
        try:
            cm = None
            try:
                cm = self.web_view.get_user_content_manager()
            except Exception:
                cm = None

            if cm:
                try:
                    cm.register_script_message_handler("timezoneSelected")
                except Exception as e:
                    # non-fatal
                    print(f"[TimezoneSelectPage] register_script_message_handler warning: {e}")
                try:
                    cm.connect("script-message-received", self.on_timezone_selected_from_map)
                except Exception as e:
                    print(f"[TimezoneSelectPage] Could not connect script-message-received: {e}")
            else:
                # will register in on_map_load_changed
                pass
        except Exception as e:
            print(f"[TimezoneSelectPage] _try_register_message_handler error: {e}")

    # called when webview load state changes
    def on_map_load_changed(self, web_view, load_event):
        if load_event == WebKit.LoadEvent.FINISHED:
            # If message handler wasn't available earlier, try to register now
            try:
                cm = web_view.get_user_content_manager()
            except Exception:
                cm = None

            if cm:
                try:
                    cm.register_script_message_handler("timezoneSelected")
                except Exception:
                    pass
                try:
                    cm.connect("script-message-received", self.on_timezone_selected_from_map)
                except Exception:
                    pass
            print("[TimezoneSelectPage] Map load finished")

    # -------------------------
    # Message from JS: timezone selected
    # -------------------------
    def on_timezone_selected_from_map(self, content_manager, message):
        try:
            if hasattr(message, "get_js_value"):
                tz = message.get_js_value().to_string()
            else:
                tz = str(message)
            if tz:
                print(f"[TimezoneSelectPage] Timezone selected from map: {tz}")
                # select in list (avoid recursion)
                self._selecting_from_map = True
                self.select_timezone_in_list(tz)
                self.btn_proceed.set_sensitive(True)
                self._selecting_from_map = False
                # highlight on map
                self.highlight_timezone_on_map(tz)
                # set selected_timezone
                self.selected_timezone = tz
        except Exception as e:
            print(f"[TimezoneSelectPage] Error handling script message: {e}; type={type(message)}; dir={dir(message)}")

    # -------------------------
    # List / search / selection logic (no saving)
    # -------------------------
    def populate_timezones(self):
        try:
            result = subprocess.run(['timedatectl', 'list-timezones'], capture_output=True, text=True, check=True)
            timezones = result.stdout.strip().split('\n')
        except Exception:
            timezones = list(self.timezone_coordinates.keys()) + ["UTC"]

        grouped = {}
        for tz in timezones:
            if "/" in tz:
                continent = tz.split('/')[0]
            else:
                continent = "Other"
            grouped.setdefault(continent, []).append(tz)

        for continent in sorted(grouped.keys()):
            expander = Adw.ExpanderRow(title=continent)
            self.list_box.append(expander)

            nested_listbox = Gtk.ListBox()
            nested_listbox.get_style_context().add_class("boxed-list")
            nested_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            nested_listbox.connect("row-selected", self.on_row_selected)
            expander.add_row(nested_listbox)

            expander.child_rows = []
            for tz_name in sorted(grouped[continent]):
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row_box.set_margin_start(10)
                row_box.set_margin_end(10)
                row_box.set_margin_top(10)
                row_box.set_margin_bottom(10)

                label = Gtk.Label(label=tz_name, xalign=0)
                label.set_hexpand(True)
                row_box.append(label)

                if tz_name in self.timezone_coordinates:
                    icon = Gtk.Image.new_from_icon_name("mark-location-symbolic")
                    icon.set_opacity(0.6)
                    row_box.append(icon)

                row.set_child(row_box)
                row.timezone_name = tz_name
                row.search_term = tz_name.lower().replace("_", " ")
                nested_listbox.append(row)
                expander.child_rows.append(row)
            self.expander_rows.append(expander)

    def on_search_changed(self, entry):
        text = entry.get_text().lower()
        for expander in self.expander_rows:
            visible = 0
            for row in expander.child_rows:
                ok = text in row.search_term
                row.set_visible(ok)
                if ok:
                    visible += 1
            expander.set_visible(visible > 0)
            if text:
                expander.set_expanded(visible > 0)

    def select_timezone_in_list(self, timezone):
        continent = timezone.split('/')[0] if '/' in timezone else "Other"
        for exp in self.expander_rows:
            if exp.get_title() == continent:
                exp.set_expanded(True)
                for row in exp.child_rows:
                    if hasattr(row, "timezone_name") and row.timezone_name == timezone:
                        nested = row.get_parent()
                        try:
                            nested.unselect_all()
                        except Exception:
                            pass
                        nested.select_row(row)
                        self.on_row_selected(nested, row)
                        GLib.idle_add(lambda: self.scroll_to_row(row))
                        return True
        return False

    def scroll_to_row(self, row):
        try:
            widget = row
            while widget and not isinstance(widget, Gtk.ScrolledWindow):
                widget = widget.get_parent()
            if widget and isinstance(widget, Gtk.ScrolledWindow):
                vadj = widget.get_vadjustment()
                if vadj:
                    alloc = row.get_allocation()
                    vadj.set_value(max(0, alloc.y - vadj.get_page_size() / 2))
        except Exception as e:
            print(f"[TimezoneSelectPage] scroll error: {e}")
        return False

    def highlight_timezone_on_map(self, timezone):
        js = f"""
        map.eachLayer(function(layer) {{
            if (layer instanceof L.Marker) {{
                layer.setOpacity(0.7);
            }}
        }});
        console.log('highlight {timezone}');
        """
        try:
            if hasattr(self.web_view, "run_javascript"):
                self.web_view.run_javascript(js, None, lambda w, r: None, None)
            elif hasattr(self.web_view, "evaluate_javascript"):
                self.web_view.evaluate_javascript(js, -1, None, None, None, None)
            else:
                print("[TimezoneSelectPage] No JS exec API found")
        except Exception as e:
            print(f"[TimezoneSelectPage] highlight JS error: {e}")

    def on_row_selected(self, listbox, row):
        # avoid recursion when selected from map
        if hasattr(self, "_selecting_from_map") and self._selecting_from_map:
            self._selecting_from_map = False
        else:
            if self.selected_timezone and self.selected_timezone != getattr(row, "timezone_name", None):
                # clear previous selection if needed (best-effort)
                try:
                    if self.selected_row and self.selected_row.get_parent() != listbox:
                        self.selected_row.get_parent().unselect_row(self.selected_row)
                except Exception:
                    pass

        self.selected_row = row
        self.btn_proceed.set_sensitive(row is not None)
        if row is not None:
            # DO NOT save to disk in this version; just set selected_timezone and highlight
            if hasattr(row, "timezone_name"):
                self.selected_timezone = row.timezone_name
                self.highlight_timezone_on_map(row.timezone_name)

    def on_back(self, button):
        if hasattr(self.app, "go_to"):
            self.app.go_to("language")

    def on_continue_clicked(self, button):
        if self.selected_timezone:
            # store into app state, but do not write files
            if hasattr(self.app, "selected_timezone"):
                self.app.selected_timezone = self.selected_timezone
            print(f"[TimezoneSelectPage] Proceeding with timezone: {self.selected_timezone}")
        else:
            print("[TimezoneSelectPage] No timezone selected")

    def get_selected_timezone(self):
        return self.selected_timezone

    def __del__(self):
        try:
            if getattr(self, "map_file_path", None) and os.path.exists(self.map_file_path):
                os.unlink(self.map_file_path)
        except Exception:
            pass

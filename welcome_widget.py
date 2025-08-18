#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
import os
import gettext
import locale
import math

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# Import GLib for the timer and Adw for the animation
from gi.repository import Gtk, Adw, Gdk, GLib

# --- i18n Setup ---
WIDGET_NAME = "linexin-installer-welcome-widget"
LOCALE_DIR = "/usr/share/locale"
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain(WIDGET_NAME, LOCALE_DIR)
gettext.bindtextdomain(WIDGET_NAME, LOCALE_DIR)
gettext.textdomain(WIDGET_NAME)
_ = gettext.gettext


class WelcomeWidget(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- Language Lists for Animation ---
        self.translations = [
            "Welcome to", "Witaj w", "Bienvenido a", "Bienvenue à",
            "Willkommen bei", "Benvenuto in", "Bem-vindo a", "Добро пожаловать в",
            "へようこそ", "欢迎来到", "مرحبا بك في", "में आपका स्वागत है", "Welkom bij",
            "Välkommen till", "'a hoş geldiniz", "에 오신 것을 환영합니다", "Καλώς ήρθατε στο",
            "Ласкаво просимо до", "Vítejte v", "Tervetuloa"
        ]
        
        self.button_translations = [
            "Begin Installation", "Rozpocznij instalację", "Iniciar instalación", "Commencer l'installation",
            "Installation beginnen", "Inizia l'installazione", "Iniciar instalação", "Начать установку",
            "インストールを開始", "开始安装", "بدء التثبيت", "इंस्टॉलेशन शुरू करें", "Installatie beginnen",
            "Påbörja installationen", "Kuruluma Başla", "설치 시작", "Έναρξη εγκατάστασης",
            "Почати встановлення", "Zahájit instalaci", "Aloita asennus"
        ]
        
        self.current_lang_index = 0
        self.animation_running = False

        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "images", "logo.png")

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)  # We'll use margins for better control
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        # Add CSS for enhanced styling
        self.setup_custom_css()

        # Create main container with some breathing room
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=40)
        main_container.set_margin_top(60)
        main_container.set_margin_bottom(60)
        main_container.set_margin_start(80)
        main_container.set_margin_end(80)
        main_container.set_valign(Gtk.Align.CENTER)
        main_container.set_halign(Gtk.Align.CENTER)

        # Welcome text container - fixed height to prevent layout shifts
        text_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        text_container.set_halign(Gtk.Align.CENTER)
        text_container.set_valign(Gtk.Align.CENTER)
        text_container.set_size_request(-1, 80)  # Fixed height to prevent movement

        # Animated welcome label
        self.welcome_label = Gtk.Label()
        self.welcome_label.add_css_class("welcome_text")
        self.welcome_label.set_markup(f'<span size="x-large" weight="bold">{_("Welcome to")}</span>')
        self.welcome_label.set_halign(Gtk.Align.CENTER)
        self.welcome_label.set_valign(Gtk.Align.CENTER)
        text_container.append(self.welcome_label)

        main_container.append(text_container)

        # Logo with scaling animation - allow shrinking again
        self.logo_container = Gtk.Box(halign=Gtk.Align.CENTER)
        self.welcome_image = Gtk.Picture.new_for_filename(image_path)
        self.welcome_image.set_can_shrink(True)  # Allow shrinking again
        self.welcome_image.set_halign(Gtk.Align.CENTER)
        self.welcome_image.set_valign(Gtk.Align.CENTER)
        self.welcome_image.add_css_class("logo_image")
        self.welcome_image.set_size_request(300, 300)  # Preferred size
        self.logo_container.append(self.welcome_image)
        main_container.append(self.logo_container)

        # Button container with hover effects
        button_container = Gtk.Box(halign=Gtk.Align.CENTER, spacing=20)
        button_container.set_margin_top(40)
        
        self.btn_install = Gtk.Button(label=_("Begin Installation"))
        self.btn_install.add_css_class("suggested-action")
        self.btn_install.add_css_class("proceed_button")
        self.btn_install.add_css_class("animated_button")
        self.btn_install.set_size_request(200, 50)
        
        # Add hover effects
        hover_controller = Gtk.EventControllerMotion()
        hover_controller.connect("enter", self.on_button_hover_enter)
        hover_controller.connect("leave", self.on_button_hover_leave)
        self.btn_install.add_controller(hover_controller)
        
        button_container.append(self.btn_install)
        main_container.append(button_container)

        self.append(main_container)

        # Start entrance animations
        GLib.timeout_add(100, self.start_entrance_animations)
        
        # Start language cycling after entrance (much slower)
        GLib.timeout_add_seconds(8, self.start_language_cycling)

    def setup_custom_css(self):
        """Setup enhanced CSS for modern look and animations"""
        css_provider = Gtk.CssProvider()
        css_data = """
        .welcome_text {
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.5s ease;
        }
        
        .subtitle_text {
            font-style: italic;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .logo_image {
            transition: opacity 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .animated_button {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-radius: 25px;
            font-weight: bold;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
        }
        
        .animated_button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(74, 144, 226, 0.4);
        }
        
        .animated_button:active {
            transform: translateY(1px);
            box-shadow: 0 2px 8px rgba(74, 144, 226, 0.3);
        }
        
        /* Pulse animation for active elements */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .pulse-animation {
            animation: pulse 2s ease-in-out infinite;
        }
        """
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def start_entrance_animations(self):
        """Create staggered entrance animations for all elements"""
        # Fade in welcome text
        self.animate_element_entrance(self.welcome_label, 0)
        
        # Scale in logo with delay
        GLib.timeout_add(300, lambda: self.animate_logo_entrance())
        
        # Slide in button with delay
        GLib.timeout_add(600, lambda: self.animate_button_entrance())
        # Fade in progress dots with stagger - REMOVED
        # for i, dot in enumerate(self.progress_dots):
        #     GLib.timeout_add(1200 + (i * 50), lambda d=dot: self.animate_element_entrance(d, 0))
        
        return False

    def animate_element_entrance(self, element, start_opacity):
        """Generic fade-in animation for elements"""
        element.set_opacity(start_opacity)
        target = Adw.CallbackAnimationTarget.new(
            lambda value, data: element.set_opacity(value), None
        )
        animation = Adw.TimedAnimation.new(
            element, start_opacity, 1.0, 800, target
        )
        animation.play()

    def animate_logo_entrance(self):
        """Special scaling entrance for logo"""
        # Start with scale 0.3 and animate to 1.0
        original_size = self.welcome_image.get_size_request()
        
        def scale_callback(value, data):
            # Apply CSS transform for scaling
            scale_factor = 0.3 + (value * 0.7)  # From 0.3 to 1.0
            self.welcome_image.set_opacity(value)
            
        target = Adw.CallbackAnimationTarget.new(scale_callback, None)
        animation = Adw.TimedAnimation.new(
            self.welcome_image, 0.0, 1.0, 1000, target
        )
        animation.set_easing(Adw.Easing.EASE_OUT_BACK)  # Bouncy effect
        animation.play()

    def animate_button_entrance(self):
        """Slide-up animation for button"""
        self.btn_install.set_opacity(0)
        self.btn_install.set_margin_top(120)  # Start lower
        
        # Opacity animation
        opacity_target = Adw.CallbackAnimationTarget.new(
            lambda value, data: self.btn_install.set_opacity(value), None
        )
        opacity_animation = Adw.TimedAnimation.new(
            self.btn_install, 0.0, 1.0, 600, opacity_target
        )
        
        # Slide animation
        slide_target = Adw.CallbackAnimationTarget.new(
            lambda value, data: self.btn_install.set_margin_top(int(120 - (value * 40))), None
        )
        slide_animation = Adw.TimedAnimation.new(
            self.btn_install, 0.0, 1.0, 600, slide_target
        )
        slide_animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        
        opacity_animation.play()
        slide_animation.play()

    def update_progress_dots(self):
        """Update progress dots with smooth transitions"""
        for i, dot in enumerate(self.progress_dots):
            if i == self.current_lang_index:
                dot.add_css_class("active_dot")
                # Add pulse effect
                dot.add_css_class("pulse-animation")
            else:
                dot.remove_css_class("active_dot")
                dot.remove_css_class("pulse-animation")

    def on_button_hover_enter(self, controller, x, y):
        """Enhanced hover enter effect"""
        # Scale up button slightly
        self.btn_install.add_css_class("pulse-animation")

    def on_button_hover_leave(self, controller):
        """Enhanced hover leave effect"""
        # Remove pulse effect
        self.btn_install.remove_css_class("pulse-animation")

    def start_language_cycling(self):
        """Begin the language cycling animation loop"""
        if not self.animation_running:
            self.animation_running = True
            GLib.timeout_add_seconds(3, self.cycle_language)
        return False

    def cycle_language(self):
        """Main language cycling with enhanced animations"""
        if not self.animation_running:
            return False
            
        # Start the fade out with scaling (slower timing)
        self.start_text_fade_out_enhanced()
        return True

    def _on_welcome_opacity_update(self, value, user_data):
        """Update welcome label opacity with scaling effect"""
        self.welcome_label.set_opacity(value)
        # Add subtle scaling during fade
        scale = 0.95 + (value * 0.05)  # Scale from 0.95 to 1.0

    def _on_button_opacity_update(self, value, user_data):
        """Update button opacity"""
        self.btn_install.set_opacity(value)

    def start_text_fade_out_enhanced(self):
        """Enhanced fade out with multiple elements"""
        # Fade out welcome text
        welcome_target = Adw.CallbackAnimationTarget.new(self._on_welcome_opacity_update, None)
        welcome_animation = Adw.TimedAnimation.new(
            self.welcome_label, 1.0, 0.0, 400, welcome_target
        )
        welcome_animation.set_easing(Adw.Easing.EASE_IN_CUBIC)
        
        # Fade out button
        button_target = Adw.CallbackAnimationTarget.new(self._on_button_opacity_update, None)
        button_animation = Adw.TimedAnimation.new(
            self.btn_install, 1.0, 0.0, 400, button_target
        )
        button_animation.set_easing(Adw.Easing.EASE_IN_CUBIC)
        
        # Connect completion callback
        welcome_animation.connect("done", self.change_text_and_fade_in_enhanced)
        
        welcome_animation.play()
        button_animation.play()

    def change_text_and_fade_in_enhanced(self, animation):
        """Enhanced text change with smooth transitions"""
        # Update language index
        self.current_lang_index = (self.current_lang_index + 1) % len(self.translations)
        
        # Update welcome label text
        new_text = self.translations[self.current_lang_index]
        self.welcome_label.set_markup(f'<span size="x-large" weight="bold">{new_text}</span>')

        # Update button text
        new_button_text = self.button_translations[self.current_lang_index]
        self.btn_install.set_label(new_button_text)

        # Update progress dots - REMOVED FUNCTIONALITY
        # self.update_progress_dots()

        # Fade in welcome label with bounce
        welcome_target = Adw.CallbackAnimationTarget.new(self._on_welcome_opacity_update, None)
        welcome_fade_in = Adw.TimedAnimation.new(
            self.welcome_label, 0.0, 1.0, 600, welcome_target
        )
        welcome_fade_in.set_easing(Adw.Easing.EASE_OUT_BACK)  # Bouncy entrance
        
        # Fade in button with slide
        button_target = Adw.CallbackAnimationTarget.new(self._on_button_opacity_update, None)
        button_fade_in = Adw.TimedAnimation.new(
            self.btn_install, 0.0, 1.0, 600, button_target
        )
        button_fade_in.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        
        welcome_fade_in.play()
        # Delay button fade in slightly for staggered effect
        GLib.timeout_add(150, lambda: button_fade_in.play())

        # Schedule next cycle (much slower - 5 seconds between changes)
        GLib.timeout_add_seconds(5, self.start_text_fade_out_enhanced)

    def add_floating_particles(self):
        """Add subtle floating particle effect (optional enhancement)"""
        # This could be implemented with custom drawing for extra flair
        pass

    def stop_animations(self):
        """Stop all running animations (useful for cleanup)"""
        self.animation_running = False


class EnhancedWelcomeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.linexin.installer.welcome")
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        # Create window with modern styling
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("LineXin OS Installer")
        self.win.set_default_size(800, 600)
        
        # Set up window background
        self.setup_window_styling()
        
        # Create and add welcome widget
        self.welcome_widget = WelcomeWidget()
        self.win.set_content(self.welcome_widget)
        
        # Add some window-level effects
        self.win.connect("close-request", self.on_window_close)
        
        self.win.present()

    def setup_window_styling(self):
        """Setup window-level styling"""
        css_provider = Gtk.CssProvider()
        css_data = """
        window {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        """
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_window_close(self, window):
        """Cleanup when window closes"""
        if hasattr(self, 'welcome_widget'):
            self.welcome_widget.stop_animations()
        return False


if __name__ == "__main__":
    app = EnhancedWelcomeApp()
    app.run(None)
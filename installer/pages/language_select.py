import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class LanguageSelectPage(Adw.Bin):
    def __init__(self, app):
        super().__init__()
        self.app = app

        # główny layout
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        self.set_child(box)

        title = Gtk.Label(label="🌐 <big><b>Select your language</b></big>", use_markup=True)
        title.set_halign(Gtk.Align.CENTER)
        box.append(title)

        # języki z emoji flag (nie wszystkie mają dokładne flagi, więc symbolicznie)
        self.languages = {
            "af_ZA.UTF-8": "🇿🇦 Afrikaans (Suid-Afrika)",
            "sq_AL.UTF-8": "🇦🇱 Shqip (Shqipëri)",
            "ar_SA.UTF-8": "🇸🇦 العربية (السعودية)",
            "be_BY.UTF-8": "🇧🇾 Беларуская (Беларусь)",
            "bs_BA.UTF-8": "🇧🇦 Bosanski (Bosna i Hercegovina)",
            "bg_BG.UTF-8": "🇧🇬 Български (България)",
            "ca_ES.UTF-8": "🇪🇸 Català (Espanya)",
            "zh_CN.UTF-8": "🇨🇳 简体中文 (中国)",
            "zh_TW.UTF-8": "🇹🇼 繁體中文 (台灣)",
            "hr_HR.UTF-8": "🇭🇷 Hrvatski (Hrvatska)",
            "cs_CZ.UTF-8": "🇨🇿 Čeština (Česká republika)",
            "da_DK.UTF-8": "🇩🇰 Dansk (Danmark)",
            "nl_NL.UTF-8": "🇳🇱 Nederlands (Nederland)",
            "en_US.UTF-8": "🇺🇸 English (United States)",
            "en_GB.UTF-8": "🇬🇧 English (United Kingdom)",
            "en_AU.UTF-8": "🇦🇺 English (Australia)",
            "en_CA.UTF-8": "🇨🇦 English (Canada)",
            "et_EE.UTF-8": "🇪🇪 Eesti (Eesti)",
            "fa_IR.UTF-8": "🇮🇷 فارسی (ایران)",
            "fil_PH.UTF-8": "🇵🇭 Filipino (Pilipinas)",
            "fi_FI.UTF-8": "🇫🇮 Suomi (Suomi)",
            "fr_FR.UTF-8": "🇫🇷 Français (France)",
            "fr_CA.UTF-8": "🇨🇦 Français (Canada)",
            "ga_IE.UTF-8": "🇮🇪 Gaeilge (Éire)",
            "gl_ES.UTF-8": "🇪🇸 Galego (España)",
            "ka_GE.UTF-8": "🇬🇪 ქართული (საქართველო)",
            "de_DE.UTF-8": "🇩🇪 Deutsch (Deutschland)",
            "el_GR.UTF-8": "🇬🇷 Ελληνικά (Ελλάδα)",
            "gu_IN.UTF-8": "🇮🇳 ગુજરાતી (ભારત)",
            "he_IL.UTF-8": "🇮🇱 עברית (ישראל)",
            "hi_IN.UTF-8": "🇮🇳 हिन्दी (भारत)",
            "hu_HU.UTF-8": "🇭🇺 Magyar (Magyarország)",
            "is_IS.UTF-8": "🇮🇸 Íslenska (Ísland)",
            "id_ID.UTF-8": "🇮🇩 Bahasa Indonesia (Indonesia)",
            "it_IT.UTF-8": "🇮🇹 Italiano (Italia)",
            "ja_JP.UTF-8": "🇯🇵 日本語 (日本)",
            "ko_KR.UTF-8": "🇰🇷 한국어 (대한민국)",
            "pl_PL.UTF-8": "🇵🇱 Polski (Polska)",
            "pt_BR.UTF-8": "🇧🇷 Português (Brasil)",
            "ru_RU.UTF-8": "🇷🇺 Русский (Россия)",
            "es_ES.UTF-8": "🇪🇸 Español (España)",
            "sv_SE.UTF-8": "🇸🇪 Svenska (Sverige)",
            "tr_TR.UTF-8": "🇹🇷 Türkçe (Türkiye)",
            "uk_UA.UTF-8": "🇺🇦 Українська (Україна)",
            "vi_VN.UTF-8": "🇻🇳 Tiếng Việt (Việt Nam)",
        }

        self.combo = Gtk.ComboBoxText()
        for code, name in sorted(self.languages.items()):
            self.combo.append(code, name)
        self.combo.set_active_id("en_US.UTF-8")
        box.append(self.combo)

        # przyciski
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        btn_box.set_halign(Gtk.Align.CENTER)
        box.append(btn_box)

        btn_back = Gtk.Button(label="← Back")
        btn_back.connect("clicked", self.on_back)
        btn_box.append(btn_back)

        btn_next = Gtk.Button(label="Next →")
        btn_next.add_css_class("suggested-action")
        btn_next.connect("clicked", self.on_next)
        btn_box.append(btn_next)

    def on_back(self, button):
        self.app.go_to("welcome")

    def on_next(self, button):
        selected = self.combo.get_active_id()
        self.app.selected_language = selected
        print(f"[Pelican Installer] Selected language: {selected}")
        self.app.go_to("timezone")

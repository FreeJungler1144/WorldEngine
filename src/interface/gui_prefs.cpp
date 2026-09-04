#include "gui_prefs.hpp"

#include <cstdlib>
#include <fstream>

#include <nlohmann/json.hpp>

// Only for effective_theme(), which has to ask Windows which way the
// system theme is set. Nothing else in this file touches the platform.
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

namespace inop {
namespace gui {

const char* const kPrefsPath = "inop.gui.json";

namespace {

// Written as names rather than integers so the file stays legible and a
// future reordering of the enums cannot silently reinterpret a saved
// value as a different setting.
const char* theme_name(Theme t) {
    switch (t) {
        case Theme::Light: return "light";
        case Theme::Dark: return "dark";
        default: return "system";
    }
}

// An older preferences file holds "dark" or "light" and keeps meaning
// exactly what it did. Only an unrecognised value lands on System, which
// is also what a fresh install gets.
Theme theme_from(const std::string& s) {
    if (s == "light") return Theme::Light;
    if (s == "dark") return Theme::Dark;
    return Theme::System;
}

const char* colourblind_name(ColourblindMode m) {
    switch (m) {
        case ColourblindMode::Protanopia: return "protanopia";
        case ColourblindMode::Deuteranopia: return "deuteranopia";
        case ColourblindMode::Tritanopia: return "tritanopia";
        case ColourblindMode::Achromatopsia: return "achromatopsia";
        default: return "full";
    }
}

ColourblindMode colourblind_from(const std::string& s) {
    if (s == "protanopia") return ColourblindMode::Protanopia;
    if (s == "deuteranopia") return ColourblindMode::Deuteranopia;
    if (s == "tritanopia") return ColourblindMode::Tritanopia;
    if (s == "achromatopsia") return ColourblindMode::Achromatopsia;
    // The names these modes were saved under before they were given their
    // clinical ones. Read but never written, so a preferences file written
    // by an older build keeps working instead of silently reverting to
    // full colour. "red-green" becomes deuteranopia, the commoner of the
    // two it used to cover. "red-blue" and "blue-green" describe no
    // clinical type and have no successor, so they fall through. So does
    // "off", which is what full colour was called before it was named for
    // what it is rather than for what it is not.
    if (s == "red-green") return ColourblindMode::Deuteranopia;
    if (s == "monochrome") return ColourblindMode::Achromatopsia;
    return ColourblindMode::Full;
}

const char* window_mode_name(WindowMode m) {
    switch (m) {
        case WindowMode::BorderlessFullscreen: return "borderless";
        case WindowMode::Fullscreen: return "fullscreen";
        default: return "windowed";
    }
}

WindowMode window_mode_from(const std::string& s) {
    if (s == "borderless") return WindowMode::BorderlessFullscreen;
    if (s == "fullscreen") return WindowMode::Fullscreen;
    return WindowMode::Windowed;
}

std::string fonts_dir() {
    const char* windir = std::getenv("WINDIR");
    return windir ? std::string(windir) + "\\Fonts\\" : std::string("C:\\Windows\\Fonts\\");
}

bool font_present(const std::string& file) {
    std::ifstream f(fonts_dir() + file, std::ios::binary);
    return static_cast<bool>(f);
}

}  // namespace

Theme effective_theme(Theme t) {
    if (t != Theme::System) return t;
#if defined(_WIN32)
    // The value Windows itself uses for application chrome, as opposed to
    // the separate one for the taskbar and Start. Nonzero means light.
    // Read on every call rather than cached, so changing the system theme
    // while INOP is running is picked up the next time the palette is set
    // instead of needing a restart.
    DWORD light = 0;
    DWORD size = sizeof(light);
    if (RegGetValueW(HKEY_CURRENT_USER,
                     L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                     L"AppsUseLightTheme", RRF_RT_REG_DWORD, nullptr, &light,
                     &size) == ERROR_SUCCESS)
        return light ? Theme::Light : Theme::Dark;
#endif
    return Theme::Dark;
}

const std::vector<FontChoice>& available_fonts() {
    static const std::vector<FontChoice> found = [] {
        const FontChoice candidates[] = {
            {"Times New Roman", "times.ttf"}, {"Georgia", "georgia.ttf"},
            {"Segoe UI", "segoeui.ttf"},      {"Arial", "arial.ttf"},
            {"Verdana", "verdana.ttf"},       {"Tahoma", "tahoma.ttf"},
            {"Consolas", "consola.ttf"},
        };
        std::vector<FontChoice> out;
        for (const FontChoice& c : candidates)
            if (font_present(c.file)) out.push_back(c);
        return out;
    }();
    return found;
}

const std::vector<int>& zoom_steps() {
    // Dense near 100 and sparse at the extremes, which is what browsers and
    // Windows both ship: 25 points is a small relative change at 200% and a
    // large one at 75%, so uniform steps waste entries where they are least
    // useful. Every value here is reachable; the list stops where the
    // layouts stop.
    static const std::vector<int> v{50, 70, 80, 90, 100, 110, 120, 135, 150, 175, 200};
    return v;
}

// Raised from 125 to 175 once the settings and maintenance screens learned
// to scroll, and from 175 to 200 once the setup screen did too. That last
// one was the binding constraint: its header and top row are a fixed 300
// logical pixels, and the bottom row took whatever was left, so the higher
// the scale the less room the rotor rows had. The bottom row is laid out at
// its natural height now and everything under the header scrolls, so the
// fixed region can no longer squeeze anything off the screen.
//
// 200 is where the list stops rather than where the layouts do, because 200
// is the number SC 1.4.4 asks for and there is no demand past it. The
// ceiling and zoom_steps() must agree: a value offered but refused makes the
// control lie about what it can do.
const int kMaxSupportedZoom = 200;

bool operator==(const GuiPrefs& a, const GuiPrefs& b) {
    return a.theme == b.theme && a.colourblind == b.colourblind &&
           a.window_mode == b.window_mode && a.font_file == b.font_file &&
           a.zoom_percent == b.zoom_percent;
}

bool load_prefs(GuiPrefs& p, const std::string& path) {
    std::ifstream f(path);
    if (!f) return false;

    nlohmann::json j = nlohmann::json::parse(f, nullptr, false);
    if (j.is_discarded() || !j.is_object()) return false;

    GuiPrefs read;
    if (j.contains("theme") && j["theme"].is_string())
        read.theme = theme_from(j["theme"].get<std::string>());
    if (j.contains("colourblind") && j["colourblind"].is_string())
        read.colourblind = colourblind_from(j["colourblind"].get<std::string>());
    if (j.contains("window_mode") && j["window_mode"].is_string())
        read.window_mode = window_mode_from(j["window_mode"].get<std::string>());
    // A font the machine does not have would leave the window with no text
    // at all, so a saved name that is no longer installed falls back to the
    // default rather than being taken at its word.
    if (j.contains("font") && j["font"].is_string()) {
        std::string file = j["font"].get<std::string>();
        for (const FontChoice& c : available_fonts())
            if (c.file == file) read.font_file = file;
    }
    // Only a value the control could actually have produced is accepted:
    // a hand-edited 900 would otherwise scale the interface past anything
    // usable with no way back to the settings screen to undo it.
    if (j.contains("zoom") && j["zoom"].is_number_integer()) {
        int z = j["zoom"].get<int>();
        for (int step : zoom_steps())
            if (step == z) read.zoom_percent = z;
    }

    p = read;
    return true;
}

bool save_prefs(const GuiPrefs& p, const std::string& path) {
    nlohmann::json j;
    j["theme"] = theme_name(p.theme);
    j["colourblind"] = colourblind_name(p.colourblind);
    j["window_mode"] = window_mode_name(p.window_mode);
    j["font"] = p.font_file;
    j["zoom"] = p.zoom_percent;

    std::ofstream f(path);
    if (!f) return false;
    f << j.dump(2) << "\n";
    return static_cast<bool>(f);
}

}  // namespace gui
}  // namespace inop

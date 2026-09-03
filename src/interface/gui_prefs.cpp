#include "gui_prefs.hpp"

#include <cstdlib>
#include <fstream>

#include <nlohmann/json.hpp>

namespace inop {
namespace gui {

const char* const kPrefsPath = "inop.gui.json";

namespace {

// Written as names rather than integers so the file stays legible and a
// future reordering of the enums cannot silently reinterpret a saved
// value as a different setting.
const char* theme_name(Theme t) { return t == Theme::Light ? "light" : "dark"; }

Theme theme_from(const std::string& s) { return s == "light" ? Theme::Light : Theme::Dark; }

const char* colourblind_name(ColourblindMode m) {
    switch (m) {
        case ColourblindMode::Protanopia: return "protanopia";
        case ColourblindMode::Deuteranopia: return "deuteranopia";
        case ColourblindMode::Tritanopia: return "tritanopia";
        case ColourblindMode::Achromatopsia: return "achromatopsia";
        default: return "off";
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
    // off. "red-green" becomes deuteranopia, the commoner of the two it
    // used to cover. "red-blue" and "blue-green" describe no clinical type
    // and have no successor, so they fall through to off.
    if (s == "red-green") return ColourblindMode::Deuteranopia;
    if (s == "monochrome") return ColourblindMode::Achromatopsia;
    return ColourblindMode::Off;
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
    static const std::vector<int> v{50, 75, 100, 125, 150, 175, 200, 225, 250};
    return v;
}

const int kMaxSupportedZoom = 125;

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

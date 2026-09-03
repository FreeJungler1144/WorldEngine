#include "gui_settings_panel.hpp"

#include <algorithm>
#include <vector>

namespace inop {
namespace gui {

namespace {

constexpr float kMargin = 16.0f;
constexpr float kBtnW = 150.0f;
constexpr float kWideBtnW = 200.0f;
constexpr float kBtnH = 30.0f;
constexpr float kRowH = 30.0f;
constexpr float kRowGap = 8.0f;
constexpr float kSectionGap = 18.0f;
constexpr float kHeadingH = 30.0f;
constexpr float kColW = 840.0f;
constexpr float kLabelW = 250.0f;
constexpr float kCtrlW = 300.0f;
constexpr float kGap = 20.0f;

// Stable within one frame and unique across the panel, which is all
// dropdown() asks of them.
constexpr int kIdColourblind = 1;
constexpr int kIdFontSize = 2;
constexpr int kIdResolution = 3;
constexpr int kIdFont = 4;
constexpr int kIdTheme = 5;
constexpr int kIdLanguage = 6;
constexpr int kIdZoom = 7;

// The clinical names, each with the plain meaning after it: the operator
// who knows their diagnosis finds it by name, and the operator who does
// not can still tell which one describes them.
const std::vector<std::string>& colourblind_options() {
    static const std::vector<std::string> v{"Off", "Protanopia (red-blind)",
                                            "Deuteranopia (green-blind)",
                                            "Tritanopia (blue-yellow)",
                                            "Achromatopsia (no colour)"};
    return v;
}

const std::vector<std::string>& resolution_options() {
    static const std::vector<std::string> v{"Windowed", "Borderless fullscreen", "Fullscreen"};
    return v;
}

const std::vector<std::string>& theme_options() {
    static const std::vector<std::string> v{"Dark", "Light"};
    return v;
}

const std::vector<std::string>& font_size_options() {
    static const std::vector<std::string> v{"Small", "Normal", "Large"};
    return v;
}

// Zoom scales the whole interface, font size scales only the text, which
// is why they are two settings and not one. Percentages rather than
// Small/Normal/Large because a literal zoom has a literal factor. Built
// from zoom_steps() so the labels and the stored values cannot drift.
const std::vector<std::string>& zoom_options() {
    static const std::vector<std::string> v = [] {
        std::vector<std::string> out;
        for (int step : zoom_steps()) out.push_back(std::to_string(step) + "%");
        return out;
    }();
    return v;
}

int zoom_at(int idx) {
    const std::vector<int>& steps = zoom_steps();
    if (idx < 0 || idx >= static_cast<int>(steps.size())) return 100;
    return steps[static_cast<size_t>(idx)];
}

int index_of_zoom(int percent) {
    const std::vector<int>& steps = zoom_steps();
    int fallback = 0;
    for (size_t i = 0; i < steps.size(); ++i) {
        if (steps[i] == percent) return static_cast<int>(i);
        if (steps[i] == 100) fallback = static_cast<int>(i);
    }
    return fallback;
}

const std::vector<std::string>& language_options() {
    static const std::vector<std::string> v{"English"};
    return v;
}

const std::vector<std::string>& font_options() {
    static const std::vector<std::string> v = [] {
        std::vector<std::string> out;
        for (const FontChoice& c : available_fonts()) out.push_back(c.name);
        if (out.empty()) out.push_back("no system fonts found");
        return out;
    }();
    return v;
}

int index_of_font(const std::string& file) {
    const std::vector<FontChoice>& fonts = available_fonts();
    for (size_t i = 0; i < fonts.size(); ++i)
        if (fonts[i].file == file) return static_cast<int>(i);
    return 0;
}

ColourblindMode colourblind_at(int idx) {
    switch (idx) {
        case 1: return ColourblindMode::Protanopia;
        case 2: return ColourblindMode::Deuteranopia;
        case 3: return ColourblindMode::Tritanopia;
        case 4: return ColourblindMode::Achromatopsia;
        default: return ColourblindMode::Off;
    }
}

int index_of_colourblind(ColourblindMode m) {
    switch (m) {
        case ColourblindMode::Protanopia: return 1;
        case ColourblindMode::Deuteranopia: return 2;
        case ColourblindMode::Tritanopia: return 3;
        case ColourblindMode::Achromatopsia: return 4;
        default: return 0;
    }
}

WindowMode window_mode_at(int idx) {
    switch (idx) {
        case 1: return WindowMode::BorderlessFullscreen;
        case 2: return WindowMode::Fullscreen;
        default: return WindowMode::Windowed;
    }
}

int index_of_window_mode(WindowMode m) {
    switch (m) {
        case WindowMode::BorderlessFullscreen: return 1;
        case WindowMode::Fullscreen: return 2;
        default: return 0;
    }
}

// One section heading with the rule under it. Returns the y where the
// first row of the section starts.
float heading(float x, float y, const std::string& text) {
    label(Rect{x, y, kColW, kHeadingH}, text, false, Font::BodyLarge);
    float rule_y = y + kHeadingH - 2.0f;
    draw_rect(x, rule_y, kColW, 1.0f, palette::border());
    return y + kHeadingH + kRowGap;
}

// The left-hand caption every row carries, dimmed when the row is locked.
void row_label(float x, float y, const std::string& text, bool locked) {
    label(Rect{x, y, kLabelW, kRowH}, text, locked);
}

// The dim explanation to the right of a locked control, saying why it is
// locked rather than leaving the operator to guess.
void row_note(float x, float y, const std::string& text) {
    label(Rect{x + kLabelW + kGap + kCtrlW + kGap, y, kColW - kLabelW - kCtrlW - 2 * kGap, kRowH},
          text, true);
}

Rect control_rect(float x, float y) { return Rect{x + kLabelW + kGap, y, kCtrlW, kRowH}; }

}  // namespace

void SettingsPanel::open(const GuiPrefs& current) {
    pending_ = current;
    applied_ = current;
    colourblind_idx_ = index_of_colourblind(pending_.colourblind);
    window_mode_idx_ = index_of_window_mode(pending_.window_mode);
    theme_idx_ = pending_.theme == Theme::Light ? 1 : 0;
    font_idx_ = index_of_font(pending_.font_file);
    zoom_idx_ = index_of_zoom(pending_.zoom_percent);
    open_dropdown_id_ = -1;
    status_.clear();
    status_error_ = false;
    apply_pending_ = false;
}

bool SettingsPanel::take_apply_request(GuiPrefs* out) {
    if (!apply_pending_) return false;
    apply_pending_ = false;
    if (out) *out = pending_;
    applied_ = pending_;
    return true;
}

void SettingsPanel::set_status(const std::string& text, bool error) {
    status_ = text;
    status_error_ = error;
}

void SettingsPanel::frame(const GuiInput& in, int width, int height) {
    back_clicked_ = false;
    wordmark_clicked_ = false;

    float w = static_cast<float>(width), h = static_cast<float>(height);
    begin_widget_frame();
    clear(palette::background());

    // Whatever the popup wrote into the indices last frame becomes the
    // pending preferences before anything reads them, so the Apply button
    // and the enum fields agree with what is on screen.
    pending_.colourblind = colourblind_at(colourblind_idx_);
    pending_.window_mode = window_mode_at(window_mode_idx_);
    pending_.theme = theme_idx_ == 1 ? Theme::Light : Theme::Dark;
    pending_.zoom_percent = zoom_at(zoom_idx_);
    const std::vector<FontChoice>& fonts = available_fonts();
    if (!fonts.empty() && font_idx_ >= 0 && font_idx_ < static_cast<int>(fonts.size()))
        pending_.font_file = fonts[static_cast<size_t>(font_idx_)].file;
    if (pending_ != applied_) status_.clear();

    float top = draw_header(in, w);
    float x = std::max(kMargin, (w - kColW) * 0.5f);

    float y = draw_accessibility(in, x, top);
    y = draw_graphics(in, x, y + kSectionGap);
    y = draw_appearance(in, x, y + kSectionGap);
    y = draw_audio(x, y + kSectionGap);
    y = draw_interface(in, x, y + kSectionGap);

    // The button row follows the sections, but never off the bottom of a
    // short window.
    float by = std::min(y + kSectionGap, h - kMargin - kBtnH - 24.0f);

    bool dirty = pending_ != applied_;
    if (button(Rect{x, by, kBtnW, kBtnH}, "Apply", in, dirty, true)) apply_pending_ = true;

    bool at_defaults = pending_ == GuiPrefs{};
    if (button(Rect{x + kBtnW + kRowGap, by, kWideBtnW, kBtnH}, "Reset to default", in,
               !at_defaults)) {
        pending_ = GuiPrefs{};
        colourblind_idx_ = index_of_colourblind(pending_.colourblind);
        window_mode_idx_ = index_of_window_mode(pending_.window_mode);
        theme_idx_ = 0;
        font_idx_ = index_of_font(pending_.font_file);
        zoom_idx_ = index_of_zoom(pending_.zoom_percent);
        status_.clear();
    }

    if (!status_.empty()) {
        Rect status_r{x, by + kBtnH + 6.0f, kColW, kRowH};
        if (status_error_) {
            draw_rect(status_r.x, status_r.y, kColW, kRowH, palette::error_bg());
            draw_text(Font::Body, status_r.x + 6.0f,
                      status_r.y + (kRowH + text_line_height(Font::Body) * 0.7f) * 0.5f, status_,
                      palette::error_text());
        } else {
            label(status_r, status_, true);
        }
    } else if (dirty) {
        label(Rect{x, by + kBtnH + 6.0f, kColW, kRowH}, "Not applied yet.", true);
    }

    draw_open_dropdown_popup(in, open_dropdown_id_);

    // Again after the popup, so a pick made this frame is not left sitting
    // only in the index until the next one.
    pending_.colourblind = colourblind_at(colourblind_idx_);
    pending_.window_mode = window_mode_at(window_mode_idx_);
    pending_.theme = theme_idx_ == 1 ? Theme::Light : Theme::Dark;
    pending_.zoom_percent = zoom_at(zoom_idx_);
    if (!fonts.empty() && font_idx_ >= 0 && font_idx_ < static_cast<int>(fonts.size()))
        pending_.font_file = fonts[static_cast<size_t>(font_idx_)].file;

    end_widget_frame(in);
}

float SettingsPanel::draw_header(const GuiInput& in, float width) {
    const float pad = 6.0f;
    // Same shape as every other screen: the way back on the left, the
    // wordmark on the right, what this screen is in between.
    Rect back_r{kMargin, pad, kBtnW, kBtnH};
    if (button(back_r, "Back", in, true)) back_clicked_ = true;

    float word_tw = text_width(Font::Wordmark, "INOP");
    float word_th = text_line_height(Font::Wordmark);
    Rect wordmark_r{width - kMargin - (word_tw + 24.0f), pad, word_tw + 24.0f, word_th + 12.0f};
    if (wordmark_button(wordmark_r, in)) wordmark_clicked_ = true;

    float gap_x0 = back_r.x + back_r.w + 20.0f;
    float gap_x1 = wordmark_r.x - 20.0f;
    float title_tw = text_width(Font::BodyLarge, "Settings");
    float title_x = gap_x0 + std::max(0.0f, (gap_x1 - gap_x0 - title_tw) * 0.5f);
    label(Rect{title_x, pad, title_tw, word_th + 12.0f}, "Settings", false, Font::BodyLarge);

    return pad + word_th + 12.0f + 10.0f;
}

float SettingsPanel::draw_accessibility(const GuiInput& in, float x, float y) {
    y = heading(x, y, "Accessibility");

    row_label(x, y, "Arachnophobia mode", true);
    toggle(control_rect(x, y), arachnophobia_, "nothing in the interface to hide yet", in, false);
    y += kRowH + kRowGap;

    row_label(x, y, "Colourblind mode", false);
    dropdown(control_rect(x, y), colourblind_options(), colourblind_idx_, kIdColourblind,
             open_dropdown_id_, in, true);
    y += kRowH + kRowGap;

    row_label(x, y, "Font size", true);
    dropdown(control_rect(x, y), font_size_options(), font_size_idx_, kIdFontSize,
             open_dropdown_id_, in, false);
    row_note(x, y, "waiting on the panel layouts to scale");
    y += kRowH;

    return y;
}

float SettingsPanel::draw_graphics(const GuiInput& in, float x, float y) {
    y = heading(x, y, "Graphics");

    row_label(x, y, "Resolution mode", false);
    dropdown(control_rect(x, y), resolution_options(), window_mode_idx_, kIdResolution,
             open_dropdown_id_, in, true);
    y += kRowH + kRowGap;

    row_label(x, y, "Zoom", false);
    dropdown(control_rect(x, y), zoom_options(), zoom_idx_, kIdZoom, open_dropdown_id_, in, true);
    // Said before Apply rather than only after it, so the refusal is not a
    // surprise. gui.cpp still enforces it — this is the warning, not the
    // check.
    if (zoom_at(zoom_idx_) > kMaxSupportedZoom)
        row_note(x, y, "above " + std::to_string(kMaxSupportedZoom) +
                           "% the panels do not fit a window this size yet");
    y += kRowH + kRowGap;

    row_label(x, y, "Reduced motion", true);
    toggle(control_rect(x, y), reduced_motion_, "nothing animates yet", in, false);
    y += kRowH;

    return y;
}

float SettingsPanel::draw_appearance(const GuiInput& in, float x, float y) {
    y = heading(x, y, "Appearance");

    bool have_fonts = !available_fonts().empty();
    row_label(x, y, "Font family", !have_fonts);
    dropdown(control_rect(x, y), font_options(), font_idx_, kIdFont, open_dropdown_id_, in,
             have_fonts);
    if (!have_fonts) row_note(x, y, "no usable font file in the system font folder");
    y += kRowH + kRowGap;

    row_label(x, y, "Light / dark mode", false);
    dropdown(control_rect(x, y), theme_options(), theme_idx_, kIdTheme, open_dropdown_id_, in,
             true);
    y += kRowH;

    return y;
}

float SettingsPanel::draw_audio(float x, float y) {
    y = heading(x, y, "Audio");
    label(Rect{x, y, kColW, kRowH}, "The application makes no sound yet, so there is nothing here.",
          true);
    return y + kRowH;
}

float SettingsPanel::draw_interface(const GuiInput& in, float x, float y) {
    y = heading(x, y, "Interface");

    row_label(x, y, "Interface language", true);
    dropdown(control_rect(x, y), language_options(), language_idx_, kIdLanguage, open_dropdown_id_,
             in, false);
    row_note(x, y, "locked to English until there are translations");
    y += kRowH;

    return y;
}

}  // namespace gui
}  // namespace inop

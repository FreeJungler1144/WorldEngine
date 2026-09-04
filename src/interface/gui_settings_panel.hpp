// gui_settings_panel.hpp — the application settings screen, reached from
// the main menu.
//
// Edits GuiPrefs, nothing else. It never repaints the application itself:
// a change stays pending inside this panel until Apply is clicked, at
// which point the new preferences are handed to gui.cpp, which owns the
// window, the font atlases and the palette and is the only place allowed
// to touch them. Leaving the screen with something unapplied discards it.
//
// Several rows are drawn locked on purpose. They are the settings the
// operator has asked for whose subject does not exist yet — there is no
// sound to switch off, nothing animates, no translation to switch to —
// and showing them disabled says that more honestly than leaving them out
// and more honestly than a live control that quietly does nothing.
#pragma once

#include <string>

#include "gui_prefs.hpp"
#include "gui_widgets.hpp"

namespace inop {
namespace gui {

class SettingsPanel {
public:
    // Loads the screen with the preferences currently in force. Pending
    // edits from a previous visit are dropped, which is what makes
    // leaving the screen a cancel.
    void open(const GuiPrefs& current);

    // width/height are the current framebuffer size in pixels.
    void frame(const GuiInput& in, int width, int height);

    // True the frame Back was clicked — caller returns to the main menu.
    bool back_clicked() const { return back_clicked_; }
    // True the frame the INOP wordmark was clicked — caller returns to the
    // main menu.
    bool wordmark_clicked() const { return wordmark_clicked_; }

    // True the frame Apply was clicked, handing over the preferences to
    // put in force and store. Consumed by the call, like the clipboard
    // requests on the enciphering screen.
    bool take_apply_request(GuiPrefs* out);

    // What actually happened, reported back by whoever applied it, and
    // drawn under the buttons until the next edit. `error` picks the
    // failure colour.
    void set_status(const std::string& text, bool error);

private:
    float draw_header(const GuiInput& in, float width);
    // Each draws one section downward from `y` and returns the y just past
    // it, so the sections stack down one column.
    float draw_accessibility(const GuiInput& in, float x, float y);
    float draw_graphics(const GuiInput& in, float x, float y);
    float draw_appearance(const GuiInput& in, float x, float y);
    float draw_audio(float x, float y);
    float draw_interface(const GuiInput& in, float x, float y);

    // Pending is what the controls edit; applied is what was in force when
    // the screen opened or when Apply last succeeded. Apply is only
    // offered when they differ.
    GuiPrefs pending_;
    GuiPrefs applied_;

    // Dropdown selections are indices into the option lists, so they are
    // kept beside the enums rather than derived every frame.
    int colourblind_idx_ = 0;
    int window_mode_idx_ = 0;
    int theme_idx_ = 0;
    int font_idx_ = 0;
    int zoom_idx_ = 0;

    // Locked rows still need somewhere for the widget to write, since the
    // widget set takes a reference. Nothing reads these.
    bool arachnophobia_ = false;
    bool reduced_motion_ = false;
    int font_size_idx_ = 1;  // Normal
    int language_idx_ = 0;

    // How far the content is scrolled, and how tall it measured last frame.
    // The second is what the clamp needs and can only be known after a
    // layout pass, so it lags by one frame by construction.
    float scroll_ = 0.0f;
    float content_h_ = 0.0f;

    int open_dropdown_id_ = -1;
    std::string status_;
    bool status_error_ = false;
    bool apply_pending_ = false;
    bool back_clicked_ = false;
    bool wordmark_clicked_ = false;
};

}  // namespace gui
}  // namespace inop

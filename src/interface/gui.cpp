// gui.cpp — GLFW window/context creation and the main loop for the
// optional GUI. Compiled only when INOP_WITH_GUI is ON.
#include "gui.hpp"

#include <iostream>
#include <string>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
// Older MinGW/SDK headers may not declare this constant even though the
// function exists on Windows 10 1703+. Without it, a DPI-unaware process
// gets its window bitmap-scaled by DWM at non-100% display scaling — the
// window looks shrunk and content clips at the edges, because GLFW still
// lays widgets out for the full pixel size while DWM presents a scaled
// copy. Declaring per-monitor-v2 awareness up front avoids that entirely.
#ifndef DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
#define DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 ((HANDLE)-4)
#endif
#endif

// IMPORTANT: no GLFW_CONTEXT_VERSION_MAJOR/MINOR or GLFW_OPENGL_PROFILE
// hints are ever set below. Requesting a specific version/profile from
// GLFW would silently break every fixed-function draw call in
// gui_render.cpp (glBegin/glOrtho/glTexImage2D/...) — see gui_render.hpp's
// header comment for the full reasoning. Leaving these hints untouched is
// what makes WGL hand back the driver's default compatibility context.
#include <GLFW/glfw3.h>

#include "gui_enciphering_panel.hpp"
#include "gui_main_menu.hpp"
#include "gui_maintenance_panel.hpp"
#include "gui_prefs.hpp"
#include "gui_render.hpp"
#include "gui_settings_panel.hpp"
#include "gui_setup_panel.hpp"
#include "gui_widgets.hpp"

namespace inop {

namespace {

gui::GuiInput g_input;

void char_callback(GLFWwindow*, unsigned int codepoint) { g_input.typed.push_back(codepoint); }

void key_callback(GLFWwindow*, int key, int /*scancode*/, int action, int /*mods*/) {
    if (action != GLFW_PRESS && action != GLFW_REPEAT) return;
    if (key == GLFW_KEY_BACKSPACE) g_input.key_backspace = true;
    if (key == GLFW_KEY_ENTER || key == GLFW_KEY_KP_ENTER) g_input.key_enter = true;
    if (key == GLFW_KEY_ESCAPE) g_input.key_escape = true;
}

void scroll_callback(GLFWwindow*, double /*xoffset*/, double yoffset) { g_input.scroll_y += yoffset; }

void framebuffer_size_callback(GLFWwindow*, int width, int height) { gui::set_viewport(width, height); }

// Where the window sits and how big it is while it is an ordinary window,
// captured once at startup. Going fullscreen throws that away, so it is
// kept here to come back to rather than re-derived from a window that is
// currently covering the whole screen.
struct WindowedGeometry {
    int x = 0, y = 0, w = 0, h = 0;
};

void apply_window_mode(GLFWwindow* window, gui::WindowMode mode, const WindowedGeometry& geom) {
    GLFWmonitor* monitor = glfwGetPrimaryMonitor();
    const GLFWvidmode* vm = monitor ? glfwGetVideoMode(monitor) : nullptr;
    switch (mode) {
        case gui::WindowMode::Fullscreen:
            // Exclusive: the window takes the monitor, at the mode the
            // monitor is already running, so no resolution switch happens
            // and nothing else on the desktop gets rearranged.
            if (monitor && vm)
                glfwSetWindowMonitor(window, monitor, 0, 0, vm->width, vm->height,
                                     vm->refreshRate);
            break;
        case gui::WindowMode::BorderlessFullscreen: {
            // Still an ordinary window as far as the compositor is
            // concerned, just an undecorated one covering the monitor,
            // which is what keeps alt-tab and overlays behaving.
            if (!vm) break;
            int mx = 0, my = 0;
            glfwGetMonitorPos(monitor, &mx, &my);
            // Decoration comes off first: asking for the monitor size
            // while the window still has a title bar sizes the frame,
            // not the content, and taking the bar away afterwards leaves
            // the window short by exactly the height of the bar.
            glfwSetWindowAttrib(window, GLFW_DECORATED, GLFW_FALSE);
            glfwSetWindowMonitor(window, nullptr, mx, my, vm->width, vm->height, 0);
            break;
        }
        case gui::WindowMode::Windowed:
        default:
            glfwSetWindowMonitor(window, nullptr, geom.x, geom.y, geom.w, geom.h, 0);
            glfwSetWindowAttrib(window, GLFW_DECORATED, GLFW_TRUE);
            break;
    }
}

}  // namespace

bool gui_available() { return true; }

// Every failure path below returns Terminal rather than Quit. The program
// now opens on the window, so a machine that cannot start GLFW at all
// would otherwise have no way to reach the cipher — falling through to the
// terminal keeps a broken graphics stack from making the whole binary
// unusable.
GuiExit run_gui_settings() {
#if defined(_WIN32)
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
#endif

    if (!glfwInit()) {
        std::cerr << "gui: glfwInit failed\n";
        return GuiExit::Terminal;
    }

    GLFWwindow* window = glfwCreateWindow(1400, 950, "INOP", nullptr, nullptr);
    if (!window) {
        std::cerr << "gui: glfwCreateWindow failed\n";
        glfwTerminate();
        return GuiExit::Terminal;
    }

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    glfwSetCharCallback(window, char_callback);
    glfwSetKeyCallback(window, key_callback);
    glfwSetScrollCallback(window, scroll_callback);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    gui::render_init();

    // Preferences decide how everything below looks, so they are read
    // before the first atlas is baked and the first frame is drawn. A
    // first run has no file and gets the defaults.
    gui::GuiPrefs prefs;
    gui::load_prefs(prefs);
    gui::palette::set_palette(prefs.theme, prefs.colourblind);

    if (!gui::load_fonts(prefs.font_file)) {
        // A stored typeface that has since been uninstalled must not cost
        // the operator the whole application, so the default is tried
        // before giving up.
        std::cerr << "gui: could not load font '" << prefs.font_file << "' — trying the default\n";
        prefs.font_file = gui::GuiPrefs{}.font_file;
        if (!gui::load_fonts(prefs.font_file)) {
            std::cerr << "gui: could not load system font (times.ttf) — closing\n";
            glfwDestroyWindow(window);
            glfwTerminate();
            return GuiExit::Terminal;
        }
    }

    // Captured before any fullscreen switch, so Windowed has somewhere to
    // come back to.
    WindowedGeometry geom;
    glfwGetWindowPos(window, &geom.x, &geom.y);
    glfwGetWindowSize(window, &geom.w, &geom.h);
    if (prefs.window_mode != gui::WindowMode::Windowed)
        apply_window_mode(window, prefs.window_mode, geom);

    int fb_w = 0, fb_h = 0;
    glfwGetFramebufferSize(window, &fb_w, &fb_h);
    gui::set_viewport(fb_w, fb_h);

    gui::SetupPanel panel;
    gui::MainMenu main_menu;
    gui::EncipheringPanel enciphering;
    gui::SettingsPanel settings;
    gui::MaintenancePanel maintenance;
    // Owned here, not by any screen — a screen only knows how to signal
    // "the operator picked me" (open_inop_requested()/wordmark_clicked()/
    // next_clicked()/back_clicked()/exit_requested()), not what that means
    // for what gets shown next. See the header comment of
    // gui_setup_panel.hpp for why the screens themselves stay this narrow.
    // The GUI opens on MainMenu, not Setup directly.
    enum class Screen { MainMenu, Setup, Enciphering, Settings, Maintenance };
    Screen screen = Screen::MainMenu;
    bool mouse_down_prev = false;
    // Quit unless the operator specifically asks for the terminal: the
    // window close button and Esc are both ways of saying "I am done", and
    // only the Terminal button means "carry on somewhere else".
    GuiExit exit_reason = GuiExit::Quit;

    // Modals belong to this loop rather than to a screen, because they
    // cover the whole window and the screen underneath must not react
    // while one is up. Only one is ever open.
    enum class Modal { None, ConfirmQuit, ZoomUnsupported };
    Modal modal = Modal::None;

    gui::set_ui_scale(static_cast<float>(prefs.zoom_percent) / 100.0f);

    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        // Cursor position arrives in real pixels while every widget lays
        // itself out in logical units, so it has to come back through the
        // zoom before any hit test sees it.
        const float scale = gui::ui_scale();
        double mx = 0, my = 0;
        glfwGetCursorPos(window, &mx, &my);
        g_input.mouse_x = mx / scale;
        g_input.mouse_y = my / scale;

        bool mouse_down_cur = glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS;
        g_input.mouse_pressed = mouse_down_cur && !mouse_down_prev;
        g_input.mouse_released = !mouse_down_cur && mouse_down_prev;
        mouse_down_prev = mouse_down_cur;

        g_input.ctrl_held =
            glfwGetKey(window, GLFW_KEY_LEFT_CONTROL) == GLFW_PRESS ||
            glfwGetKey(window, GLFW_KEY_RIGHT_CONTROL) == GLFW_PRESS;

        glfwGetFramebufferSize(window, &fb_w, &fb_h);
        // The size the screens are told about is the logical one, so a
        // panel centring itself in "the window" centres in what the
        // operator can actually see at this zoom.
        const int lw = static_cast<int>(static_cast<float>(fb_w) / scale);
        const int lh = static_cast<int>(static_cast<float>(fb_h) / scale);

        // While a modal is up the screen behind still draws, so it stays
        // visible under the dimming, but it must not react to anything.
        gui::GuiInput screen_input = g_input;
        if (modal != Modal::None) {
            screen_input.mouse_pressed = false;
            screen_input.mouse_released = false;
            screen_input.typed.clear();
            screen_input.key_backspace = false;
            screen_input.key_enter = false;
            screen_input.key_escape = false;
            screen_input.scroll_y = 0;
        }

        if (screen == Screen::Setup) {
            panel.frame(screen_input, lw, lh);
            if (panel.wordmark_clicked()) screen = Screen::MainMenu;
            if (panel.next_clicked()) {
                enciphering.open(panel.state());
                screen = Screen::Enciphering;
            }
        } else if (screen == Screen::Enciphering) {
            enciphering.frame(screen_input, lw, lh);
            // The clipboard is the one thing the screen needs GLFW for,
            // and GLFW stays in this file, so the screen asks and this
            // loop answers.
            std::string copy;
            if (enciphering.take_copy_request(&copy)) glfwSetClipboardString(window, copy.c_str());
            if (enciphering.paste_requested()) {
                const char* pasted = glfwGetClipboardString(window);
                enciphering.deliver_paste(pasted ? pasted : "");
            }
            if (enciphering.back_clicked()) screen = Screen::Setup;
            if (enciphering.wordmark_clicked()) screen = Screen::MainMenu;
        } else if (screen == Screen::Settings) {
            settings.frame(screen_input, lw, lh);
            // The screen edits preferences and asks; the window, the font
            // atlases and the palette are all owned here, so putting a
            // change into force is this loop's job, the same way the
            // clipboard is.
            gui::GuiPrefs next;
            if (settings.take_apply_request(&next)) {
                bool font_ok = true;
                if (next.font_file != prefs.font_file &&
                    !gui::load_fonts(next.font_file)) {
                    gui::load_fonts(prefs.font_file);
                    next.font_file = prefs.font_file;
                    font_ok = false;
                }
                gui::palette::set_palette(next.theme, next.colourblind);
                if (next.window_mode != prefs.window_mode)
                    apply_window_mode(window, next.window_mode, geom);

                // The zoom ceiling is enforced here rather than in the
                // settings screen because it is a fact about the window,
                // which this loop owns. Refusing the value outright and
                // saying so beats applying a scale that puts half a panel
                // past the bottom edge with no way to reach the control
                // that would undo it.
                bool zoom_refused = false;
                if (next.zoom_percent > gui::kMaxSupportedZoom) {
                    next.zoom_percent = prefs.zoom_percent;
                    zoom_refused = true;
                    modal = Modal::ZoomUnsupported;
                }
                if (next.zoom_percent != prefs.zoom_percent)
                    gui::set_ui_scale(static_cast<float>(next.zoom_percent) / 100.0f);

                prefs = next;
                bool saved = gui::save_prefs(prefs);
                // Reopened so the screen shows what is actually in force,
                // which after a failed font is not quite what was asked
                // for.
                settings.open(prefs);
                if (!font_ok)
                    settings.set_status("That font could not be read. Everything else applied.",
                                        true);
                else if (zoom_refused)
                    settings.set_status("Everything except the zoom applied.", true);
                else if (!saved)
                    settings.set_status("Applied, but inop.gui.json could not be written.", true);
                else
                    settings.set_status("Applied, and saved to inop.gui.json.", false);
            }
            if (settings.back_clicked() || settings.wordmark_clicked()) screen = Screen::MainMenu;
        } else if (screen == Screen::Maintenance) {
            // Nothing to answer for this screen: it writes wheel files and
            // key sheets itself, and needs neither the window, the fonts
            // nor the clipboard to do it.
            maintenance.frame(screen_input, lw, lh);
            if (maintenance.back_clicked() || maintenance.wordmark_clicked())
                screen = Screen::MainMenu;
        } else {
            main_menu.frame(screen_input, lw, lh);
            if (main_menu.open_inop_requested()) screen = Screen::Setup;
            if (main_menu.maintenance_requested()) {
                maintenance.open();
                screen = Screen::Maintenance;
            }
            if (main_menu.settings_requested()) {
                settings.open(prefs);
                screen = Screen::Settings;
            }
            if (main_menu.terminal_requested()) {
                exit_reason = GuiExit::Terminal;
                glfwSetWindowShouldClose(window, GLFW_TRUE);
            }
            if (main_menu.exit_requested()) {
                if (g_input.ctrl_held) glfwSetWindowShouldClose(window, GLFW_TRUE);
                else modal = Modal::ConfirmQuit;
            }
        }

        // Escape, but only when no modal is already holding it — an open
        // modal answers the key itself. Holding Control skips the question,
        // which is the bargain every warning in this interface offers.
        if (modal == Modal::None && g_input.key_escape) {
            if (g_input.ctrl_held) {
                glfwSetWindowShouldClose(window, GLFW_TRUE);
            } else if (screen != Screen::MainMenu) {
                // A sub-screen has somewhere to go back to, so Escape means
                // up rather than out. Only the main menu, which has nothing
                // above it, reads Escape as leaving.
                screen = Screen::MainMenu;
            } else {
                modal = Modal::ConfirmQuit;
            }
        }

        // Modals draw last so they sit over whichever screen is behind, and
        // they get the real input that the screen was just denied.
        if (modal == Modal::ConfirmQuit) {
            gui::ModalChoice choice = gui::modal_question(
                static_cast<float>(lw), static_cast<float>(lh), "Quit INOP?",
                "Anything you have not saved will be lost.", "Quit", "Cancel", g_input);
            if (choice == gui::ModalChoice::Confirm)
                glfwSetWindowShouldClose(window, GLFW_TRUE);
            else if (choice == gui::ModalChoice::Cancel)
                modal = Modal::None;
        } else if (modal == Modal::ZoomUnsupported) {
            if (gui::modal_notice(static_cast<float>(lw), static_cast<float>(lh),
                                  "That zoom is not supported yet",
                                  "Above " + std::to_string(gui::kMaxSupportedZoom) +
                                      "% the panels do not fit the window. Zoom left unchanged.",
                                  g_input))
                modal = Modal::None;
        }

        glfwSwapBuffers(window);

        // Edge-triggered/accumulated input has now been consumed for this
        // frame — clear it before the next poll picks up new events.
        g_input.typed.clear();
        g_input.key_backspace = g_input.key_enter = g_input.key_escape = false;
        g_input.scroll_y = 0;
    }

    gui::render_shutdown();
    glfwDestroyWindow(window);
    glfwTerminate();
    return exit_reason;
}

}  // namespace inop

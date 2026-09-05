// gui.hpp — entry point for the optional GUI
//
// This header must never include any GL/GLFW types: it is included
// unconditionally by main.cpp regardless of whether the binary was built
// with INOP_WITH_GUI. Which .cpp actually defines run_gui_settings() (the
// real window in gui.cpp, or the one-line stub in gui_stub.cpp) is decided
// entirely by CMakeLists.txt's source list — main.cpp needs no #ifdef.
#pragma once

#include <functional>
#include <string>

namespace inop {

// Why the GUI closed, which is what decides whether the process ends or
// carries on into the terminal session. Exit, Esc and the window close
// button all mean Quit; only the main menu's Terminal button means the
// operator wants the CLI instead.
enum class GuiExit { Quit, Terminal };

// Whether this binary has a real GUI at all. True in gui.cpp, false in
// gui_stub.cpp, so main.cpp can decide whether to open on the window
// without an #ifdef. A CLI-only build answers false and goes straight to
// the terminal, silently — an unasked-for "no GUI support" line on every
// startup would be noise, whereas choosing the menu option and being told
// is useful.
bool gui_available();

// `script_path`, when it is not empty, names a file that fills the input
// struct instead of the pointer and the keyboard -- see gui_script.hpp.
// The window is still real and still visible; only the filling of the
// struct changes, and nothing else in the GUI can tell the difference.
//
// Opens the GUI window and blocks until the operator closes it. Opens on
// the main menu (gui_main_menu.hpp); "Open INOP" there leads to the
// machine setup screen (gui_setup_panel.hpp), whose own INOP wordmark
// leads back and whose "Next" button leads on to the enciphering screen
// (gui_enciphering_panel.hpp). Maintenance (gui_maintenance_panel.hpp) and
// Settings (gui_settings_panel.hpp) are both real screens now.
GuiExit run_gui_settings(const std::string& script_path = "");

// How one self-test check reports itself: whether it passed, and what it
// was. main.cpp owns the printing and the failure count, so the GUI half
// of the list reads exactly like the rest of it.
using SelfTestCheck = std::function<void(bool, const std::string&)>;

// The parts of the GUI that need no window at all: the preferences file,
// the script parser and the saved configuration store. Which .cpp defines
// this is the same source list choice that decides run_gui_settings(), so
// a CLI-only build links a version that checks nothing rather than failing
// to find the symbol.
void gui_self_test(const SelfTestCheck& check);

}  // namespace inop

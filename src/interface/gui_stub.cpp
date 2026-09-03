// gui_stub.cpp — compiled instead of gui.cpp when INOP_WITH_GUI is OFF.
// Keeps the CLI-only build's terminal menu identical in shape (option
// always listed) without linking GLFW/OpenGL/stb_truetype/nlohmann-json.
#include <iostream>

#include "gui.hpp"

namespace inop {

bool gui_available() { return false; }

GuiExit run_gui_settings() {
    std::cout << "  this build has no GUI support "
                 "(configure with -DINOP_WITH_GUI=ON and a vcpkg toolchain file)\n";
    // Terminal, not Quit: reaching here means the operator asked for the
    // window from the menu and cannot have it, which is a reason to stay
    // in the session rather than to end it. main.cpp never calls this at
    // startup in a stub build, because gui_available() said no.
    return GuiExit::Terminal;
}

}  // namespace inop

#include "gui_main_menu.hpp"

namespace inop {
namespace gui {

namespace {
constexpr float kMargin = 24.0f;
constexpr float kButtonW = 220.0f, kButtonH = 40.0f, kButtonGap = 14.0f;
}  // namespace

void MainMenu::frame(const GuiInput& in, int width, int height) {
    open_inop_requested_ = false;
    terminal_requested_ = false;
    maintenance_requested_ = false;
    settings_requested_ = false;
    exit_requested_ = false;

    float w = static_cast<float>(width), h = static_cast<float>(height);
    begin_widget_frame();
    clear(palette::background());

    // Title, top centre, just under the margin — reuses the Wordmark font
    // (44pt), the largest atlas baked; ask if this needs to be bigger than
    // the setup screen's own wordmark, since that would need a dedicated
    // font size.
    float title_tw = text_width(Font::Wordmark, "INOP");
    float title_th = text_line_height(Font::Wordmark);
    label(Rect{(w - title_tw) * 0.5f, kMargin, title_tw, title_th}, "INOP", false, Font::Wordmark);

    // Five buttons stacked in the screen's centre, in this order: Open
    // INOP, Terminal, Maintenance, Settings, Exit. Terminal sits directly
    // under Open INOP because the two are the same choice — which
    // interface to work in — and the rest of the stack is everything else.
    const int kCount = 5;
    float stack_h = kCount * kButtonH + (kCount - 1) * kButtonGap;
    float x = (w - kButtonW) * 0.5f;
    float y = (h - stack_h) * 0.5f;
    const float step = kButtonH + kButtonGap;

    Rect open_inop_r{x, y, kButtonW, kButtonH};
    if (button(open_inop_r, "Open INOP", in, true)) open_inop_requested_ = true;

    Rect terminal_r{x, y + step, kButtonW, kButtonH};
    if (button(terminal_r, "Terminal", in, true)) terminal_requested_ = true;

    Rect maintenance_r{x, y + 2 * step, kButtonW, kButtonH};
    if (button(maintenance_r, "Maintenance", in, true)) maintenance_requested_ = true;

    Rect settings_r{x, y + 3 * step, kButtonW, kButtonH};
    if (button(settings_r, "Settings", in, true)) settings_requested_ = true;

    Rect exit_r{x, y + 4 * step, kButtonW, kButtonH};
    if (button(exit_r, "Exit", in, true)) exit_requested_ = true;

    end_widget_frame(in);
}

}  // namespace gui
}  // namespace inop

// gui_anim.hpp -- the frame clock, and the per widget timers every
// animated widget reads.
//
// Immediate mode keeps no widget tree to hang state on, so the timers here
// are keyed on the rect a widget draws itself into rather than on an id
// every caller would have to invent and keep unique. That works because a
// rect is rebuilt from the same layout constants every frame and so comes
// out identical while nothing moves, and because a rect that has changed
// is a widget the pointer has left, which is exactly when a hover clock
// should start over.
//
// The highlight is driven by whichever rect claims it rather than by the
// hover test itself. A later arrow key navigation can then light a control
// by naming its rect, instead of needing a second highlight path beside
// this one.
#pragma once

#include "gui_widgets.hpp"

namespace inop {
namespace gui {

// Called once per frame by gui.cpp, before anything draws. Seconds, so no
// widget ever has to know what refresh rate it is running at.
void set_frame_dt(float dt);
float frame_dt();

// Whether motion is allowed at all. Reaches the widgets the same way the
// palette does: gui.cpp sets it at startup and again whenever the settings
// screen applies a change, and no widget keeps a copy of its own. With
// motion off every eased value below jumps to its endpoint instead of
// travelling there, and nothing that moves position moves at all.
//
// Hover timing keeps running either way, because a tooltip is information
// rather than motion and asking for less motion should not take it away.
void set_motion_enabled(bool enabled);
bool motion_enabled();

// Everything a widget needs to draw itself this frame.
struct WidgetMotion {
    float hover = 0.0f;        // 0 to 1, eased. The highlight.
    float press = 0.0f;        // 0 to 1, eased. The dip.
    float hovered_for = 0.0f;  // unbroken seconds of hover. The tooltip wait.
};

// Call once per widget per frame, before drawing it, whether or not the
// pointer is anywhere near it. The call is what keeps that rect alive; a
// rect that stops asking fades out and is forgotten.
WidgetMotion widget_motion(const Rect& r, const GuiInput& in);

// Advances every timer by one frame and retires the ones nothing is asking
// about any more. Called from begin_widget_frame(), so no screen has to
// remember to do it and no screen can do it twice.
void anim_begin_frame();

}  // namespace gui
}  // namespace inop

#include "gui_anim.hpp"

#include <algorithm>
#include <cmath>

namespace inop {
namespace gui {

namespace {

float g_dt = 0.0f;
bool g_motion = true;

// How long each ease takes end to end, in seconds. Both rises are quicker
// than their falls, which is the usual asymmetry: a control should feel
// like it answered at once and then let go unhurriedly.
constexpr float kHoverRise = 0.11f;
constexpr float kHoverFall = 0.17f;
constexpr float kPressRise = 0.05f;
constexpr float kPressFall = 0.13f;

// Rects are rebuilt from the same constants every frame and so match
// exactly while nothing moves. The tolerance is here for the frame a
// scroll offset lands on a fraction of a unit, not because the arithmetic
// is expected to drift.
constexpr float kSameRect = 0.5f;

struct Slot {
    Rect rect{0, 0, 0, 0};
    float hover = 0.0f;
    float press = 0.0f;
    float hovered_for = 0.0f;
    bool hovered_now = false;
    bool held_now = false;
    // Whether the press currently in flight started on this rect. A drag
    // that began somewhere else must not dip whatever it happens to pass
    // over on the way.
    bool pressed_here = false;
    bool used = false;
};

// One control is hovered and one is pressed at any moment, so the spare
// slots exist only for the ones still fading out behind the pointer. Eight
// is more than a pointer can leave behind at these speeds, and running out
// simply retires the faintest one, which is the one nobody can see.
constexpr int kSlots = 8;
Slot g_slots[kSlots];

bool same_rect(const Rect& a, const Rect& b) {
    return std::fabs(a.x - b.x) < kSameRect && std::fabs(a.y - b.y) < kSameRect &&
           std::fabs(a.w - b.w) < kSameRect && std::fabs(a.h - b.h) < kSameRect;
}

Slot* slot_for(const Rect& r) {
    for (Slot& s : g_slots)
        if (s.used && same_rect(s.rect, r)) return &s;
    for (Slot& s : g_slots)
        if (!s.used) {
            s = Slot{};
            s.rect = r;
            s.used = true;
            return &s;
        }
    Slot* faintest = &g_slots[0];
    for (Slot& s : g_slots)
        if (std::max(s.hover, s.press) < std::max(faintest->hover, faintest->press)) faintest = &s;
    *faintest = Slot{};
    faintest->rect = r;
    faintest->used = true;
    return faintest;
}

float advance(float value, bool toward_one, float rise, float fall) {
    if (!g_motion) return toward_one ? 1.0f : 0.0f;
    float step = g_dt / (toward_one ? rise : fall);
    value += toward_one ? step : -step;
    return std::clamp(value, 0.0f, 1.0f);
}

}  // namespace

void set_frame_dt(float dt) { g_dt = dt; }
float frame_dt() { return g_dt; }

void set_motion_enabled(bool enabled) { g_motion = enabled; }
bool motion_enabled() { return g_motion; }

void anim_begin_frame() {
    for (Slot& s : g_slots) {
        if (!s.used) continue;

        s.hover = advance(s.hover, s.hovered_now, kHoverRise, kHoverFall);
        s.hovered_for = s.hovered_now ? s.hovered_for + g_dt : 0.0f;

        // The dip holds only while the button is still down AND the
        // pointer is still on the control, so sliding off a held button
        // lets it back up, and sliding back on presses it again.
        bool dipped = s.pressed_here && s.held_now && s.hovered_now;
        s.press = advance(s.press, dipped, kPressRise, kPressFall);
        if (!s.held_now) s.pressed_here = false;

        // Nothing asked about it and nothing is left to draw, so the slot
        // goes back for a control the pointer has yet to reach.
        if (!s.hovered_now && s.hover <= 0.0f && s.press <= 0.0f) s.used = false;

        s.hovered_now = false;
        s.held_now = false;
    }
}

WidgetMotion widget_motion(const Rect& r, const GuiInput& in) {
    WidgetMotion out;
    // A control the pointer is not on costs no slot at all unless it is
    // still fading, which is what keeps a screen full of widgets down to
    // the handful the pointer has actually visited.
    if (!rect_contains(r, in.mouse_x, in.mouse_y)) {
        // With motion off nothing is left fading behind the pointer, so
        // there is nothing to look up either.
        if (!g_motion) return out;
        for (Slot& s : g_slots)
            if (s.used && same_rect(s.rect, r)) {
                out.hover = s.hover;
                out.press = s.press;
                break;
            }
        return out;
    }

    Slot* s = slot_for(r);
    s->hovered_now = true;
    if (in.mouse_held) s->held_now = true;
    if (in.mouse_pressed) {
        s->pressed_here = true;
        s->press = 0.0f;
    }

    if (!g_motion) {
        // Read from the state rather than from the timers. The timers are
        // advanced once per frame at the top of the frame, so a control
        // asked about on the frame the pointer arrives would otherwise
        // still answer with the value from before it got there. An ease
        // hides that frame; an instant change is exactly where it shows.
        out.hover = 1.0f;
        out.press = (s->pressed_here && in.mouse_held) ? 1.0f : 0.0f;
        out.hovered_for = s->hovered_for;
        s->hover = out.hover;
        s->press = out.press;
        return out;
    }

    out.hover = s->hover;
    out.press = s->press;
    out.hovered_for = s->hovered_for;
    return out;
}

}  // namespace gui
}  // namespace inop

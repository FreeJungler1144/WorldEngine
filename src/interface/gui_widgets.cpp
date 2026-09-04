#include "gui_widgets.hpp"

#include <algorithm>

namespace inop {
namespace gui {

bool rect_contains(const Rect& r, double mx, double my) {
    return mx >= r.x && mx <= r.x + r.w && my >= r.y && my <= r.y + r.h;
}

namespace {

const void* g_focus = nullptr;       // identity of the std::string* being edited
bool g_click_consumed_this_frame = false;

struct PendingDropdown {
    bool active = false;
    int id = -1;
    Rect box;
    const std::vector<std::string>* options = nullptr;
    int* selected = nullptr;
};
PendingDropdown g_pending;

// Scroll offset (pixels) for whichever dropdown popup is currently open.
// Reset to 0 whenever a *different* dropdown becomes the open one, so
// switching from a long rotor-picker list to another dropdown never
// starts mid-scrolled. Only one popup is ever open at a time, so a single
// shared offset (rather than one per dropdown id) is enough.
float g_popup_scroll = 0.0f;
int g_popup_scroll_owner = -1;

// Where the open dropdown popup was drawn on the previous frame, and
// whether there was one. A popup is drawn last so it sits on top, but
// every widget it covers has already run its own hit test by then, so
// without this the control underneath sees the click first and takes it:
// picking the fourth entry of a five-entry list would instead open
// whatever dropdown that row happened to be sitting over. The rect is a
// frame behind, which is exactly right — a popup has to have been drawn
// before it can be clicked.
//
// begin_widget_frame() ages one into the other every frame rather than
// leaving a rect set until something clears it. A screen with no
// dropdowns at all never calls draw_open_dropdown_popup, so a rect that
// stayed set would go on swallowing clicks there for the rest of the
// session — leaving the setup screen with a list open would have left a
// dead patch in the middle of the main menu.
Rect g_popup_rect_last{0, 0, 0, 0};
bool g_popup_shown_last = false;
bool g_popup_drawn_this_frame = false;

// True only between the first and last draw call of a modal. The popup
// guard below exists to stop a click landing on a control that happens to
// sit under an open dropdown popup; a modal is drawn over everything
// including that popup, so for its own buttons the guard is exactly wrong
// and would swallow the click that dismisses it.
bool g_in_modal = false;

bool click_over_open_popup(const GuiInput& in) {
    if (g_in_modal) return false;
    return g_popup_shown_last && rect_contains(g_popup_rect_last, in.mouse_x, in.mouse_y);
}

const float PAD = 6.0f;

}  // namespace

void begin_widget_frame() {
    g_click_consumed_this_frame = false;
    g_pending.active = false;
    g_popup_shown_last = g_popup_drawn_this_frame;
    g_popup_drawn_this_frame = false;
}

void end_widget_frame(const GuiInput& in) {
    if (in.mouse_pressed && !g_click_consumed_this_frame) g_focus = nullptr;
}

namespace palette {
namespace {

struct Colors {
    Color background, panel, border, border_invalid;
    Color text, text_dim, accent;
    Color disabled_bg, disabled_text;
    Color error_bg, error_text;
};

// The dark palette is the original one and stays the default. The light
// one is the same design at inverted lightness: the greys keep their
// spacing, so a panel still reads as raised off the background and a
// disabled control still reads as sunk into it.
Colors dark_base() {
    Colors c;
    c.background = rgba(0.09f, 0.09f, 0.10f);
    c.panel = rgba(0.14f, 0.14f, 0.16f);
    c.border = rgba(0.32f, 0.32f, 0.36f);
    c.border_invalid = rgba(0.75f, 0.30f, 0.28f);
    c.text = rgba(0.92f, 0.92f, 0.90f);
    c.text_dim = rgba(0.58f, 0.58f, 0.60f);
    c.accent = rgba(0.78f, 0.60f, 0.28f);  // brass/amber
    c.disabled_bg = rgba(0.16f, 0.16f, 0.17f);
    c.disabled_text = rgba(0.40f, 0.40f, 0.42f);
    c.error_bg = rgba(0.30f, 0.12f, 0.12f);
    c.error_text = rgba(0.92f, 0.70f, 0.70f);
    return c;
}

Colors light_base() {
    Colors c;
    c.background = rgba(0.93f, 0.92f, 0.90f);
    c.panel = rgba(0.99f, 0.98f, 0.96f);
    c.border = rgba(0.62f, 0.61f, 0.58f);
    c.border_invalid = rgba(0.70f, 0.18f, 0.16f);
    c.text = rgba(0.12f, 0.12f, 0.11f);
    c.text_dim = rgba(0.44f, 0.44f, 0.43f);
    c.accent = rgba(0.74f, 0.54f, 0.18f);
    c.disabled_bg = rgba(0.87f, 0.86f, 0.84f);
    c.disabled_text = rgba(0.58f, 0.58f, 0.57f);
    c.error_bg = rgba(0.97f, 0.86f, 0.85f);
    c.error_text = rgba(0.55f, 0.10f, 0.10f);
    return c;
}

// Only four colours in the palette carry a signal by hue: the accent (a
// control is focused, enabled, chosen), and the three that say something
// is wrong. Everything else is a neutral grey and reads the same under
// every condition, so a colourblind mode only ever touches these four.
//
// Each mode is named for the pair the operator cannot separate, so the
// rule is simply that the two signals must not be that pair. Under
// red-green the classic surviving pair is blue against orange; under
// red-blue, green against amber; under blue-green, brass against magenta.
// Monochrome has no hue left to use at all, so the two signals separate
// by lightness instead, which is the one channel every condition keeps.
void apply_colourblind(Colors& c, ColourblindMode mode, Theme theme) {
    const bool dark = theme == Theme::Dark;
    switch (mode) {
        // Protanopia and deuteranopia are both red-green deficiencies and
        // want the same thing: signalling that never asks red and green to
        // be told apart. Blue for "this is the way on", amber for "this is
        // wrong" — both survive either type, and they differ from each
        // other in hue and in luminance, so the pair is still separable if
        // the display is poor. Sharing one arm rather than inventing a
        // cosmetic difference between two conditions that need the same
        // remedy.
        case ColourblindMode::Protanopia:
        case ColourblindMode::Deuteranopia:
            c.accent = dark ? rgba(0.35f, 0.62f, 0.95f) : rgba(0.16f, 0.40f, 0.82f);
            c.border_invalid = dark ? rgba(0.92f, 0.58f, 0.12f) : rgba(0.78f, 0.45f, 0.04f);
            c.error_bg = dark ? rgba(0.32f, 0.20f, 0.03f) : rgba(0.99f, 0.90f, 0.75f);
            c.error_text = dark ? rgba(0.98f, 0.78f, 0.35f) : rgba(0.52f, 0.30f, 0.02f);
            break;
        case ColourblindMode::Tritanopia:
            // Blue against yellow is the pair that fails here, which rules
            // out both the default brass accent and the blue used above.
            // Red and green are seen normally, so the signalling moves
            // there: green for the way on, magenta for wrongness.
            c.accent = dark ? rgba(0.32f, 0.74f, 0.40f) : rgba(0.11f, 0.46f, 0.20f);
            c.border_invalid = dark ? rgba(0.88f, 0.28f, 0.68f) : rgba(0.72f, 0.10f, 0.50f);
            c.error_bg = dark ? rgba(0.30f, 0.08f, 0.22f) : rgba(0.99f, 0.85f, 0.94f);
            c.error_text = dark ? rgba(0.97f, 0.68f, 0.88f) : rgba(0.55f, 0.06f, 0.36f);
            break;
        case ColourblindMode::Achromatopsia:
            c.accent = dark ? rgba(0.70f, 0.70f, 0.70f) : rgba(0.42f, 0.42f, 0.42f);
            c.border_invalid = dark ? rgba(1.00f, 1.00f, 1.00f) : rgba(0.00f, 0.00f, 0.00f);
            c.error_bg = dark ? rgba(0.28f, 0.28f, 0.28f) : rgba(0.80f, 0.80f, 0.80f);
            c.error_text = dark ? rgba(1.00f, 1.00f, 1.00f) : rgba(0.04f, 0.04f, 0.04f);
            break;
        case ColourblindMode::Off:
        default:
            break;
    }
}

Colors g_current = dark_base();

}  // namespace

void set_palette(Theme theme, ColourblindMode mode) {
    Colors c = theme == Theme::Light ? light_base() : dark_base();
    apply_colourblind(c, mode, theme);
    g_current = c;
}

Color background() { return g_current.background; }
Color panel() { return g_current.panel; }
Color border() { return g_current.border; }
Color border_invalid() { return g_current.border_invalid; }
Color text() { return g_current.text; }
Color text_dim() { return g_current.text_dim; }
Color accent() { return g_current.accent; }
Color disabled_bg() { return g_current.disabled_bg; }
Color disabled_text() { return g_current.disabled_text; }
Color error_bg() { return g_current.error_bg; }
Color error_text() { return g_current.error_text; }

// Worked out from the accent rather than tabled alongside it: a blue or
// dark-green accent needs pale ink where brass needs near-black, and one
// forgotten table entry is an unreadable button. Coefficients are the
// usual perceived-brightness weights.
Color on_accent() {
    const Color a = g_current.accent;
    float luma = 0.299f * a.r + 0.587f * a.g + 0.114f * a.b;
    return luma > 0.55f ? rgba(0.10f, 0.09f, 0.07f) : rgba(0.98f, 0.98f, 0.97f);
}
}  // namespace palette

void label(const Rect& r, const std::string& text, bool dim, Font font) {
    float ty = r.y + (r.h + text_line_height(font) * 0.7f) * 0.5f;
    draw_text(font, r.x, ty, text, dim ? palette::text_dim() : palette::text());
}

bool button(const Rect& r, const std::string& text, const GuiInput& in, bool enabled,
            bool accent) {
    bool hovered = rect_contains(r, in.mouse_x, in.mouse_y);
    bool clicked = false;
    Color bg = !enabled ? palette::disabled_bg()
                         : (accent ? palette::accent() : palette::panel());
    draw_rect(r.x, r.y, r.w, r.h, bg);
    draw_rect_outline(r.x, r.y, r.w, r.h, palette::border());
    Color fg = !enabled ? palette::disabled_text()
                         : (accent ? palette::on_accent() : palette::text());
    float tw = text_width(Font::Body, text);
    float tx = r.x + (r.w - tw) * 0.5f;
    float ty = r.y + (r.h + text_line_height(Font::Body) * 0.7f) * 0.5f;
    draw_text(Font::Body, tx, ty, text, fg);
    if (enabled && hovered && in.mouse_pressed && !click_over_open_popup(in)) {
        clicked = true;
        g_click_consumed_this_frame = true;
    }
    return clicked;
}

bool wordmark_button(const Rect& r, const GuiInput& in) {
    bool hovered = rect_contains(r, in.mouse_x, in.mouse_y);
    if (hovered) draw_rect(r.x, r.y, r.w, r.h, palette::panel());
    draw_text(Font::Wordmark, r.x + 8, r.y + text_line_height(Font::Wordmark) * 0.75f, "INOP",
              palette::text());
    return hovered && in.mouse_pressed;
}

namespace {

// Widths add up exactly here: the baked atlas has no kerning, so one
// measurement per character is enough to know where a line ends.
std::vector<std::string> wrap_lines(float box_w, const std::string& text) {
    const float avail = std::max(0.0f, box_w - 2 * PAD);
    std::vector<std::string> lines;
    std::string cur;
    float cur_w = 0;
    size_t last_space = std::string::npos;
    for (char c : text) {
        if (c == '\n') {
            lines.push_back(cur);
            cur.clear();
            cur_w = 0;
            last_space = std::string::npos;
            continue;
        }
        float cw = text_width(Font::Body, std::string(1, c));
        if (cur_w + cw > avail && !cur.empty()) {
            if (c == ' ') {
                lines.push_back(cur);
                cur.clear();
                cur_w = 0;
                last_space = std::string::npos;
                continue;
            }
            if (last_space != std::string::npos) {
                lines.push_back(cur.substr(0, last_space));
                cur = cur.substr(last_space + 1);
                cur_w = text_width(Font::Body, cur);
                last_space = std::string::npos;
            } else {
                lines.push_back(cur);
                cur.clear();
                cur_w = 0;
            }
        }
        if (c == ' ') last_space = cur.size();
        cur.push_back(c);
        cur_w += cw;
    }
    if (!cur.empty() || lines.empty()) lines.push_back(cur);
    return lines;
}

float block_line_height() { return text_line_height(Font::Body) * 1.3f; }

}  // namespace

int text_block_lines(float box_w, const std::string& text) {
    return static_cast<int>(wrap_lines(box_w, text).size());
}

float text_block_height(int lines) {
    if (lines < 1) lines = 1;
    return static_cast<float>(lines) * block_line_height() + 2 * PAD;
}

int text_block(const Rect& r, const std::string& text, const GuiInput& in, float& scroll,
               bool dim) {
    draw_rect(r.x, r.y, r.w, r.h, palette::panel());
    draw_rect_outline(r.x, r.y, r.w, r.h, palette::border());

    std::vector<std::string> lines = wrap_lines(r.w, text);
    const float lh = block_line_height();
    const float content_h = static_cast<float>(lines.size()) * lh;

    // Compared against the whole box, not the box minus padding: a single
    // line in a field-height box is taller than the padded interior, and
    // treating that as overflow is what used to push it down far enough
    // for its descenders to touch the bottom edge.
    const float overflow = content_h - r.h;
    float top;
    if (overflow <= 0) {
        scroll = 0;
        top = r.y + (r.h - content_h) * 0.5f;
    } else {
        if (in.scroll_y != 0 && rect_contains(r, in.mouse_x, in.mouse_y))
            scroll -= static_cast<float>(in.scroll_y) * lh;
        if (scroll < 0) scroll = 0;
        if (scroll > overflow + 2 * PAD) scroll = overflow + 2 * PAD;
        top = r.y + PAD - scroll;
    }

    begin_scissor(r.x, r.y, r.w, r.h);
    float y = top;
    for (const std::string& line : lines) {
        if (y + lh > r.y && y < r.y + r.h)
            draw_text(Font::Body, r.x + PAD, y + lh * 0.75f, line,
                      dim ? palette::text_dim() : palette::text());
        y += lh;
    }
    end_scissor();
    return static_cast<int>(lines.size());
}

bool toggle(const Rect& r, bool& value, const std::string& text, const GuiInput& in,
            bool enabled) {
    bool changed = false;
    float box_size = r.h;
    Rect box{r.x, r.y, box_size, box_size};
    Color bg = !enabled ? palette::disabled_bg() : (value ? palette::accent() : palette::panel());
    draw_rect(box.x, box.y, box.w, box.h, bg);
    draw_rect_outline(box.x, box.y, box.w, box.h, palette::border());
    label(Rect{r.x + box_size + PAD, r.y, r.w - box_size - PAD, r.h}, text, !enabled);
    if (enabled && rect_contains(box, in.mouse_x, in.mouse_y) && in.mouse_pressed &&
        !click_over_open_popup(in)) {
        value = !value;
        changed = true;
        g_click_consumed_this_frame = true;
    }
    return changed;
}

bool text_field(const Rect& r, std::string& value, const GuiInput& in, const std::string& allowed,
                 size_t max_len, bool enabled, bool invalid, CaseFold case_fold,
                 const std::string& placeholder, bool center_text) {
    bool changed = false;
    bool focused = enabled && g_focus == static_cast<const void*>(&value);

    if (enabled && rect_contains(r, in.mouse_x, in.mouse_y) && in.mouse_pressed &&
        !click_over_open_popup(in)) {
        g_focus = &value;
        focused = true;
        g_click_consumed_this_frame = true;
    }

    if (focused) {
        if (in.key_backspace && !value.empty()) {
            value.pop_back();
            changed = true;
        }
        for (unsigned int cp : in.typed) {
            if (cp > 127) continue;
            char c = static_cast<char>(cp);
            if (case_fold == CaseFold::ToLower && c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
            else if (case_fold == CaseFold::ToUpper && c >= 'a' && c <= 'z') c = static_cast<char>(c - 'a' + 'A');
            if (value.size() >= max_len) continue;
            if (allowed.find(c) == std::string::npos) continue;
            value.push_back(c);
            changed = true;
        }
    }

    Color bg = !enabled ? palette::disabled_bg() : palette::panel();
    draw_rect(r.x, r.y, r.w, r.h, bg);
    Color border = invalid ? palette::border_invalid() : (focused ? palette::accent() : palette::border());
    draw_rect_outline(r.x, r.y, r.w, r.h, border, focused ? 2.0f : 1.0f);
    if (value.empty() && !focused && !placeholder.empty()) {
        if (center_text) {
            float tw = text_width(Font::Body, placeholder);
            label(Rect{r.x + (r.w - tw) * 0.5f, r.y, r.w, r.h}, placeholder, true);
        } else {
            label(Rect{r.x + PAD, r.y, r.w - 2 * PAD, r.h}, placeholder, true);
        }
    } else {
        std::string shown = value + (focused ? "|" : "");
        if (!center_text) {
            // Show the tail once the text outgrows the box, so what was
            // just typed stays in view. Widths add up exactly: the baked
            // atlas has no kerning.
            float avail = r.w - 2 * PAD;
            float used = 0;
            size_t start = shown.size();
            while (start > 0) {
                float cw = text_width(Font::Body, std::string(1, shown[start - 1]));
                if (used + cw > avail) break;
                used += cw;
                --start;
            }
            if (start > 0) shown = shown.substr(start);
        }
        if (center_text) {
            float tw = text_width(Font::Body, shown);
            label(Rect{r.x + (r.w - tw) * 0.5f, r.y, r.w, r.h}, shown, !enabled);
        } else {
            label(Rect{r.x + PAD, r.y, r.w - 2 * PAD, r.h}, shown, !enabled);
        }
    }
    return changed;
}

bool numeric_field(const Rect& r, std::string& value, const GuiInput& in, size_t max_len,
                    bool enabled, bool invalid, bool center_text) {
    return text_field(r, value, in, "0123456789", max_len, enabled, invalid,
                       CaseFold::None, /*placeholder=*/"", center_text);
}

bool dropdown(const Rect& r, const std::vector<std::string>& options, int& selected, int id,
              int& open_dropdown_id, const GuiInput& in, bool enabled, bool invalid) {
    bool changed = false;
    bool is_open = enabled && open_dropdown_id == id;

    Color bg = !enabled ? palette::disabled_bg() : palette::panel();
    draw_rect(r.x, r.y, r.w, r.h, bg);
    Color border_color =
        invalid ? palette::border_invalid() : (is_open ? palette::accent() : palette::border());
    draw_rect_outline(r.x, r.y, r.w, r.h, border_color);
    std::string shown =
        (selected >= 0 && selected < static_cast<int>(options.size())) ? options[static_cast<size_t>(selected)] : "";
    label(Rect{r.x + PAD, r.y, r.w - 2 * PAD - 14, r.h}, shown, !enabled);
    label(Rect{r.x + r.w - 16, r.y, 14, r.h}, is_open ? "^" : "v", !enabled);

    if (enabled && rect_contains(r, in.mouse_x, in.mouse_y) && in.mouse_pressed &&
        !click_over_open_popup(in)) {
        open_dropdown_id = is_open ? -1 : id;
        g_click_consumed_this_frame = true;
        is_open = !is_open;
    }

    if (is_open) {
        g_pending.active = true;
        g_pending.id = id;
        g_pending.box = r;
        g_pending.options = &options;
        g_pending.selected = &selected;
    }
    return changed;
}

void draw_open_dropdown_popup(const GuiInput& in, int& open_dropdown_id) {
    if (!g_pending.active || !g_pending.options) return;
    if (g_pending.id != g_popup_scroll_owner) {
        g_popup_scroll = 0.0f;
        g_popup_scroll_owner = g_pending.id;
    }

    const auto& options = *g_pending.options;
    const float row_h = g_pending.box.h;
    const float max_visible = 8.0f;
    float list_h = row_h * std::min<float>(static_cast<float>(options.size()), max_visible);
    Rect popup{g_pending.box.x, g_pending.box.y + g_pending.box.h, g_pending.box.w, list_h};
    g_popup_rect_last = popup;
    g_popup_drawn_this_frame = true;

    float max_scroll = std::max(0.0f, static_cast<float>(options.size()) * row_h - list_h);
    g_popup_scroll -= static_cast<float>(in.scroll_y) * row_h;
    if (g_popup_scroll < 0.0f) g_popup_scroll = 0.0f;
    if (g_popup_scroll > max_scroll) g_popup_scroll = max_scroll;

    draw_rect(popup.x, popup.y, popup.w, popup.h, palette::panel());
    draw_rect_outline(popup.x, popup.y, popup.w, popup.h, palette::accent());

    bool clicked_inside = false;
    // Rows are only skipped when *entirely* outside the popup — a row
    // scrolled by a fraction of its height is still partially inside and
    // must draw, but without a scissor clip that partial draw renders at
    // full size and bleeds past the popup's own edges into whatever sits
    // just above/below it (the closed box itself, or the next widget
    // down). begin_scissor crops that overflow to the popup rect.
    begin_scissor(popup.x, popup.y, popup.w, popup.h);
    for (size_t i = 0; i < options.size(); ++i) {
        float row_y = popup.y + row_h * static_cast<float>(i) - g_popup_scroll;
        if (row_y + row_h < popup.y || row_y > popup.y + popup.h) continue;  // fully scrolled off-screen

        Rect row{popup.x, row_y, popup.w, row_h};
        bool hovered = rect_contains(row, in.mouse_x, in.mouse_y) && rect_contains(popup, in.mouse_x, in.mouse_y);
        if (hovered) draw_rect(row.x, row.y, row.w, row.h, palette::border());
        label(Rect{row.x + PAD, row.y, row.w - 2 * PAD, row.h}, options[i]);
        if (hovered && in.mouse_pressed) {
            *g_pending.selected = static_cast<int>(i);
            open_dropdown_id = -1;
            clicked_inside = true;
        }
    }
    end_scissor();

    if (max_scroll > 0.0f) {
        // A minimal scrollbar thumb on the right edge — enough to signal
        // "there's more below" without a full scrollbar widget.
        float thumb_h = std::max(12.0f, popup.h * (list_h / (static_cast<float>(options.size()) * row_h)));
        float thumb_y = popup.y + (popup.h - thumb_h) * (g_popup_scroll / max_scroll);
        draw_rect(popup.x + popup.w - 4, thumb_y, 3, thumb_h, palette::accent());
    }

    if (in.mouse_pressed && !clicked_inside && !rect_contains(g_pending.box, in.mouse_x, in.mouse_y)) {
        // Click landed outside the box and outside the popup — close it.
        if (!rect_contains(popup, in.mouse_x, in.mouse_y)) open_dropdown_id = -1;
    }
}

// ── scrolling ───────────────────────────────────────────────────────────

namespace {

constexpr float kScrollStep = 48.0f;
constexpr float kScrollBarW = 4.0f;

float scroll_span(float top, float height, float content_height) {
    float view_h = height - top;
    return content_height > view_h ? content_height - view_h : 0.0f;
}

}  // namespace

float begin_scroll_region(float top, float width, float height, float& scroll,
                          float content_height, const GuiInput& in) {
    const float max_scroll = scroll_span(top, height, content_height);

    // Only while the pointer is actually over the region, so a wheel event
    // meant for something else does not move the page underneath it.
    if (in.scroll_y != 0.0 && in.mouse_y >= top)
        scroll -= static_cast<float>(in.scroll_y) * kScrollStep;

    if (scroll > max_scroll) scroll = max_scroll;
    if (scroll < 0.0f) scroll = 0.0f;

    begin_scissor(0.0f, top, width, height - top);
    return top - scroll;
}

void end_scroll_region(float top, float width, float height, float scroll,
                       float content_height) {
    end_scissor();

    const float max_scroll = scroll_span(top, height, content_height);
    if (max_scroll <= 0.0f) return;  // everything fits; no bar to draw

    const float view_h = height - top;
    const float track_x = width - kScrollBarW - 2.0f;
    draw_rect(track_x, top, kScrollBarW, view_h, palette::disabled_bg());

    float thumb_h = std::max(24.0f, view_h * (view_h / content_height));
    float thumb_y = top + (view_h - thumb_h) * (scroll / max_scroll);
    draw_rect(track_x, thumb_y, kScrollBarW, thumb_h, palette::accent());
}

// ── modals ──────────────────────────────────────────────────────────────

namespace {

constexpr float kModalW = 460.0f;
constexpr float kModalPad = 22.0f;
constexpr float kModalBtnW = 130.0f;
constexpr float kModalBtnH = 32.0f;

// The dimmed sheet plus the box, shared by both modal shapes. Returns the
// box so the caller can lay its own contents out inside it.
Rect draw_modal_frame(float screen_w, float screen_h, const std::string& title,
                      const std::string& body, float box_h) {
    g_in_modal = true;
    // The screen behind has already been drawn by the caller; this greys
    // it out so it reads as out of reach rather than merely unresponsive.
    draw_rect(0, 0, screen_w, screen_h, rgba(0.0f, 0.0f, 0.0f, 0.55f));

    Rect box{(screen_w - kModalW) * 0.5f, (screen_h - box_h) * 0.5f, kModalW, box_h};
    draw_rect(box.x, box.y, box.w, box.h, palette::panel());
    draw_rect_outline(box.x, box.y, box.w, box.h, palette::border());

    float y = box.y + kModalPad;
    label(Rect{box.x + kModalPad, y, box.w - 2 * kModalPad, 26.0f}, title, false, Font::BodyLarge);
    y += 34.0f;
    label(Rect{box.x + kModalPad, y, box.w - 2 * kModalPad, 24.0f}, body, true);
    return box;
}

}  // namespace

ModalChoice modal_question(float screen_w, float screen_h, const std::string& title,
                           const std::string& body, const std::string& confirm_text,
                           const std::string& cancel_text, const GuiInput& in) {
    const float box_h = kModalPad * 2 + 34.0f + 24.0f + 18.0f + kModalBtnH;
    Rect box = draw_modal_frame(screen_w, screen_h, title, body, box_h);

    float by = box.y + box_h - kModalPad - kModalBtnH;
    // Confirm on the right, the way a dialog that can lose you something
    // should read: the default reading order puts the safe answer first.
    Rect cancel_r{box.x + kModalPad, by, kModalBtnW, kModalBtnH};
    Rect confirm_r{box.x + box.w - kModalPad - kModalBtnW, by, kModalBtnW, kModalBtnH};

    bool cancel = button(cancel_r, cancel_text, in, true);
    bool confirm = button(confirm_r, confirm_text, in, true, true);
    g_in_modal = false;

    if (in.key_enter) confirm = true;
    if (in.key_escape) cancel = true;

    if (confirm) return ModalChoice::Confirm;
    if (cancel) return ModalChoice::Cancel;
    return ModalChoice::None;
}

bool modal_notice(float screen_w, float screen_h, const std::string& title,
                  const std::string& body, const GuiInput& in) {
    const float box_h = kModalPad * 2 + 34.0f + 24.0f + 18.0f + kModalBtnH;
    Rect box = draw_modal_frame(screen_w, screen_h, title, body, box_h);

    float by = box.y + box_h - kModalPad - kModalBtnH;
    Rect ok_r{box.x + box.w - kModalPad - kModalBtnW, by, kModalBtnW, kModalBtnH};
    bool ok = button(ok_r, "OK", in, true, true);
    g_in_modal = false;
    return ok || in.key_enter || in.key_escape;
}

}  // namespace gui
}  // namespace inop

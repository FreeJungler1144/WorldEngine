// gui_self_test.cpp — the parts of the GUI that can be checked without a
// window, run as part of `inop --self-test`.
//
// Everything here is pure logic that happens to live in a GUI-only source
// file: parsing a preferences file, parsing a script, and the saved
// configuration store. None of it draws, so none of it needs a GL context
// and none of it can be skipped for want of one.
//
// Compiled only when INOP_WITH_GUI is on. A CLI-only build gets the empty
// version in gui_stub.cpp instead, the same way it gets the empty
// run_gui_settings(), so main.cpp needs no #ifdef either way.
//
// What is deliberately not here: anything that measures text. wrap_lines()
// asks the baked font atlas how wide a character is, and with no atlas
// every character is nought wide, so a headless check of it would pass on
// nonsense. resolve_focus() is not here either, because the rects it works
// on are registered by focus_register(), which the header does not expose;
// widening the public interface for a test would be the wrong trade.
#include <cstdio>
#include <fstream>
#include <string>

#include "gui.hpp"
#include "gui_config_store.hpp"
#include "gui_prefs.hpp"
#include "gui_script.hpp"
#include "gui_setup_panel.hpp"
#include "gui_widgets.hpp"

namespace inop {

namespace {

// A file under the working directory that only this suite writes, deleted
// as soon as the check that needed it is done. A check that reads a file
// has to write one first, and leaving it behind would make the next run
// depend on the last.
std::string write_temp(const std::string& name, const std::string& body) {
    const std::string path = "inop_selftest_" + name;
    std::ofstream f(path, std::ios::binary);
    f << body;
    return path;
}

void drop_temp(const std::string& path) { std::remove(path.c_str()); }

}  // namespace

void gui_self_test(const SelfTestCheck& check) {
    using namespace inop::gui;

    // ── preferences ────────────────────────────────────────────────────
    {
        GuiPrefs wrote;
        wrote.theme = Theme::Light;
        wrote.colourblind = ColourblindMode::Tritanopia;
        wrote.window_mode = WindowMode::Windowed;
        wrote.zoom_percent = 135;
        wrote.reduced_motion = true;
        const std::string path = "inop_selftest_prefs.json";
        const bool saved = save_prefs(wrote, path);
        GuiPrefs read;
        const bool loaded = load_prefs(read, path);
        drop_temp(path);
        check(saved && loaded && read == wrote, "prefs survive a save and a load unchanged");
    }
    {
        // Every field here is one a hand edited file could carry and the
        // control could not produce. None of them may be taken at face
        // value: a zoom of 900 would scale the interface past any way back
        // to the settings screen that could undo it.
        const std::string path = write_temp(
            "prefs_bad.json",
            "{\"zoom\":900,\"font\":\"no-such-face.ttf\",\"colourblind\":\"red-green\"}");
        GuiPrefs p;
        const bool loaded = load_prefs(p, path);
        drop_temp(path);
        check(loaded && p.zoom_percent == 100, "a zoom no control offers is ignored");
        check(loaded && p.font_file == GuiPrefs{}.font_file,
              "a font this machine does not have falls back to the default");
        check(loaded && p.colourblind == ColourblindMode::Deuteranopia,
              "the older red-green name still reads as deuteranopia");
    }
    {
        const std::string path = write_temp("prefs_off.json", "{\"colourblind\":\"off\"}");
        GuiPrefs p;
        const bool loaded = load_prefs(p, path);
        drop_temp(path);
        check(loaded && p.colourblind == ColourblindMode::Full,
              "the older off name still reads as full colour");
    }
    {
        const std::string path = write_temp("prefs_junk.json", "this is not json");
        GuiPrefs p;
        const bool loaded = load_prefs(p, path);
        drop_temp(path);
        check(!loaded, "a preferences file that is not JSON is refused");
    }
    {
        GuiPrefs p;
        check(!load_prefs(p, "inop_selftest_nothing_here.json"),
              "a preferences file that is not there is refused");
    }

    // ── where a font file is looked for ────────────────────────────────
    {
        check(!font_path("cour.ttf").empty(),
              "font_path finds a face in the system font folder");
        check(font_path("definitely-not-a-face.ttf").empty(),
              "font_path comes back empty for a face nobody has");
    }

    // ── the script parser refuses what it cannot run ───────────────────
    {
        struct Bad {
            const char* body;
            const char* what;
        };
        const Bad bad[] = {
            {"move 10\n", "move with only one coordinate is refused"},
            {"type\n", "type with nothing to type is refused"},
            {"key\n", "key with no key named is refused"},
            {"key sideways\n", "a key nobody has is refused"},
            {"ctrl maybe\n", "ctrl takes on or off and nothing else"},
            {"scroll\n", "scroll with no amount is refused"},
            {"wait\n", "wait with no number is refused"},
            {"wait -1\n", "a wait that runs backwards is refused"},
            {"shot\n", "shot with no name is refused"},
            {"shot sub/dir\n", "a shot name carrying a path is refused"},
            {"banana\n", "a verb the parser does not know is refused"},
        };
        for (const Bad& b : bad) {
            const std::string path = write_temp("script_bad.txt", b.body);
            InputScript s;
            std::string err;
            const bool ok = s.load(path, &err);
            drop_temp(path);
            check(!ok && !err.empty(), b.what);
        }
    }
    {
        InputScript s;
        std::string err;
        check(!s.load("inop_selftest_no_script.txt", &err),
              "a script file that is not there is refused");
    }

    // ── the script parser runs what it accepts ─────────────────────────
    {
        const std::string path = write_temp("script_ok.txt",
                                            "# a comment, then a blank line\n"
                                            "\n"
                                            "move 40 60\n"
                                            "click\n"
                                            "type hello\n"
                                            "key enter\n"
                                            "ctrl on\n"
                                            "scroll 2\n"
                                            "shot a-picture\n"
                                            "quit\n");
        InputScript s;
        std::string err;
        const bool ok = s.load(path, &err);
        drop_temp(path);
        check(ok && err.empty(), "a script using every verb loads");
        if (ok) {
            GuiInput in;
            s.fill(in, 0.016f);
            check(in.mouse_x == 40 && in.mouse_y == 60, "move puts the pointer where it says");
            // A click is two frames because a real button is a down edge
            // and then an up edge, and no widget in here sees both at once.
            s.fill(in, 0.016f);
            const bool down = in.mouse_pressed && in.mouse_held && !in.mouse_released;
            s.fill(in, 0.016f);
            const bool up = in.mouse_released && !in.mouse_held && !in.mouse_pressed;
            check(down && up, "click is a down frame and then an up frame");
            s.fill(in, 0.016f);
            check(in.typed.size() == 5 && in.typed[0] == 'h' && in.typed[4] == 'o',
                  "type delivers the rest of the line");
            s.fill(in, 0.016f);
            check(in.key_enter && !in.key_escape, "key enter arrives as one keypress");
            s.fill(in, 0.016f);
            check(in.ctrl_held, "ctrl on is held rather than pressed");
            s.fill(in, 0.016f);
            check(in.scroll_y == 2 && in.ctrl_held,
                  "scroll carries its amount, and ctrl is still held");
            s.fill(in, 0.016f);
            check(s.pending_shot() == "a-picture", "shot names the picture it wants");
            check(!s.fill(in, 0.016f), "quit asks for the window to close");
        }
    }
    {
        // A wait is real elapsed time, not a count of frames, so a short
        // frame must not advance past it.
        const std::string path = write_temp("script_wait.txt", "wait 0.1\nkey enter\n");
        InputScript s;
        std::string err;
        const bool ok = s.load(path, &err);
        drop_temp(path);
        GuiInput in;
        s.fill(in, 0.02f);
        // The frame that finishes the wait is still the waiting frame. The
        // step after it gets the next one, which is why this looks for the
        // keypress rather than assuming which frame carries it.
        const bool held = !in.key_enter;
        int frames = 0;
        while (frames < 20 && !in.key_enter) {
            s.fill(in, 0.02f);
            ++frames;
        }
        check(ok && held && in.key_enter && frames >= 4,
              "a wait holds for its seconds and then lets go");
    }

    // ── the saved configuration store ──────────────────────────────────
    {
        // A default panel state has no rotors picked, so it is exactly the
        // incomplete configuration load_config() exists to refuse.
        // load_config() is the sole authority on whether a file is
        // corrupted, and the tile browser shows its popup on that answer
        // alone, so what it refuses matters as much as what it accepts.
        PanelState empty_state;
        const std::string name = "inop-selftest.json";
        std::string save_err;
        const bool saved = save_config(empty_state, name, &save_err);
        check(saved, "a configuration writes to setup/");
        check(saved && config_exists(name), "a saved configuration is found again by name");

        PanelState back;
        std::string load_err;
        const bool loaded = load_config("setup/" + name, back, &load_err);
        check(!loaded && !load_err.empty(),
              "a configuration with no rotors picked is refused, with a reason");

        std::string del_err;
        const bool deleted = delete_config("setup/" + name, &del_err);
        check(deleted, "a saved configuration deletes");
        check(deleted && !config_exists(name), "a deleted configuration is gone");
    }
    {
        std::string err;
        check(!delete_config("setup/inop-selftest-never-existed.json", &err),
              "deleting a configuration that is not there is refused");
    }
    {
        const std::string path = write_temp("config_junk.json", "{ not a configuration");
        PanelState out;
        std::string err;
        const bool loaded = load_config(path, out, &err);
        drop_temp(path);
        check(!loaded && !err.empty(), "a configuration file that is not JSON is refused");
    }
    {
        // The suggestion is the lowest unused number for the suite, so it
        // must never name a file that is already sitting there.
        PanelState st;
        const std::string suggested = suggest_filename(st);
        check(!suggested.empty() && !config_exists(suggested),
              "the suggested filename is one that is not taken");
    }
}

}  // namespace inop

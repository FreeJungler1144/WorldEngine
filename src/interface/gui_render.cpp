#include "gui_render.hpp"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <vector>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

// GLFW's header includes the platform GL header (GL/gl.h on Windows) for
// us, giving every OpenGL 1.1 entry point opengl32.dll exports statically —
// no GLAD/GLEW loader needed. This is only safe as long as gui.cpp never
// asks GLFW for a specific GL version/profile (see the comment there).
#include <GLFW/glfw3.h>

// GL_CLAMP_TO_EDGE is GL 1.2, not 1.1, so some gl.h headers omit the
// enum. It is just a constant, not a function pointer, so no loader is
// needed to use it — define it ourselves if missing.
#ifndef GL_CLAMP_TO_EDGE
#define GL_CLAMP_TO_EDGE 0x812F
#endif

#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"

namespace inop {
namespace gui {

namespace {

struct FontAtlas {
    GLuint texture = 0;
    std::vector<stbtt_bakedchar> chars;  // ASCII 32..127 (96 glyphs)
    int bitmap_w = 0, bitmap_h = 0;
    float pixel_height = 0;
};

FontAtlas g_body;
FontAtlas g_wordmark;
FontAtlas g_body_large;

bool read_file(const std::string& path, std::vector<unsigned char>& out) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    f.seekg(0, std::ios::end);
    std::streamoff len = f.tellg();
    if (len <= 0) return false;
    f.seekg(0, std::ios::beg);
    out.resize(static_cast<size_t>(len));
    f.read(reinterpret_cast<char*>(out.data()), len);
    return static_cast<bool>(f) || f.eof();
}

bool bake_font(const std::string& path, float pixel_height, FontAtlas& out) {
    std::vector<unsigned char> ttf;
    if (!read_file(path, ttf)) {
        std::cerr << "gui: could not read font file '" << path << "'\n";
        return false;
    }
    const int bw = 1024, bh = 1024;
    std::vector<unsigned char> bitmap(static_cast<size_t>(bw) * bh);
    out.chars.resize(96);
    int result = stbtt_BakeFontBitmap(ttf.data(), 0, pixel_height, bitmap.data(), bw, bh, 32, 96,
                                       out.chars.data());
    if (result <= 0) {
        std::cerr << "gui: font atlas bake failed for '" << path << "'\n";
        return false;
    }
    glGenTextures(1, &out.texture);
    glBindTexture(GL_TEXTURE_2D, out.texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_ALPHA, bw, bh, 0, GL_ALPHA, GL_UNSIGNED_BYTE, bitmap.data());
    out.bitmap_w = bw;
    out.bitmap_h = bh;
    out.pixel_height = pixel_height;
    return true;
}

// Every atlas back to its unbaked state, textures released. Shared by
// shutdown and by a re-bake, since a re-bake that kept the old texture
// names would leak one atlas per typeface change.
void free_atlases() {
    if (g_body.texture) glDeleteTextures(1, &g_body.texture);
    if (g_wordmark.texture) glDeleteTextures(1, &g_wordmark.texture);
    if (g_body_large.texture) glDeleteTextures(1, &g_body_large.texture);
    g_body = FontAtlas{};
    g_wordmark = FontAtlas{};
    g_body_large = FontAtlas{};
}

const FontAtlas& atlas_for(Font font) {
    switch (font) {
        case Font::Wordmark:
            return g_wordmark;
        case Font::BodyLarge:
            return g_body_large;
        default:
            return g_body;
    }
}

// Both in pixels, not logical units: glScissor and glViewport speak
// pixels, and the width is kept so set_ui_scale() can redo the projection
// without waiting for the next resize event.
int g_viewport_w = 0;
int g_viewport_h = 0;  // needed to flip our top-left-origin rects into glScissor's bottom-left ones
float g_ui_scale = 1.0f;

}  // namespace

bool render_init() {
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    return true;
}

void render_shutdown() { free_atlases(); }

void set_viewport(int width, int height) {
    if (width <= 0 || height <= 0) return;
    g_viewport_w = width;
    g_viewport_h = height;
    glViewport(0, 0, width, height);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    // Top-left origin, y increasing downward — matches GLFW cursor
    // coordinates so widget hit-testing needs no flip.
    //
    // Dividing the extents by the scale is the whole of the zoom: the
    // window still has the same pixels, but fewer logical units span it,
    // so everything drawn in logical units comes out proportionally
    // bigger. No widget, panel or layout constant knows this happened.
    glOrtho(0, static_cast<double>(width) / g_ui_scale,
            static_cast<double>(height) / g_ui_scale, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
}

void set_ui_scale(float scale) {
    if (scale <= 0.0f) return;
    g_ui_scale = scale;
    set_viewport(g_viewport_w, g_viewport_h);
}

float ui_scale() { return g_ui_scale; }

void begin_scissor(float x, float y, float w, float h) {
    glEnable(GL_SCISSOR_TEST);
    // glScissor is bottom-left-origin regardless of the glOrtho we set up,
    // so flip y here rather than asking every caller to think in GL's
    // coordinate space. It also speaks pixels while callers speak logical
    // units, so the scale has to be undone on the way in.
    const float s = g_ui_scale;
    const float px = x * s, py = y * s, pw = w * s, ph = h * s;
    glScissor(static_cast<int>(px), static_cast<int>(static_cast<float>(g_viewport_h) - (py + ph)),
              static_cast<int>(pw), static_cast<int>(ph));
}

void end_scissor() { glDisable(GL_SCISSOR_TEST); }

void clear(Color background) {
    glClearColor(background.r, background.g, background.b, background.a);
    glClear(GL_COLOR_BUFFER_BIT);
}

void draw_rect(float x, float y, float w, float h, Color c) {
    glDisable(GL_TEXTURE_2D);
    glColor4f(c.r, c.g, c.b, c.a);
    glBegin(GL_QUADS);
    glVertex2f(x, y);
    glVertex2f(x + w, y);
    glVertex2f(x + w, y + h);
    glVertex2f(x, y + h);
    glEnd();
}

void draw_rect_outline(float x, float y, float w, float h, Color c, float thickness) {
    glDisable(GL_TEXTURE_2D);
    glColor4f(c.r, c.g, c.b, c.a);
    glLineWidth(thickness);
    glBegin(GL_LINE_LOOP);
    glVertex2f(x, y);
    glVertex2f(x + w, y);
    glVertex2f(x + w, y + h);
    glVertex2f(x, y + h);
    glEnd();
}

bool load_fonts(const std::string& font_file) {
    const char* windir = std::getenv("WINDIR");
    std::string fonts_dir = windir ? std::string(windir) + "\\Fonts\\" : "C:\\Windows\\Fonts\\";
    // One typeface throughout, not just the wordmark — Body/BodyLarge used
    // to be Segoe UI, but the operator asked for one consistent typeface
    // across the whole panel. Which one it is became a preference; that it
    // is the same one in all three sizes did not.
    free_atlases();
    bool ok_body = bake_font(fonts_dir + font_file, 18.0f, g_body);
    bool ok_word = bake_font(fonts_dir + font_file, 44.0f, g_wordmark);
    bool ok_large = bake_font(fonts_dir + font_file, 28.0f, g_body_large);
    if (!(ok_body && ok_word && ok_large)) {
        free_atlases();
        return false;
    }
    return true;
}

float text_width(Font font, const std::string& text) {
    const FontAtlas& a = atlas_for(font);
    if (a.chars.empty()) return 0.0f;
    float w = 0.0f;
    for (unsigned char ch : text) {
        if (ch < 32 || ch > 127) continue;
        w += a.chars[static_cast<size_t>(ch - 32)].xadvance;
    }
    return w;
}

float text_line_height(Font font) { return atlas_for(font).pixel_height * 1.25f; }

void draw_text(Font font, float x, float baseline_y, const std::string& text, Color c) {
    const FontAtlas& a = atlas_for(font);
    if (!a.texture) return;
    glEnable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, a.texture);
    glColor4f(c.r, c.g, c.b, c.a);
    float xpos = x, ypos = baseline_y;
    glBegin(GL_QUADS);
    for (unsigned char ch : text) {
        if (ch < 32 || ch > 127) continue;
        stbtt_aligned_quad q;
        stbtt_GetBakedQuad(const_cast<stbtt_bakedchar*>(a.chars.data()), a.bitmap_w, a.bitmap_h,
                            ch - 32, &xpos, &ypos, &q, 1);
        glTexCoord2f(q.s0, q.t0);
        glVertex2f(q.x0, q.y0);
        glTexCoord2f(q.s1, q.t0);
        glVertex2f(q.x1, q.y0);
        glTexCoord2f(q.s1, q.t1);
        glVertex2f(q.x1, q.y1);
        glTexCoord2f(q.s0, q.t1);
        glVertex2f(q.x0, q.y1);
    }
    glEnd();
    glDisable(GL_TEXTURE_2D);
}

}  // namespace gui
}  // namespace inop

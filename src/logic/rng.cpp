// rng.cpp — OS entropy, no third-party dependencies.
//
// Windows: BCryptGenRandom (Vista+). Needs -lbcrypt at link time.
// Everything else: /dev/urandom.
//
// Both are cryptographically secure. There is deliberately no fallback to
// rand() or std::random_device — silently degrading to a weak generator is
// exactly the failure this file exists to prevent, so it throws instead.

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <bcrypt.h>
#ifndef BCRYPT_USE_SYSTEM_PREFERRED_RNG
#define BCRYPT_USE_SYSTEM_PREFERRED_RNG 0x00000002
#endif
#endif

#include "rng.hpp"

#include <stdexcept>
#include <vector>

#if !defined(_WIN32)
#include <cstdio>
#include <sys/types.h>
#include <unistd.h>
#endif

namespace inop {

void secure_bytes(uint8_t* buf, size_t n) {
    if (n == 0) return;
#if defined(_WIN32)
    // A NULL algorithm handle with this flag uses the system default RNG,
    // so there is no handle to open, close, or leak.
    while (n > 0) {
        ULONG chunk = n > 0x40000000u ? 0x40000000u : static_cast<ULONG>(n);
        if (BCryptGenRandom(NULL, reinterpret_cast<PUCHAR>(buf), chunk,
                            BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0)
            throw std::runtime_error("BCryptGenRandom failed: no OS entropy");
        buf += chunk;
        n -= chunk;
    }
#else
    static FILE* src = nullptr;
    if (!src) {
        src = std::fopen("/dev/urandom", "rb");
        if (!src) throw std::runtime_error("cannot open /dev/urandom");
    }
    if (std::fread(buf, 1, n, src) != n)
        throw std::runtime_error("short read from /dev/urandom");
#endif
}

namespace {
// Fisher-Yates shuffling a wheel batch draws once per swap, which used to
// cost one OS entropy call (BCryptGenRandom/fread) per draw. Buffered in
// bulk instead, the same batching secure_string() already does below —
// refilled only when exhausted, not on every single draw.
uint32_t next_uint32() {
    static std::vector<uint8_t> pool;
    static size_t pos = 0;
#if !defined(_WIN32)
    // A fork() after the pool is filled leaves parent and child holding the
    // same buffered bytes, and neither has any way to notice: both go on to
    // draw the same shuffles, which means the same wheels and the same key
    // sheet. Discarding the pool whenever the pid changes costs one getpid()
    // per draw and makes that impossible. Windows has no fork, so this is
    // POSIX-only rather than conditional on anything else.
    static pid_t owner = 0;
    const pid_t self = getpid();
    if (self != owner) {
        pool.clear();
        pos = 0;
        owner = self;
    }
#endif
    if (pos + 4 > pool.size()) {
        pool.resize(4096);
        secure_bytes(pool.data(), pool.size());
        pos = 0;
    }
    uint32_t v = static_cast<uint32_t>(pool[pos]) | (static_cast<uint32_t>(pool[pos + 1]) << 8) |
                 (static_cast<uint32_t>(pool[pos + 2]) << 16) | (static_cast<uint32_t>(pool[pos + 3]) << 24);
    pos += 4;
    return v;
}
}  // namespace

uint32_t secure_below(uint32_t bound) {
    if (bound == 0) throw std::invalid_argument("secure_below(0)");
    if (bound == 1) return 0;

    // Reject the ragged tail so every value is equally likely.
    const uint32_t limit = UINT32_MAX - (UINT32_MAX % bound) - 1;
    uint32_t v;
    do {
        v = next_uint32();
    } while (v > limit);
    return v % bound;
}

std::string secure_string(const std::string& alphabet, size_t n) {
    const uint32_t size = static_cast<uint32_t>(alphabet.size());
    if (size == 0) throw std::invalid_argument("secure_string: empty alphabet");
    if (n == 0) return std::string();

    // Draw in bulk and reject the biased tail — one call, not n.
    const uint32_t limit = 256 - (256 % size);
    std::string out;
    out.reserve(n);
    std::vector<uint8_t> buf;
    while (out.size() < n) {
        size_t want = (n - out.size()) * 2 + 8;
        buf.resize(want);
        secure_bytes(buf.data(), want);
        for (size_t i = 0; i < want && out.size() < n; ++i)
            if (buf[i] < limit) out += alphabet[buf[i] % size];
    }
    return out;
}

void entropy_self_check() {
    // Thresholds here are set so a healthy OS entropy source clears them by
    // a wide margin — every one of them has a false-alarm probability below
    // one in a billion — while a source that is merely "varied enough to
    // look random at a glance" does not. The earlier limits (64 distinct
    // bytes out of 4096, 15 distinct draws out of 512) were loose enough
    // that a generator restricted to 20 symbols would have passed both.

    // 1. Raw bytes: coverage, spread, and balance.
    const size_t N = 4096;
    std::vector<uint8_t> buf(N);
    secure_bytes(buf.data(), N);

    int counts[256] = {0};
    for (size_t i = 0; i < N; ++i) ++counts[buf[i]];
    int distinct = 0;
    for (int v = 0; v < 256; ++v) if (counts[v]) ++distinct;
    // 4096 draws over 256 values leaves an expected 0.00003 values unseen,
    // so a healthy source returns 256 essentially every time.
    if (distinct < 250)
        throw std::runtime_error(
            "entropy source is degenerate: " + std::to_string(distinct) +
            " distinct byte values in " + std::to_string(N) + " bytes (expected ~256)");

    // Chi-square over the 256 byte values, 255 degrees of freedom: mean 255,
    // standard deviation ~22.6. 500 is roughly eleven deviations out, and a
    // source biased toward any small subset of byte values overshoots it by
    // orders of magnitude — 20 usable values scores about 48,000.
    const double expected = static_cast<double>(N) / 256.0;
    double chi2 = 0.0;
    for (int v = 0; v < 256; ++v) {
        const double d = static_cast<double>(counts[v]) - expected;
        chi2 += d * d / expected;
    }
    if (chi2 > 500.0)
        throw std::runtime_error(
            "entropy source is not uniform: byte-value chi-square is " + std::to_string(chi2) +
            " over 255 degrees of freedom (expected around 255)");

    // Monobit: 32,768 bits, expected 16,384 set, standard deviation ~90.5.
    // Catches a source that covers every byte value but leans on one side of
    // the bit distribution, which the value histogram alone can miss.
    long ones = 0;
    for (size_t i = 0; i < N; ++i) {
        uint8_t b = buf[i];
        while (b) { ones += b & 1; b = static_cast<uint8_t>(b >> 1); }
    }
    const long bits = static_cast<long>(N) * 8;
    const long deviation = ones - bits / 2;
    if (deviation > 600 || deviation < -600)
        throw std::runtime_error(
            "entropy source is not balanced: " + std::to_string(ones) + " set bits in " +
            std::to_string(bits) + " (expected " + std::to_string(bits / 2) + " +/- 91)");

    // 2. secure_below must actually vary. This is the exact path that failed
    //    silently once: keys looked random while every shuffle returned 0.
    const int draws = 512;
    int hits[38] = {0};
    for (int i = 0; i < draws; ++i) {
        uint32_t v = secure_below(38);
        if (v >= 38) throw std::runtime_error("secure_below returned out of range");
        ++hits[v];
    }
    int spread = 0;
    for (int v = 0; v < 38; ++v) if (hits[v]) ++spread;
    // Coupon collector says all 38 show up within about 162 draws; over 512
    // the chance of even one going missing is around one in a million, so
    // anything below 36 is a broken generator rather than bad luck.
    if (spread < 36)
        throw std::runtime_error(
            "secure_below is degenerate: only " + std::to_string(spread) +
            " distinct values in " + std::to_string(draws) + " draws (expected 38)");

    // Coverage alone would still pass a generator that hits all 38 values but
    // heavily favours a few. Chi-square over 37 degrees of freedom: mean 37,
    // standard deviation ~8.6, so 120 is about ten deviations out.
    const double draw_expected = static_cast<double>(draws) / 38.0;
    double draw_chi2 = 0.0;
    for (int v = 0; v < 38; ++v) {
        const double d = static_cast<double>(hits[v]) - draw_expected;
        draw_chi2 += d * d / draw_expected;
    }
    if (draw_chi2 > 120.0)
        throw std::runtime_error(
            "secure_below is not uniform: chi-square is " + std::to_string(draw_chi2) +
            " over 37 degrees of freedom (expected around 37)");
}

}  // namespace inop

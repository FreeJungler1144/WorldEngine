// langprobe_main.cpp — offline dumper for the numeral-suffix diacritic
// scheme.
//
// Writes, per language, the exact symbol stream the live pipeline would
// hand to the rotors: preprocess(fold_diacritics(mark_literal_digits(raw)))
// over that language's benchmark corpus. Also writes the declared
// (base letter, mark code) grammar the scheme is built on.
//
// This target exists so the measurement runs against the real tables in
// languages.cpp rather than a reimplementation of them in the analysis
// script. It touches no key material, no cipher state and no message path,
// and like inop_benchmark it is never linked into the live pipeline.
//
//   inop_langprobe [--corpus-dir benchmark/corpus] [--out probe_out]
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "inop.hpp"
#include "languages.hpp"
#include "pipeline.hpp"
#include "registry.hpp"

using namespace inop;

namespace {

std::string read_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return {};
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// Line structure is a property of the corpus file, not of a message. A
// newline left in place would be dropped by preprocess() and silently weld
// the last word of one line onto the first word of the next, inventing
// bigrams that the language never produced. Folding it to a space instead
// keeps the word boundary the source actually had.
std::string flatten_whitespace(const std::string& text) {
    std::string out;
    out.reserve(text.size());
    for (char c : text) out += (c == '\n' || c == '\r' || c == '\t') ? ' ' : c;
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    std::string corpus_dir = "benchmark/corpus";
    std::string out_dir = "probe_out";
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--corpus-dir" && i + 1 < argc) corpus_dir = argv[++i];
        else if (arg == "--out" && i + 1 < argc) out_dir = argv[++i];
        else {
            std::cerr << "usage: inop_langprobe [--corpus-dir DIR] [--out DIR]\n";
            return 2;
        }
    }

    const Alphabet alpha(ALPHA38);

    std::ofstream manifest(out_dir + "/manifest.tsv");
    if (!manifest) {
        std::cerr << "cannot write into " << out_dir
                  << " — create it first (this tool does not make directories)\n";
        return 1;
    }
    manifest << "lang\traw_bytes\tfolded_symbols\n";

    std::ofstream marks(out_dir + "/marks.tsv");
    marks << "lang\tbase\tcode\n";
    for (const auto& l : supported_languages())
        for (const auto& [base, code] : declared_marks(l.code))
            marks << l.code << '\t' << base << '\t' << code << '\n';
    for (const auto& [base, code] : declared_marks(""))
        marks << "GLOBAL" << '\t' << base << '\t' << code << '\n';

    int done = 0, missing = 0;
    for (const auto& l : supported_languages()) {
        std::string raw = read_file(corpus_dir + "/" + l.code + ".txt");
        if (raw.empty()) {
            std::cerr << "  !! " << l.code << ": no corpus file, skipped\n";
            ++missing;
            continue;
        }
        std::string folded =
            preprocess(fold_diacritics(mark_literal_digits(flatten_whitespace(raw)), l.code), alpha);
        std::ofstream f(out_dir + "/" + l.code + ".folded", std::ios::binary);
        f << folded;
        manifest << l.code << '\t' << raw.size() << '\t' << folded.size() << '\n';
        ++done;
    }
    std::cout << done << " language(s) dumped, " << missing << " without corpus\n";
    return 0;
}

# Word list

`enable1.txt.gz` is the ENABLE word list (Enhanced North American Benchmark
Lexicon): 172,823 lowercase English words, one per line, 2 to 28 letters.

- Licence: public domain. ENABLE was released into the public domain by its
  author, Alan Beale, and is used by many open-source word games.
- Source: https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt
- SHA-256 of the uncompressed file:
  `3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89`
- Compressed with `gzip -n -9` (no timestamp, so rebuilding gives the same file).

Loaded by `backend.core.dictionary.load_word_list()`.

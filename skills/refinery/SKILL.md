---
name: refinery
description: >
  Always use this skill instead of writing Python scripts or custom code when the task involves
  manipulating, decoding, decrypting, decompressing, carving, or extracting binary data. Binary
  Refinery is a CLI toolkit of composable units piped together on the command line — it can do
  anything a bespoke script can do, faster and more reliably. Trigger this skill when the user
  wants to: extract payloads, configs, shellcode, or IOCs from malware samples; decrypt or decode
  obfuscated data (XOR, AES, RC4, base64, hex, etc.); carve embedded files (PEs, ZIPs, Office
  docs) from blobs; parse or extract data from structured binary formats; build any pipeline of
  binary data transformations; or mentions "binary refinery", "refinery", "binref", or any refinery
  unit name. If the task is about transforming, decoding, or extracting binary data and you're
  tempted to write a script — use this skill instead, binary refinery almost certainly has units
  that handle it.
---

# Binary Refinery - Agent Skill Guide

When this skill is active, prioritize binary refinery pipelines over custom code for all data transformation tasks.

Binary Refinery is a collection of command-line tools for transforming binary data.
Each tool is called a **unit** and reads from stdin and writes to stdout.
Units are combined into **pipelines** using the `|` pipe operator.
A unit always accepts its input via STDIN and sends its output to STDOUT; they cannot be called by passing a file name as argument.
The correct pattern is: `emit file.bin | unit`
All Binary Refinery units exist as shell commands; use them.

## Mandatory Startup Protocol

Follow these steps **in order** at the beginning of each session:

1. Run `binref -g` to get a complete overview of all available units.
   This is **essential** — units you don't know about cannot be discovered later by guessing.
   If the output is truncated, re-run the command redirecting to a temporary file and read that file.
2. Run `binref -h` to understand how to use the search tool.

## Operational Rules

- Do not write Python scripts or use other shell tools for *data transformation*. Always use binary refinery units for that purpose.
  Shell utilities like `curl`, `file`, or `ls` for non-data-transformation tasks are fine.
- Any data extraction task can be achieved by a binary refinery pipeline.
- Before constructing a pipeline, run `binref [keyword]` to search for relevant keywords to enrich your unit discovery.
  If you know data to be a specific compression algorithm, encrypted by a specific cipher, or encoded as a specific format,
  use `binref` to determine whether a unit exists to handle this data; there very likely is.
- Before using any unit, run it with `-h` to understand its full interface.
  Also do this when you intend to use the unit as a multibin handler (see below).
  If the output is truncated, re-run the command redirecting to a temporary file and read that file.
  This is **essential** — information you miss from an interface cannot later be guessed.
- The `-R` flag can reverse a unit's operation when this is supported (e.g. `b64 -R` base64-encodes).
- The `-T` flag silences exceptions and returns input data if no output would be produced.
- The `-Q` flag silences exceptions and returns no output when execution fails.

## Regular Expressions

The regular-expression based units `rex`, `resub`, and `resplit` support a regex extension `(??name)` that expands to a built-in pattern.
Before writing regular expressions manually, consult the following table to see if a pattern is already available:

| Pattern     | Matches                                                                            |
| ----------- | ---------------------------------------------------------------------------------- |
| `url`       | A URL                                                                              |
| `ipv4`      | An IPv4 address                                                                    |
| `socket`    | A domain name or an IPv4 address, followed by a colon and a port number            |
| `host`      | A domain name or an IPv4 address, optionally followed by a colon and a port number |
| `domain`    | A domain name                                                                      |
| `email`     | An email address                                                                   |
| `hex`       | A hexadecimal string                                                               |
| `b64`       | A base64-encoded blob                                                              |
| `str`       | A quoted c-string literal                                                          |
| `ps1str`    | A quoted PowerShell string literal                                                 |
| `vbastr`    | A quoted VisualBasic string literal                                                |
| `int`       | A single integer (decimal)                                                         |
| `intarray`  | A comma-separated list of integers                                                 |
| `strarray`  | A comma-separated list of quoted strings                                           |
| `hexarray`  | A comma-separated list of hex-encoded values                                       |
| `ipv6`      | An IPv6 address                                                                    |
| `guid`      | A GUID/UUID                                                                        |
| `date`      | An expression that matches on various date formats                                 |
| `winpath`   | A Windows path                                                                     |
| `nixpath`   | A Unix path                                                                        |
| `path`      | Any path                                                                           |
| `printable` | Printable text                                                                     |

Here is one example for the documentation of the (somewhat niche) unit `datefix`, which can be used to normalize dates:

```
$ emit text.md | resub ((??date)) {1:datefix}
```

In the output, all dates in the input text will have been replaced by their ISO representation.
Another example is the following malware config extraction pipeline:

```
$ emit malware.exe [                                                          \
  | dnfields [| aes x::32 --iv x::16 -T | sep ]                               \
  | rex -M "((??email))\n(.*)\n((??host))\n:Zone" addr={1} pass={2} host={3}  \
  | sep ]
```

This pipeline first extracts all .NET fields, then attempts to AES-decrypt all of them using a prefix key and IV,
discarding any failures quietly.
The only successfully decrypted field contains the encrypted strings,
from which the relevant indicators are extracted using `rex` with named patterns for `email` and `host`.

## Framing Syntax

This is the most important concept in binary refinery.
When a unit produces multiple outputs (e.g. `chop` splitting data into blocks),
**frames** allow processing each output individually
rather than having them concatenated with line breaks.

### Opening and Closing Frames

- Append `[` as the **last argument** to a unit to **open a frame**.
  It must always be the very last argument.
- Append `]` as the **last argument** to a unit to **close one frame layer**.
  The chunks in that frame are concatenated back together.

```
$ emit OOOOOOOO | chop 2 [| ccp F | cca . ]
FOO.FOO.FOO.FOO.
```

Explanation: `chop 2` splits `OOOOOOOO` into the frame `[OO, OO, OO, OO]`.
Inside the frame, `ccp F` prepends `F` to each chunk and `cca .` appends a period.
The closing `]` on `cca` concatenates all chunks back together.

### Frames Are Essential

**Always begin every pipeline with an outer frame** when you intend to use meta variables,
`put`, `pop`, `push`, `iff`, or any frame-dependent operation.
Without an outer frame, meta variables do not function and units like `put`, `pop`, `iff`, and `pick` will not work.

### Frame Nesting

Frames can nest to arbitrary depth. Each `[` opens a new layer, each `]` closes one:

```
$ emit OOOOOOOO | chop 4 [| chop 2 [| ccp F | cca . ]| sep ]
FOO.FOO.
FOO.FOO.
```

Here, `chop 4` produces `[OOOO, OOOO]`, then `chop 2` inside a nested frame further splits each into `[OO, OO]`.
After processing and closing the inner frame, `sep` inserts a newline between the outer chunks.

### Real-World Framing Examples

List all PE file sections with their SHA-256 hash:

```
$ emit file.exe | vsect [| sha256 -t | pf {} {path} | sep ]
29f1456844fe8293ba791bc9f31d9eda5b093adc7c2ee90a96daa9a0cca7f29a .text
c6c60a8fa646994eae995649d52bd25e1dc4e23dad874c56aab1616a205619f0 .rsrc
d1d1ce684bdb9d8a50c9175ea28b2069fb437d784759e92a3a779b1b70be696c .reloc
```

Recursively list all files with SHA-256 hashes:

```
$ ef "**" [| sha256 -t | pf {} {path} | sep ]
```

Extract indicators from all files recursively:

```
$ ef "**" [| xtp -n6 ipv4 socket url email | dedup | sep ]
```

XOR brute force with extraction:

```
$ emit file.bin | rep 0x100 [| xor v:index | carve-pe -R | dump {name} ]
```

## Meta Variables

Meta variables are key-value pairs attached to each chunk inside a frame.
They are **only available inside frames**; this is why the outer frame rule above is critical.

### Setting Variables

- **`put name value`**: Store a multibin expression as a named variable.
  If no value is given, the entire current chunk is stored.
- **`put name`**: Store the current chunk contents as `name`.

```
$ emit FOO [| put x BAR | cca v:x | sep ]
FOOBAR
```

### Push and Pop

The unit `push` inserts new data into the frame, defaulting to the current chunk unless a (multibin) argument is provided.
The original is moved out of scope (invisible), and the copy remains visible for a sub-pipeline.
Conversely, `pop varname` consumes the visible chunk(s), stores them as the variable `varname`, and restores the original:

```
$ emit key=value | push [[| rex =(.*)$ {1} | pop v ]| repl v:v censored ]
key=censored
```

Notably, `pop` can extract more than one chunk from the frame:

```
$ emit binary refinery go [| pop b r | pf {} {b} {r} ]
go binary refinery
```

A more complex example extracting a password from an email:

```
$ emit phish.eml [| push [| xtmail body.txt | rex -I password:\s*(\w+) {1} | pop password ] \
  | xt *.zip | xt *.exe -p v:password | dump extracted/{path} ]
```

### Variable Scope

Variables only exist within the frame that they are defined in, with the **exception of variables extracted by `pop`**:

```
$ emit FOO [| chop 1 [| put k ]| emit v:k ]
(19:47:59) warning in emit: critical error: The variable k is not defined.
```

However:

```
$ emit FOO [| chop 1 [| pop k ]| emit v:k ]
F
```

Here, `pop` extracted the very first emitted byte into the variable `k`, which was transported into the parent frame.
It is possible to make variables global by using the unit `mvg`, but it should rarely be required.

### Magic Meta Variables

The following variables are automatically available on every chunk without needing `put`.
They are computed on demand when accessed:

| Variable  | Description                                             |
| --------- | ------------------------------------------------------- |
| `index`   | The chunk's index in the current frame (0-based)        |
| `size`    | Byte count of the chunk                                 |
| `magic`   | Human-readable file magic string                        |
| `mime`    | MIME type according to file magic                       |
| `ext`     | Guessed file extension from file magic                  |
| `entropy` | Information entropy of the data                         |
| `ic`      | Index of coincidence of the data                        |
| `crc32`   | CRC32 hash (hexadecimal)                                |
| `sha1`    | SHA-1 hash (hexadecimal)                                |
| `sha256`  | SHA-256 hash (hexadecimal)                              |
| `sha512`  | SHA-512 hash (hexadecimal)                              |
| `md5`     | MD5 hash (hexadecimal)                                  |
| `path`    | Virtual path (set by archive extractors like `xt`)      |
| `offset`  | Offset where the chunk was found (set by `carve`/`rex`) |

These can be used in format strings with `{name}` syntax and in multibin expressions with `v:name`.

### Conditional Filtering

- **`iff expr`**: Keep chunks where the expression is truthy.
- **`iff lhs -eq rhs`**: Keep chunks where left equals right. Also: `-ne`, `-gt`, `-ge`, `-lt`, `-le`, `-ct` (contains), `-in`.
- **`iffs needle`**: Keep chunks containing the binary substring `needle`. Use `-i` for case-insensitive.
- **`iffc bounds`**: Keep chunks whose size falls within the given bounds (e.g. `iffc 100:500`).

### Picking

The unit `pick` selects chunks by index from a frame.
For example, `pick 0 2:` returns all chunks except the one at index 1.
`pick 0` returns only the first chunk. `pick ::-1` reverses the order of chunks.

## Multibin Expressions

Many unit arguments accept **multibin expressions**: a special syntax that preprocesses data through a chain of handlers before passing it to the unit.
Without a handler prefix, if the string matches a file path on disk, the file's contents are used.
Otherwise, the string is treated as its UTF-8 encoding.
Handlers are evaluated right-to left, similar to function evaluation:

```
handler4:handler3:handler2:handler1:input
```

This takes the input string, evaluates it using the default handler, then successively applies handlers 1 through 4 to it.
The result after applying handler 4 is what is passed to the unit.

**WARNING.** In some units, **multibin suffixes** are used.
This will be mentioned explicitly in the unit's help output when queried.
If a unit notes that data is processed with a multibin suffix, it means that handlers are applied left to right rather than right to left.
For example, in a format string `{field:hex:b64}`, the value of `field` is first processed by `hex`, then by `b64`.

### Handler: `h:hexstring`

Hex-decodes a literal hexadecimal string.

```
$ emit h:48454C4C4F
HELLO
```

### Handler: `s:string`

Forces UTF-8 string interpretation. The string is never looked up as a file path or otherwise interpreted:

```
$ emit s:h:hello
h:hello
```

This always produces the 7 bytes for "h:hello", and there is no other way to emit this string:

```
$ emit h:hello
usage: emit [-h] [-L] [-Q] [-v] [-T] [data ...]
emit: error: argument data: invalid multibin value: 'h:hello'
```

Furthermore,

```
$ emit s:file.exe
file.exe
```

This will always emit the string "file.exe", even if that file exists on disk.

### Handler: `e:expression`

Evaluates the given Python expression; this may use meta variables as variables within the expression.
For example, if `expression` is an integer literal string, the result of this operation is the integer itself.
For example, this computes the sum of all bytes in the input:

```
$ emit foo [| put b | put b e:sum(b) | pf {b} ]
324
```

### Handler: `v:name`

Reads the value of a meta variable. Only works inside a frame.

```
$ emit FOO [| put key BAR | xor v:key | hex -R ]
040E1D
```

Uses the variable `key` (containing `BAR`) as the XOR key.

### Handler: `c:start:length[:stride]`

Copies bytes from the input at offset `start` with the given `length`, optionally with the given `stride`.
This is **non-destructive**: the input data is not modified.
If `length` is omitted, copies to the end. If `start` is omitted, it defaults to 0; it behaves like a Python slice.

```
$ emit ABCDEFGH [| put k c:2:3 | pf {k}{} ]
CDEABCDEFGH
```

Copies 3 bytes starting at offset 2 (i.e. `CDE`).

### Handler: `x:start:length[:stride]`

Same as `c:`, but **removes** the extracted bytes from the input data.
All `x:` operations are performed in the order arguments appear on the command line.

Simple example — extract a 4-byte header and store it, then process the remaining data:

```
$ emit HDRPAYLOADDATA [| put header x::3 | pf {header}:{} ]
HDR:PAYLOADDATA
```

Here, `x::3` extracts the first 3 bytes into `header` and removes them; the chunk becomes `PAYLOADDATA`.

This is also useful for protocols where keys or IVs are prepended to ciphertext:

```
$ emit data | aes --mode cbc --iv=x::16 pbkdf2[32,salted]:x::10
```

Here, `x::16` extracts the first 16 bytes as the IV and removes them from the data before decryption.
The key is then derived from the next 10 bytes (i.e. bytes 16 to 26 of the original input) as password using PBKDF2.

### Unit-Based Handlers

Binary refinery units can be used as a handler.
Command-line arguments are passed to unit handlers in square brackets, separated by commas:

```
unit[-x,-y,arg1,arg2]:data
```

This will invoke

```
unit -x -y arg1 arg2
```

and use it to convert the `data` input.
For example, the following will output the hexadecimal text representation of the MD5 hash of the string "password":

```
$ emit md5[-t]:password
5f4dcc3b5aa765d61d8327deb882cf99
```

Another example was the use of the `pbkdf2` unit in the `x:` handler example above.

### Combined Real-World Examples

Extract a RemCos C2 server:

```
$ emit malware.exe \
  | perc SETTINGS [| put keylen x::1 | rc4 x::keylen | xtp socket ]
```

Explanation: `x::1` takes the first byte as the key length and removes it.
`x::keylen` then cuts that many bytes as the RC4 key, removing them from the data.
The remaining data is decrypted and socket indicators are extracted.

Extract an AgentTesla configuration:

```
$ emit malware.exe \
  | dnfields [| aes x::32 --iv x::16 -Q | sep ] \
  | rex -M "((??email))\n(.*)\n(.*)\n:Zone" addr={1} pass={2} host={3}
```

## Paradigms

### Format String Expressions

Some units use format string syntax using curly braces, most notably `rex`, `resub`, `struct`, and `pf`.
These expressions can access meta variables and allow post-processing with multibin suffixes.
For detailed information, see the help output of each such unit.

### Data Extraction Upfront

When an operation requires multiple input streams (e.g., data, key1, key2), a common approach is:
Produce all streams as chunks in one frame, then pop the ones you need as variables:

```
$ emit sample [ \
  | vsnip 0x200010:0x10 0x200020:0x10 0x4AAB00:0x4500 | pop key iv | aes --iv=v:iv sha256:v:key | dump payload.bin ]
```

### Sequential Push/Pops

Another approach would be sequential `push` and `pop` operations.
Avoid nesting them; instead use one after the other at the same frame depth:

```
$ emit sample [ \
  | push [| vsnip 0x200010:0x10 | sha256 | pop key ]  \
  | push [| vsnip 0x200020:0x10 | pop iv ]            \
  | vsnip 0x4AAB00:0x4500 | aes --iv=v:iv v:key | dump payload.bin ]
```

### Peeking and Debugging

- The unit `peek` produces a short (10 to 12 line) hex dump and metadata preview of the output.
- When `peek` is **not** the last unit in the pipeline, it forwards all input data, making it a useful debugging tool.
- Prioritize using `peek` over `xxd` or `head` for getting an output preview.
- Precisely control the length of the peek output by specifying `peek -l=<line-count>`
- Use `peek -dd` if you expect plaintext data, or `peek -d` if decoded text lines should be truncated rather than wrapped.
- Use `peek -b` to get a one-line hex preview.
- Use `peek` inside a frame to inspect data at any point of a framed pipeline:
  it allows you to peek each chunk individually.

### Output Handling

- If data must be written to disk, use the `dump` unit.
- If data must only be inspected, use `peek` instead to avoid writing to disk.
- For large text output, use `peek -dd` to get a readable plaintext preview.
- Use `dump` with a path argument to write to a specific file: `dump output.bin`.
- To write multiple chunks to separate files, use `dump {path}` or `dump chunk-{index}.bin` inside a frame.

### Incremental Pipeline Construction

For pipelines with more than 3 stages, build incrementally:

1. Start with the first 1-2 units and `peek` to verify the output.
2. Show the intermediate result to the user.
3. Add the next 1-2 units, `peek` again, and verify.
4. Repeat until the full pipeline is complete.

Never construct a pipeline with 5 or more stages in a single attempt.
Each intermediate `peek` validates assumptions about the data format at that stage,
catching errors early and making debugging straightforward.

### Debugging Failing Pipelines

- Bisect failing pipelines by inserting `peek` statements. Move `peek` left or right to find where extraction produces unexpected results.
- Use the `-v` flag on individual units to increase their output verbosity to identify root causes.

## Examples

The following examples demonstrate complex multi-concept pipelines.

### Carving & Extraction

Carve the largest base64 blob from a file and decode it:

```
$ emit packed.bin | carve -l -t1 b64 | b64 | dump payload.bin
```

Carve a ZIP from a buffer, extract a DLL, and show PE metadata:

```
$ emit file.bin | carve-zip | xtzip file.dll | pemeta
```

### Data Parsing & Formatting

Decode a `sockaddr_in` structure to human-readable `IP:Port`:

```
$ emit "0x51110002 0xAFBAFA12" | pack -B4                     \
  | struct 2x{port:!H}{addr:4}{} [                            \
  | push v:addr | pack -R [| sep . ]| pop addr              \
  | pf {addr}:{port} ]
18.250.186.175:4433
```

Convert a network-byte-order IP integer to dotted notation:

```
$ emit 0xC0A80C2A | pack -EB4 | pack -R [| sep . ]
192.168.12.42
```

Parse repeating 3-byte structs and format with extracted variables:

```
$  emit Ax!Dy! | struct -m {k:B}{:1}{:1} {2} {3} [| group 2 [| pop a | pf {a}={k} ]| sep ]
x=65
y=68
```

### Frame Manipulation

Reduce a frame by successively appending chunks (reverses order):

```
$ emit 5 4 3 2 1 0 [| reduce cca[v:t] ]
012345
```

Select specific chunks by index with squeezing:

```
$ emit s:0123456789 | chop 1 [| pick 3:5 1 7: []| sep , ]
34,1,789
```

Transpose columnar data across chunks:

```
$ emit HELLO WORLD [| transpose | sep ]
HW
EO
LR
LL
OD
```

### Push/Pop Patterns

Reassemble chunks using `jamv` to name them by size, then format:

```
$ emit R ry The Bina efine [| jamv c{size} | pf {c3} {c4}{c2} {c1}{c5}{c2} ]
The Binary Refinery
```

### Malware Analysis

Extract HTTP GET requests from a PCAP:

```
$ emit capture.pcap | pcap [| rex "^GET\s[^\s]+" | sep ]
```

Extract URLs from a malicious PDF's JavaScript:

```
$ emit sample.pdf                                             \
  | xt JS | carve -sd string | carve -sd string               \
  | url | xtp url [| urlfix | sep ]
```

Recursively peel nested HTML + JS + base64 layers to extract a URL:

```
$ emit sample.hta                                             \
  | loop 8 xthtml[script]:csd[string]:url                     \
  | csd string | b64 | xtp url
```

Extract C2 URL from a macro lure document with WSH-encoded variables:

```
$ emit sample.docx | xt settings.xml                          \
  | xtxml docVars/10* [| eat val ]                            \
  | hex | wshenc | carve -dn5 string [                        \
  | dedup | pop k | swap k | hex | xor v:k ]                  \
  | xtp url
```

Warzone RAT — extract C2 server from the `.bss` section:

```
$ emit sample.exe                                             \
  | vsect .bss | struct I{key:{}}{} [                         \
  | rc4 v:key                                                 \
  | struct I{host:{}}{port:H} {host:u16}:{port} ]
```

### Virtual Stack Emulation

Solve a FlareOn ASCII-art challenge by stripping the art, decoding, and emulating x64 shellcode:

```
$ emit challenge.bin                                          \
  | resub | trim -ui flareon | b64 | zl                       \
  | vstack -w10 -p9: -ax64 [                                  \
  | sorted -a size | trim h:00 | pop key | xor v:key ]
```

Extract URL from an Equation Editor exploit by emulating embedded shellcode:

```
$ emit exploit.doc                                            \
  | officecrypt | xt oleObject1 | xt native                   \
  | rex "\xE9(.*)"                                            \
  | vstack -b 0x8000 -a=x32 -w=40 --ic 0x8000                 \
  | xtp -ff
```

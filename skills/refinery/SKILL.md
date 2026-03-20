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
Units cannot be called by passing a file name as argument; the correct pattern is `emit file.bin | unit`.
All output is sent to STDOUT, debug messages and `peek` unit previews (see below) appear on STDERR.
All Binary Refinery units exist as shell commands; use them.

## Mandatory Startup Protocol

Follow these steps **in order** at the beginning of each session:

1. Run `binref -g` to get a complete overview of all available units.
   This is **essential** — units you don't know about cannot be discovered later by guessing.
   If the output is truncated, re-run the command redirecting to a temporary file and read that file.
2. Run `binref -h` to understand how to use the search tool.

## Operational Rules

- Do not mix shell syntax (like environment variables) with refinery pipelines; there is a high risk of conflict.
- Do not write Python scripts or use other shell tools for _data transformation_. Always use binary refinery units for that purpose.
  Shell utilities like `curl`, `file`, or `ls` for non-data-transformation tasks are fine.
- Any data extraction task can be achieved by a binary refinery pipeline.
- Before constructing a pipeline, run `binref [keyword]` to search for relevant keywords to enrich your unit discovery.
  If you know data to be a specific compression algorithm, encrypted by a specific cipher, or encoded as a specific format,
  use `binref` to determine whether a unit exists to handle this data; there very likely is.
- Before using any unit, run it with `-?` to understand its interface.
  Also do this when you intend to use the unit as a multibin handler (see below).
  If the output is truncated, re-run the command redirecting to a temporary file and read that file.
  This is **essential** — information you miss from an interface cannot later be guessed.
- The `-R` flag can reverse a unit's operation when this is supported (e.g. `b64 -R` base64-encodes).
- The `-T` flag silences exceptions and returns input data if no output would be produced.
- The `-Q` flag silences exceptions and returns no output when execution fails.

## Multibin Expressions

Many unit arguments accept **multibin expressions**: a special syntax that preprocesses data through a chain of handlers before passing it to the unit.
Without a handler prefix, if the string matches a file path on disk, the file's contents are used.
Otherwise, the string is treated as its UTF-8 encoding.
Handlers are evaluated right to left:

```
handler4:handler3:handler2:handler1:input
```

**WARNING.** Some units use **multibin suffixes** (noted in their help output),
where handlers are applied left to right instead.
For example, in a format string `{field:hex:b64}`, the value of `field` is first processed by `hex`, then by `b64`.

### Handler: `h:hexstring`

Hex-decodes a literal hexadecimal string.

```
$ emit h:48454C4C4F
HELLO
```

### Handler: `s:string`

Forces UTF-8 string interpretation — the string is never treated as a handler prefix or looked up as a file path:

```
$ emit s:h:hello
h:hello
$ emit s:file.exe
file.exe
```

Without `s:`, `h:hello` would be parsed as hex-decode and `file.exe` would read the file from disk if it exists.

### Handler: `c:start:length[:stride]`

Copies bytes from the input at offset `start` with the given `length`, optionally with the given `stride`.
This is **non-destructive**: the input data is not modified.
If `length` is omitted, copies to the end. If `start` is omitted, it defaults to 0; it behaves like a Python slice.

```
$ emit FOO-BAR | xor c::3 | esc -R
\x00\x00\x00k\r\x0e\x14
```

`c::3` copies the first 3 bytes (`FOO`) as the XOR key without removing them from the input.

```
$ emit #H#E#L#L#O | emit c:1::2
HELLO
```

`c:1::2` copies every other byte starting at offset 1.

### Handler: `x:start:length[:stride]`

Same as `c:`, but **removes** the extracted bytes from the input data.
All `x:` operations are performed in the order arguments appear on the command line.

```
$ emit FOO-BAR | xor x::3 | esc -R
k\r\x0e\x14
```

`x::3` extracts and removes the first 3 bytes (`FOO`), so `xor` uses `FOO` as key against only the remaining `-BAR`.

```
$ emit #H#E#L#L#O######## | emit x:1:10:2 x::5
HELLO
#####
```

`x:1:10:2` pulls every other byte in a span of 10; `x::5` then takes the first 5 of what remains.

### Unit-Based Handlers

Binary refinery units can be used as a handler.
Command-line arguments are passed in square brackets, separated by commas:
`unit[-x,-y,arg1,arg2]:data` invokes `unit -x -y arg1 arg2` on the data.

```
$ emit md5[-t]:password
5f4dcc3b5aa765d61d8327deb882cf99
```

## Regular Expressions

The regular-expression based units `rex`, `resub`, and `resplit` support a regex extension `(??name)` that expands to a built-in pattern.
Before writing regular expressions manually, consult the following table to see if a pattern is already available:

| Pattern    | Matches                                       |
| ---------- | --------------------------------------------- |
| `url`      | A URL                                         |
| `ipv4`     | IPv4 address                                  |
| `ipv6`     | IPv6 address                                  |
| `socket`   | domain or ip followed by colon and port       |
| `host`     | like socket, but port suffix optional         |
| `domain`   | domain name                                   |
| `email`    | email address                                 |
| `hex`      | hex string                                    |
| `b64`      | base64-encoded data                           |
| `str`      | quoted c-string literal                       |
| `int`      | any integer literal                           |
| `intarray` | comma or semicolon-separated list of integers |
| `strarray` | list of quoted string literals                |
| `hexarray` | list of hex-encoded values                    |
| `date`     | matches various date formats                  |
| `winpath`  | Windows path                                  |
| `nixpath`  | Unix path                                     |

Normalize dates in a text file using `datefix`:

```
$ emit text.md | resub ((??date)) {1:datefix}
```

All dates in the input will have been replaced by their ISO representation.

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

Extract an AgentTesla malware config by AES-decrypting .NET fields and pulling indicators with named regex patterns:

```
$ emit malware.exe [                                                          \
  | dnfields [| aes x::32 --iv x::16 -T | sep ]                               \
  | rex -M "((??email))\n(.*)\n((??host))\n:Zone" addr={1} pass={2} host={3}  \
  | sep ]
```

`dnfields` extracts all .NET fields, then each is AES-decrypted using a 32-byte prefix key and 16-byte IV;
`-T` silences failures so only the successfully decrypted field survives.
`rex` with named patterns for `email` and `host` pulls the indicators from the decrypted strings.

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

[`v:x` retrieves the meta variable's value (`BAR`); full details are in Frame-Dependent Multibin Handlers below.]

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

| Variable  | Comment                            |
| --------- | ---------------------------------- |
| `index`   | chunk index in the frame (0-based) |
| `size`    | chunk size                         |
| `magic`   | file magic description             |
| `mime`    | MIME type                          |
| `ext`     | best-fit file extension            |
| `entropy` | information entropy of the data    |

### Common Meta Variables

Some units produce meta variables in addition to their output:
- `offset`: Offset where data was found, set by `carve` and `rex`
- `path`: Virtual path, set by archive extractors like `xt`.

### Conditional Filtering

- **`iff expr`**: Keep chunks where the expression is truthy.
- **`iff lhs -eq rhs`**: Keep chunks where left equals right. Also: `-ne`, `-gt`, `-ge`, `-lt`, `-le`, `-ct` (contains), `-in`.
- **`iffs needle`**: Keep chunks containing the binary substring `needle`. Use `-i` for case-insensitive.
- **`iffc bounds`**: Keep chunks whose size falls within the given bounds (e.g. `iffc 100:500`).

### Picking

The unit `pick` selects chunks by index from a frame.
For example, `pick 0 2:` returns all chunks except the one at index 1.
`pick 0` returns only the first chunk. `pick ::-1` reverses the order of chunks.

## Frame-Dependent Multibin Handlers

The following multibin handlers interact with frame data and meta variables.

### Handler: `e:expression`

Evaluates the given Python expression that can involve meta variables.
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

### Combined Real-World Examples

Extract a RemCos C2 server:

```
$ emit malware.exe \
  | perc SETTINGS [| put keylen x::1 | rc4 x::keylen | xtp socket ]
```

Explanation: `x::1` takes the first byte as the key length and removes it.
`x::keylen` then cuts that many bytes as the RC4 key, removing them from the data.
The remaining data is decrypted and socket indicators are extracted.

XOR brute force with extraction:

```
$ emit file.bin | rep 0x100 [| xor v:index | carve-pe -R | dump {name} ]
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
$ emit sample [                                     \
  | push [| vsnip 0x200010:0x10 | sha256 | pop k ]  \
  | push [| vsnip 0x200020:0x10 | pop iv ]          \
  | vsnip 0x4AAB00:0x4500 | aes --iv=v:iv v:key | dump payload.bin ]
```

### Output, Peeking, and Debugging

- Prioritize `peek` over `xxd` or `head` for inspecting output. It produces a short hex dump and metadata preview.
- When `peek` is **not** the last unit in the pipeline, it forwards all input data, making it a useful debugging tool.
  Use it inside a frame to inspect each chunk individually.
- `peek -dd` for plaintext, `peek -b` for a one-line hex preview.
- Control peek length with `peek -l=<line-count>`.
- To write data to disk, use the `dump` unit.

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

### Data Parsing & Formatting

Decode a `sockaddr_in` structure to human-readable `IP:Port`:

```
$ emit "0x51110002 0xAFBAFA12" | pack -B4       \
  | struct 2x{port:!H}{addr:4}{} [              \
  | push v:addr | pack -R [| sep . ]| pop addr  \
  | pf {addr}:{port} ]
18.250.186.175:4433
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

### Malware Analysis

Extract HTTP GET requests from a PCAP:

```
$ emit capture.pcap | pcap [| rex "^GET\s[^\s]+" | sep ]
```

Extract URLs from a malicious PDF's JavaScript:

```
$ emit sample.pdf                               \
  | xt JS | carve -sd string | carve -sd string \
  | url | xtp url [| urlfix | sep ]
```

Recursively peel nested HTML + JS + base64 layers to extract a URL:

```
$ emit sample.hta                               \
  | loop 8 xthtml[script]:csd[string]:url       \
  | csd string | b64 | xtp url
```

Extract C2 URL from a macro lure document with WSH-encoded variables:

```
$ emit sample.docx | xt settings.xml            \
  | xtxml docVars/10* [| eat val ]              \
  | hex | wshenc | carve -dn5 string [          \
  | dedup | pop k | swap k | hex | xor v:k ]    \
  | xtp url
```

### Virtual Stack Emulation

Solve a FlareOn ASCII-art challenge by stripping the art, decoding, and emulating x64 shellcode:

```
$ emit challenge.bin                            \
  | resub | trim -ui flareon | b64 | zl         \
  | vstack -w10 -p9: -ax64 [                    \
  | sorted -a size | trim h:00 | pop key | xor v:key ]
```

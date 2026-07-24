---
name: refinery
description: Load this skill INSTEAD OF writing a custom Python/shell script (especially python -c) whenever a task decodes/decrypts/deobfuscates/decompresses/unpacks/carves/extracts binary/encoded data — Binary Refinery is a rich, composable CLI pipeline toolkit better suited for it. Trigger always to: encode/decode/decrypt/decompress with any cipher or encoding (XOR/AES/RC4/base64/hex/gzip/LZMA/...); unpack/list archives (7z/rar/msi/iso/dmg/jar/apk/...); extract hashes (hashcat/jtr); inspect file type/metadata (signatures/timestamps/...); extract or parse data and fields from structured formats — resources, data at a virtual address, section contents (executables/documents/...); carve embedded files from blobs; extract payloads, configs, shellcode, or IOCs from malware; emulate executables/shellcode; deobfuscate scripts (ps1/js/vbs/php). Also triggers on "binary refinery", "refinery", or "binref".
---



# Binary Refinery - Agent Skill Guide

Binary Refinery is a collection of command-line tools for transforming binary data.
Each tool is a **unit** that reads from stdin and writes to stdout.
Units are combined into **pipelines** using the `|` pipe operator.
Units cannot be called by passing a file name as argument; the correct pattern is

```
emit /full/path/to/file.bin | unit
```

All output goes to STDOUT; debug messages and `peek` unit previews (see below) appear on STDERR.

## Mandatory Startup Protocol

Follow these steps in order at the start of each session, **exactly as written**.
Do not pipe through `head`/`tail` or any other limiter. Do not write to a temporary file.
The full output must appear in your context window; a partial read does not satisfy this protocol.

1. Run `binref -V` to get the current refinery version. It must be **at least 0.11.0**.
   Version too low? Abort and inform the user.
2. Run `binref -g` for a compact unit overview.
   The output of this command is kept brief.
   Running it is essential: Units you don't know about cannot be discovered later by guessing.
3. Run `binref -h` to learn the search syntax for discovering units by keyword.

If these commands do not exist, offer installation:

1. create or activate a dedicated virtual environment for this project
2. run `pip install binary-refinery`

## Operational Rules

- Do not write Python scripts or use other shell tools for data transformations; always use binary refinery units.
  Shell utilities for non-data-transformation tasks are fine.
- Use `peek` as your universal data preview tool.
  Run `peek -l0` instead of `file`, `peek -dd` instead of `head`, and plain `peek` instead of `xxd`.
  Control peek length with `peek -l=<line-count>`.
  If `peek` is the final unit in a pipeline, use the `-2` switch to prevent input data from being forwarded and leaking into the output.
- To write data to disk, use the `dump` unit.
- When extracting data based on patterns, use the `carve` unit.
- When extracting indicators from data, use `xtp`.
- Before constructing a pipeline, run `binref [keyword]` to search for relevant units.
  If you know data to be a specific compression algorithm, cipher, or encoding, use `binref` to check whether a unit handles it — there very likely is one.
- The `-R` flag can reverse a unit's operation when this is supported (e.g. `b64 -R` base64-encodes).
- The `-T` flag silences exceptions and returns input data if no output would be produced.
- The `-Q` flag silences exceptions and returns no output when execution fails.
- When constructing a pipeline that ingests file data, pass file paths as literal strings to `emit`.
  Never assign paths to shell variables first; it conflicts with multibin expression parsing and produces wrong results.
- When a unit produces errors or incomplete output, debug it.
  Do not abandon a conceptually correct unit after a single failure.

## Help First Rule

The inclusion of **any** unit in **any** pipeline for **any** reason is **invalid**
unless said unit was invoked with the `-H` switch earlier in the session transcript.
If it does not appear, run it before using the unit. There are **no exceptions**.
Check this before every unit call and every pipeline construction,
including when you intend to use the unit as a multibin handler (see below).

If you find yourself copying a unit invocation from the examples section, **stop** and run it with `-H` first.
The examples are illustrations, not templates to copy verbatim.

If the `-H` output is truncated, re-run redirecting to a temporary file and read that file.

**Why this rule exists.**
Information you miss from an interface **cannot later be guessed**, and your instincts about the syntax
will be **wrong** without proper research.

## Layer Boundary Rule

Every time a pipeline stage produces output that you recognize as a distinct artifact type
 — a script, an executable, an archive, a document, or any structured format —
you **must** search for a unit that consumes that artifact type directly before proceeding.

1. Name the artifact type in one or two words (e.g., "obfuscated PowerShell", "PE executable", "ZIP archive").
2. Run `binref [-o] [artifact-type keywords]` to search for a unit that handles it.
3. Only if no suitable high-level unit exists, decompose into low-level sub-operations.

**Why this rule exists.**
Composing low-level units to replicate what a single high-level unit already does is the refinery equivalent of writing a bespoke script:
slower, more error-prone, and it misses edge cases that unit handles.
Recognizing a data format is not a reason to skip discovery; it is the signal to search, because you now have good keywords.

## Null Result Rule

When a pipeline produces empty, missing, or unexpectedly small output where you expected data,
that is not a conclusion — it is an anomaly.
Before accepting it, strip all post-processing and run the producing unit by itself to verify the observation.
Only after this isolated check confirms the absence may you conclude the data is truly not there.

**Why this rule exists.**
A pipeline that runs without errors can still silently discard data —
by design, or because a post-processing step worked differently from what you expected.

## Unit Lookup Strategy

When searching for units, use this iterative approach:

1. Run a very broad `binref` search with a wide net of keywords that could occur on a matching unit.
2. If there are no good results, repeat with `binref -a` to also search the command-line flags.
3. While there are too many results, reduce the search radius: restrict the keywords, or narrow the flag
   (from `-a` to no flag, or from no flag to `-b` for brief-description-only search).

## Multibin Expressions

Many unit arguments accept **multibin expressions**: a syntax that preprocesses data through a chain of handlers before passing it to the unit.
Without a handler prefix, a string matching a file path on disk is replaced by the file's contents; otherwise it is treated as its UTF-8 encoding.
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
If `length` is omitted, copies to the end; if `start` is omitted, it defaults to 0. It behaves like a Python slice.

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

Binary refinery units can be used as handlers.
Command-line arguments are passed in square brackets, separated by commas:
`unit[-x,-y,arg1,arg2]:data` invokes `unit -x -y arg1 arg2` on the data.

```
$ emit md5[-t]:password
5f4dcc3b5aa765d61d8327deb882cf99
```

## Regular Expressions

All regular expressions support a regex extension `(??name)` that expands to a built-in pattern.
Before writing a regular expression manually, consult the table below and simplify by reusing a named pattern.

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
**frames** allow processing each output individually rather than concatenating them with line breaks.

### Opening and Closing Frames

- Append `[` as the **last argument** to a unit to **open a frame**. It must always be the very last argument.
- Append `]` as the **last argument** to a unit to **close one frame layer**; the chunks in that frame are concatenated back together.
- The `sep` unit inserts a separator (default: newline) between chunks before they are joined.

```
$ emit OOOOOOOO | chop 2 [| ccp F | cca . ]
FOO.FOO.FOO.FOO.
```

`chop 2` splits `OOOOOOOO` into the frame `[OO, OO, OO, OO]`.
Inside the frame, `ccp F` prepends `F` to each chunk and `cca .` appends a period.
The closing `]` on `cca` concatenates all chunks back together.

### Frames Are Essential

**Always begin every pipeline with an outer frame** when you intend to use meta variables or any frame-dependent unit (`put`, `pop`, `push`, `iff`, `pick`); without one, these do not function.

### Frame Nesting

Frames can nest to arbitrary depth. Each `[` opens a new layer, each `]` closes one:

```
$ emit OOOOOOOO | chop 4 [| chop 2 [| pf F{}. ]| sep ]
FOO.FOO.
FOO.FOO.
```

`chop 4` produces `[OOOO,OOOO]`, then `chop 2` produces `[[OO,OO],[OO,OO]]`.

Without nesting, `chop 2` simply inserts its multiple outputs into the frame,
producing `[OO,OO,OO,OO]`:

```
$ emit OOOOOOOO | chop 4 [| chop 2 | pf F{}. | sep ]
FOO.
FOO.
FOO.
FOO.
```

### Nesting to Group Multi-Output Chunks

When a unit emits N chunks per match (see Format String Expressions),
open a nested frame with `[[` to group each match's outputs for paired processing:

```
$ emit "name1=4142,name2=4344,name3=4546" | rex (\w+)=(\w+) {1} {2} [[| pop label ]| hex | pf {label}={} | sep ]
name1=AB
name2=CD
name3=EF
```

Without `[[`, the 6 chunks (`name1`,`4142`,`name2`,`4344`,`name3`,`4546`) would be a flat frame
and `pop label` would consume only the first chunk globally.
With `[[`, each pair `[label, hex_value]` becomes its own sub-frame,
so `pop label` takes the first element of each pair as a variable and leaves the second as the data to process.

This is the standard pattern when `rex` produces both **metadata** (names, keys, IVs) and **payload** chunks from the same match:
nest the outputs, `pop` the metadata into variables, process the remaining payload.

### Squeezing

Specify `[]` as the nesting instruction (a single argument, distinct from the separate `[` and `]` used to open/close frames) to fuse all output chunks into one by concatenating them:

```
$ emit XYXYXYXY | chop 4 [| snip 0::2 1::2 []| sep ]
XXYY
XXYY
```

`snip` extracts two slices `0::2` and `1::2`, but they are concatenated immediately rather than emitted as separate chunks.

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

The multibin expression `v:x` retrieves the meta variable's value (`BAR`);
full details are in Frame-Dependent Multibin Handlers below.

### Push and Pop

The unit `push` inserts new data into the frame, defaulting to the current chunk unless a (multibin) argument is provided.
The original is moved out of scope (invisible) while the copy remains visible for a sub-pipeline.
Conversely, `pop varname` consumes the visible chunk(s), stores them as the variable `varname`, and restores the original:

```
$ emit key=value | push [[| resplit = | pick 1 | pop v ]| repl v:v censored ]
key=censored
```

Notably, `pop` can extract more than one chunk from the frame:

```
$ emit binary refinery go [| pop b r | pf {} {b} {r} ]
go binary refinery
```

Since `pop` arguments are multibin expressions, handlers can transform chunks during extraction:

```
$ emit "414243" DEADBEEF [| pop key:hex | pf {key} has {} ]
ABC has DEADBEEF
```

`:hex` hex-decodes the chunk before storing it in `key`. This avoids a separate `push`/decode/`pop` round-trip when the stored form differs from the raw chunk.

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
Variables can be made global with the unit `mvg`, but this should rarely be required.

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

### Scoping

Unlike `pick`, which removes chunks from the frame, `scope` restricts subsequent operations to selected chunks while the rest pass through unchanged.
Use Python slice syntax: `scope ::2` selects every other chunk, `scope 1:` skips the first, `scope 0 3 5` selects by index.

This is essential when a frame contains a mix of chunks that need different treatment.
Rather than extracting items individually into separate pipelines,
extract them all into one frame and use `scope` to target the subset that needs transformation:

```
$ emit AABBCC | chop 2 [| scope ::2 | map AB XY | sep ]
XY
BB
XY
```

`scope ::2` restricts `map` to chunks 0 and 2 (`AA` and `CC`), leaving chunk 1 (`BB`) untouched.

Each `scope` call selects a fresh subset — it does not narrow the previous one.
This means sequential `scope` calls can apply different operations to different subsets of the same frame:

```
$ emit AABBCCDD | chop 2 [| scope 0 2 | map AC WY | scope 1 3 | map BD XZ ]
WWXXYYZZ
```

For chunks 0 and 2,  A->W and C->Y; for chunks 1 and 3, B->X and D->Z.
The closing `]` concatenates all four results in their original order.

Use `scope` when chunks need different treatments; use `push`/`pop` when you need to derive an auxiliary value (a key, IV, or length) from the data for use in a later operation.

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

Reads the value of a meta variable. Only works inside a frame (see Setting Variables).

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

Some units use format string syntax with curly braces, most notably `rex`, `resub`, `struct`, and `pf`.
These expressions can access meta variables and allow post-processing with multibin suffixes.
For details, see the help output of each such unit.

When a format-string unit specifies **multiple output slots** (e.g., `rex pattern {1} {2} {3}`),
each slot produces a **separate chunk** per match.
A regex with 3 groups and 3 output slots emits 3 chunks per match into the frame,
so `rex` can serve as a multi-output source in the **Data Extraction Upfront** pattern below whenever fields are identified by pattern rather than fixed offset.

### Data Extraction Upfront

When an operation requires multiple input streams (e.g. data, key1, key2), a common approach is to
produce all streams as chunks in one frame, then pop the ones you need as variables:

```
$ emit sample [ \
  | vsnip 0x200010:0x10 0x200020:0x10 0x4AAB00:0x4500 | pop key iv | aes --iv=v:iv sha256:v:key | dump payload.bin ]
```

The same pattern applies when fields come from pattern extraction rather than fixed offsets.
Replace `vsnip` with any multi-output unit (`rex`, `snip`, archive extractors)
and use nested framing `[[` when there are multiple matches to process independently:

```
$ emit data.bin [| rex MAGIC(.{16})(.{32})(.*) {1} {2} {3} [[| pop iv key ]| aes --iv=v:iv v:key | dump out/{index}.bin ]
```

Here `rex` emits 3 chunks per match (IV, key, ciphertext); `[[` groups each triple; `pop iv key` stores the first two as variables; the remaining ciphertext is decrypted.

### Sequential Push/Pops

Another approach uses sequential `push` and `pop` operations.
Avoid nesting them; instead use one after another at the same frame depth:

```
$ emit sample [                                     \
  | push [| vsnip 0x200010:0x10 | sha256 | pop k ]  \
  | push [| vsnip 0x200020:0x10 | pop iv ]          \
  | vsnip 0x4AAB00:0x4500 | aes --iv=v:iv v:k | dump payload.bin ]
```

### Incremental Pipeline Construction

For pipelines with more than 3 stages, build incrementally:

1. Start with the first 1-2 units and `peek` to verify the output.
2. Identify the output artifact type:
   - If it is a recognizable format, apply the **Layer Boundary Rule** before adding more stages.
   - If it is empty, missing, or unexpectedly small, apply the **Null Result Rule**.
3. Show the intermediate result to the user.
4. Add the next 1-2 units, `peek` again, and verify.
5. Repeat until the full pipeline is complete.

Never construct a pipeline with 5 or more stages in a single attempt.
Each intermediate `peek` validates assumptions about the data format at that stage,
catching errors early and keeping debugging straightforward.

### Debugging Failing Pipelines

- `peek` forwards all input data, making it a useful debugging tool.
  Use it inside a frame to inspect each chunk individually.
- If a pipeline produces no output or wrong output, bisect it by inserting `peek` statements.
  Move `peek` left or right to find where extraction produces unexpected results.
- If you used `-T` or `-Q` and the output looks wrong, remove these flags and re-run to see the actual error messages.
- Use the `-v` flag on individual units to increase their output verbosity to identify root causes.

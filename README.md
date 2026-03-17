# Binary Refinery Agent

This repository stores a skill for [binary refinery][br].
If you want to enhance your local malware analysis [Claude][ai] with knowledge of how to use it,
 you can install the skill with the following instructions:
```
/plugin marketplace add binref/agent
/plugin install refinery@binref
```
The skill should be triggered automatically when the context is appropriate,
 but you can also invoke it manually with the following command:
```
/refinery
```
This lives in its own repository to avoid cloning the full binary refinery repository when the skill is installed.

[br]: https://github.com/binref/refinery/
[ai]: https://docs.anthropic.com/en/docs/claude-code
# Binary Refinery Agent

This repository stores a [Claude][ai] skill for [Binary Refinery][br].
It can augment your malware analysis agent with a number of useful tools for data extraction and transformation.

> [!CAUTION]
> Make sure you are using [Binary Refinery][br] version 0.10.3 or later.
> The agent relies on changes to the `binref` utility that were introduced here.

The skill can be installed with these commands:
```
/plugin marketplace add binref/agent
/plugin install refinery@binref
```
And activated by using this one:
```
/refinery
```
> [!WARNING]
> The skill should be triggered automatically when the context is appropriate, but this rarely works.
> Claude is too convinced that a Python script is sufficient.
> If you know how to fix this, PRs are very welcome.

> [!NOTE]
> If you are using this and run into any problems, or if you have suggestions for the skill file:
> Open an issue or a pull request!


[br]: https://github.com/binref/refinery/
[ai]: https://docs.anthropic.com/en/docs/claude-code
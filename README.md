# Binary Refinery Agent

This repository stores a [Claude][ai] skill for [Binary Refinery][br].
It can augment your malware analysis agent with a number of useful tools for data extraction and transformation.

> [!CAUTION]
> Make sure you are using refinery version 0.10.3 or later.
> The agent relies on changes to the `binref` utility that were introduced here.

> [!NOTE]
> Bug reports and suggestions are welcome - open an issue or a pull request!

## Installation

The skill can be installed with these commands inside Claude:
```
/plugin marketplace add binref/agent
/plugin install refinery@binref
```
In order to update the skill, you then only have to update the binref marketplace.
From the commandline, run:
```
claude plugin marketplace update binref
```

## Activation

Activate the skill by using this command in Claude:
```
/refinery
```
The skill should be triggered automatically when the context is appropriate, but this rarely works.
Claude is too convinced that a Python script is sufficient.
If you know how to fix this, PRs are very welcome.


[br]: https://github.com/binref/refinery/
[ai]: https://docs.anthropic.com/en/docs/claude-code
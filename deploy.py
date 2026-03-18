import json
import re
import subprocess
import sys

_PLUGIN = '.claude-plugin/plugin.json'
_MARKET = '.claude-plugin/marketplace.json'


def main():
    if len(sys.argv) != 2:
        print(F'Usage: {sys.argv[0]} version', file=sys.stderr)
        return 1

    version = sys.argv[1]

    if not re.fullmatch(r'\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?', version):
        print(F'Invalid version: {version!r} (expected MAJOR.MINOR.PATCH[-prerelease])', file=sys.stderr)
        return 1

    with open(_PLUGIN) as fd:
        plugin = json.load(fd)
    with open(_MARKET) as fd:
        market = json.load(fd)

    plugin['version'] = version
    market['plugins'][0]['version'] = version

    with open(_PLUGIN, 'w') as fd:
        json.dump(plugin, fd, indent=2)
    with open(_MARKET, 'w') as fd:
        json.dump(market, fd, indent=2)

    subprocess.run(['git', 'add', _PLUGIN, _MARKET], check=True)
    subprocess.run(['git', 'commit', '-m', F'release {version}'], check=True)
    subprocess.run(['git', 'tag', version], check=True)
    subprocess.run(['git', 'push'], check=True)
    subprocess.run(['git', 'push', '--tags'], check=True)

    print(f'Released {version}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

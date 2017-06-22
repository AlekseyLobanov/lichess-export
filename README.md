# lichess-export
Export your chess games from lichess.org

# Installation
Requires only Python (2 or 3) and `requests` with `gevent`:
```
pip install grequests
```

Also, on Linux if you want to export to Scid you need to install Scid: `sudo apt-get install scid`.

# Using
Example:
```
python lichess.py -n hippo23 -t pgn -o hippo23.pgn  --threads 6
```
If you want scid base: `python lichess.py -n hippo23 -t scid -o hippo23  --threads 6`

If you have more than 1000 games, you can set` threads` more than `3`. If you have more than 10000 games, set` threads` to `10`

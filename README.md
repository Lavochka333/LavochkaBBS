
xlamBOT is currently the best external Brawl Stars bot.

## Where to get help

Updates, questions and builds: [Канал xlamModz](https://t.me/xlamModz)

## Requirements

- **NVIDIA GPUs**
  - `setup.py` installs `onnxruntime-gpu` when an NVIDIA GPU is detected
  - Falls back to DirectML, then CPU, if CUDA does not load

- **AMD / Intel / iGPU**
  - DirectML on Windows (`onnxruntime-directml`)
  - CPU fallback if DirectML does not load

## Installation

You will need [Python 3.11.9](https://www.python.org/downloads/release/python-3119/).

### Windows

```sh
python setup.py install
```

### Other Platforms

The official xlamBOT does **NOT** support other platforms such as Linux or Mac, but you can visit [Unofficial Ports](https://github.com/4D1-TooFarGone/Pyla-Ports) for cross-platform support.

## Using xlamBOT

> [!NOTE]
> **Note**: This open-source version runs in localhost mode. The cloud features have been disabled by default.

Run the bot:

```sh
python main.py
```

### Startup options

| Flag | Effect |
| --- | --- |
| *(none)* | Console visible, UI in the xlamBOT desktop window |
| `--no-console` | Hides the console window, output goes to `xlambot.log` in the current folder. Ignored when xlamBOT is started from an existing terminal, so your own terminal is never hidden. |
| `--no-webapp` | Opens the UI in the default browser instead of the desktop window |

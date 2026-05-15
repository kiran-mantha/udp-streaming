# UDP Stream RPi

Low-latency live streaming from a Raspberry Pi camera to a web browser. Uses UDP for camera-to-server transport, transcodes on-the-fly to HLS, and serves with a 10-second rolling buffer for instant playback.

## Architecture

```
[Pi Camera] ──UDP/JPEG──► [receiver.py] ──pipe──► [ffmpeg] ──.ts segments──► [buffer/]
                              ↕                                                    ↕
                      [archival .mjpeg/.mp4]                              [stream-server.py]
                                                                               ↕
                                                                          [Browser (hls.js)]
```

| Component | Runs on | Role |
|-----------|---------|------|
| `streamer.py` | Raspberry Pi | Captures camera, sends JPEG frames via UDP |
| `receiver.py` | Server | Receives UDP, pipes to ffmpeg for HLS, archives to MP4 |
| `stream-server.py` | Server | Flask app that serves HLS segments + player page |
| `viewer.py` | Server | Direct UDP viewer (debug tool, no HLS) |

## Setup

### 1. Prerequisites

- Python 3.11+
- ffmpeg (must be in PATH)

### 2. Virtual environment

```bash
cd udp-stream-rpi
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / RPi
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**On Raspberry Pi only**, also install picamera2:

```bash
pip install picamera2
```

### 4. Configure IP addresses

Edit `edge-device/streamer.py` and update:

```python
DEST_IP = "192.168.0.100"   # IP of the receiving server
DEST_PORT = 5000
```

## Running

Start these in order (three separate terminals on the server, one on the Pi):

### Terminal 1 — Stream server (anytime)

```bash
cd udp-stream-rpi
venv\Scripts\activate     # or source venv/bin/activate
python server/stream-server.py
```

Serves the player at `http://0.0.0.0:8080/live/`

### Terminal 2 — UDP receiver

```bash
cd udp-stream-rpi
venv\Scripts\activate
python server/receiver.py
```

Listens on UDP port 5000, writes HLS segments to `server/buffer/`, archives full stream to `server/videos/`.

### Terminal 3 — Camera streamer (on Raspberry Pi)

```bash
cd udp-stream-rpi
source venv/bin/activate
python edge-device/streamer.py
```

Sends MJPEG frames at 30 fps via UDP.

### View the stream

Open `http://<server-ip>:8080/live/` in any browser.

The player downloads 10 seconds of buffered segments instantly, so playback starts with zero buffering.

## File structure

```
udp-stream-rpi/
├── edge-device/
│   └── streamer.py       Camera capture + UDP sender (RPi/Windows)
├── server/
│   ├── receiver.py        UDP listener → HLS + archival recording
│   ├── stream-server.py   Flask HTTP server for HLS serving
│   ├── viewer.py          Direct UDP viewer (debug only)
│   ├── templates/
│   │   └── player.html    hls.js browser player
│   ├── buffer/            HLS segments (auto-created)
│   └── videos/            Archival MP4 recordings (auto-created)
└── venv/                  Python virtual environment
```

## Configuration

All settings are hardcoded as module-level constants in each script:

| Constant | Default | File |
|----------|---------|------|
| `DEST_IP` | `192.168.10.35` | `streamer.py` |
| `DEST_PORT` | `5000` | `streamer.py`, `receiver.py` |
| `FRAME_RATE` | `30` | `streamer.py`, `receiver.py` |
| `SEGMENT_DURATION` | `2` (seconds) | `receiver.py` |
| `HLS_LIST_SIZE` | `5` (10s buffer) | `receiver.py` |
| `HTTP_PORT` | `8080` | `stream-server.py` |
| `BUFFER_SIZE` | `65507` | Both |

## How it works

1. **streamer.py** captures frames from the camera, encodes them as JPEG, and sends each frame as a single UDP datagram.

2. **receiver.py** receives UDP datagrams, appends them to an archival `.mjpeg` file, and simultaneously pipes them through ffmpeg for live HLS transcoding (JPEG → H.264, 2-second segments, 10-second rolling window).

3. **stream-server.py** serves the HLS playlist and segments via HTTP. The browser player (hls.js) loads the playlist and downloads all buffered segments at once — filling its buffer instantly for zero-delay startup.

4. When the receiver stops, the `.mjpeg` file is automatically converted to `.mp4` for archival.

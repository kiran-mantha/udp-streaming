import json
import os
import socket
import subprocess
import datetime
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000
OUTPUT_FOLDER = os.path.join(BASE_DIR, "videos")
BUFFER_FOLDER = os.path.join(BASE_DIR, "buffer")
BUFFER_SIZE = 65507
FRAME_RATE = 30
SEGMENT_DURATION = 2
HLS_LIST_SIZE = 5
TIMEOUT_SECONDS = 5

stop_event = threading.Event()


def start_key_listener():
    def _listen():
        try:
            import msvcrt
            while not stop_event.is_set():
                if msvcrt.kbhit() and msvcrt.getch().lower() == b'q':
                    stop_event.set()
                    break
        except ImportError:
            import sys
            import select
            import tty
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            try:
                while not stop_event.is_set():
                    r, _, _ = select.select([sys.stdin], [], [], 0.5)
                    if r and sys.stdin.read(1) == 'q':
                        stop_event.set()
                        break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    t = threading.Thread(target=_listen, daemon=True)
    t.start()


def setup_directories():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(BUFFER_FOLDER, exist_ok=True)


def clean_buffer():
    for entry in os.listdir(BUFFER_FOLDER):
        if entry.endswith(('.ts', '.m3u8', '.jpg', '.json', '.log')):
            try:
                os.remove(os.path.join(BUFFER_FOLDER, entry))
            except OSError:
                pass


def init_archival_recording():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    mjpeg_path = os.path.join(OUTPUT_FOLDER, f"stream_{timestamp}.mjpeg")
    mp4_path = os.path.join(OUTPUT_FOLDER, f"stream_{timestamp}.mp4")
    mjpeg_file = open(mjpeg_path, 'wb')
    return mjpeg_file, mjpeg_path, mp4_path


def init_hls_pipeline():
    clean_buffer()
    hls_cmd = [
        "ffmpeg",
        "-f", "mjpeg",
        "-use_wallclock_as_timestamps", "1",
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-vsync", "cfr",
        "-g", str(FRAME_RATE * SEGMENT_DURATION),
        "-sc_threshold", "0",
        "-pix_fmt", "yuv420p",
        "-f", "hls",
        "-hls_time", str(SEGMENT_DURATION),
        "-hls_list_size", str(HLS_LIST_SIZE),
        "-hls_flags", "delete_segments+temp_file",
        "-hls_segment_filename",
        os.path.join(BUFFER_FOLDER, "segment_%05d.ts"),
        os.path.join(BUFFER_FOLDER, "stream.m3u8")
    ]
    log_path = os.path.join(BUFFER_FOLDER, "ffmpeg.log")
    log_file = open(log_path, 'w')
    proc = subprocess.Popen(hls_cmd, stdin=subprocess.PIPE, stderr=log_file)
    return proc, log_file


def init_udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    return sock


def write_status(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def convert_to_mp4(mjpeg_path, mp4_path):
    print("Converting to MP4...")
    cmd = [
        "ffmpeg",
        "-f", "mjpeg",
        "-i", mjpeg_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", str(FRAME_RATE),
        "-y",
        mp4_path
    ]
    subprocess.run(cmd)
    os.remove(mjpeg_path)
    print(f"Video saved to: {mp4_path}")


def main():
    setup_directories()

    mjpeg_file, mjpeg_path, mp4_path = init_archival_recording()
    ffmpeg_proc, ffmpeg_log = init_hls_pipeline()
    sock = init_udp_socket()

    print(f"Listening on {LISTEN_IP}:{LISTEN_PORT}")
    print(f"Recording to: {mjpeg_path}")
    print(f"HLS buffer: {BUFFER_FOLDER}/stream.m3u8 ({HLS_LIST_SIZE * SEGMENT_DURATION}s)")
    print("Press 'q' to stop")

    sock.settimeout(0.5)
    start_key_listener()

    frame_count = 0
    start_time = datetime.datetime.now()
    last_data_time = datetime.datetime.now()
    was_disconnected = False
    last_frame_data = None
    status_path = os.path.join(BUFFER_FOLDER, "status.json")
    latest_jpg_path = os.path.join(BUFFER_FOLDER, "latest.jpg")

    def update_status(overrides=None):
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        fps = frame_count / elapsed if elapsed > 0 else 0
        data = {
            "status": "live",
            "frames": frame_count,
            "fps": round(fps, 1),
            "uptime_seconds": round(elapsed, 1),
            "buffer_segments": HLS_LIST_SIZE,
            "buffer_duration_seconds": HLS_LIST_SIZE * SEGMENT_DURATION,
            "segment_duration": SEGMENT_DURATION
        }
        if overrides:
            data.update(overrides)
        write_status(status_path, data)

    try:
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                elapsed_since_data = (datetime.datetime.now() - last_data_time).total_seconds()
                if elapsed_since_data > TIMEOUT_SECONDS and not was_disconnected:
                    was_disconnected = True
                    print(f"WARNING: No data for {TIMEOUT_SECONDS}s — camera disconnected")
                    update_status({"status": "disconnected"})
                continue

            if was_disconnected:
                was_disconnected = False
                gap = (datetime.datetime.now() - last_data_time).total_seconds()
                print(f"Camera reconnected after {gap:.0f}s gap")

            last_data_time = datetime.datetime.now()

            mjpeg_file.write(data)

            if ffmpeg_proc.stdin and data:
                try:
                    ffmpeg_proc.stdin.write(data)
                except BrokenPipeError:
                    pass

            last_frame_data = data
            frame_count += 1

            if frame_count % FRAME_RATE == 0 and last_frame_data:
                try:
                    with open(latest_jpg_path, 'wb') as f:
                        f.write(last_frame_data)
                except OSError:
                    pass

            if frame_count % 300 == 0:
                print(f"Received {frame_count} frames ({frame_count / (datetime.datetime.now() - start_time).total_seconds():.1f} fps)")
                update_status()

    except KeyboardInterrupt:
        stop_event.set()
        print("\nStopping receiver")

    mjpeg_file.close()
    sock.close()

    if ffmpeg_proc.stdin:
        try:
            ffmpeg_proc.stdin.close()
        except:
            pass
    ffmpeg_proc.wait(timeout=10)
    ffmpeg_log.close()

    convert_to_mp4(mjpeg_path, mp4_path)

    write_status(status_path, {"status": "offline", "frames": frame_count})


if __name__ == "__main__":
    main()
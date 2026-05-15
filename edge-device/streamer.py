import platform
import threading
import cv2
import socket
import time

DEST_IP = "192.168.10.35"
DEST_PORT = 5000
BUFFER_SIZE = 65507
FRAME_RATE = 30
FRAME_DELAY = 1.0 / FRAME_RATE

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


def is_raspberry_pi():
    try:
        with open("/sys/firmware/devicetree/base/model") as f:
            return "Raspberry Pi" in f.read()
    except OSError:
        return False


def init_camera(is_rpi):
    if is_rpi:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        config = picam2.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"},
            controls={
                "AwbEnable": True,
                "Brightness": 0.05,
                "Contrast": 1.0,
                "Saturation": 1.3,
            }
        )
        picam2.configure(config)
        picam2.start()
        time.sleep(2)
        return picam2, True

    is_windows = platform.system() == "Windows"
    api = cv2.CAP_DSHOW if is_windows else cv2.CAP_ANY
    cap = cv2.VideoCapture(0, api)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")
    return cap, False


def capture_frame(camera, use_picamera):
    if use_picamera:
        frame = camera.capture_array()
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    ret, frame = camera.read()
    return frame if ret else None


def release_camera(camera, use_picamera):
    if use_picamera:
        camera.stop()
    else:
        camera.release()


def main():
    is_rpi = is_raspberry_pi()

    try:
        camera, use_picamera = init_camera(is_rpi)
    except ImportError:
        print("Error: picamera2 not installed on Raspberry Pi. Run: pip install picamera2")
        exit(1)
    except Exception as e:
        print(f"Error: Could not initialize camera — {e}")
        exit(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Streaming to {DEST_IP}:{DEST_PORT} at {FRAME_RATE}fps")
    print("Press 'q' to stop")

    frame_count = 0
    start_time = time.time()
    start_key_listener()

    try:
        while not stop_event.is_set():
            loop_start = time.time()

            frame = capture_frame(camera, use_picamera)
            if frame is None:
                continue

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            data = buffer.tobytes()

            if len(data) <= BUFFER_SIZE:
                sock.sendto(data, (DEST_IP, DEST_PORT))
            else:
                print(f"Frame too large ({len(data)} bytes), skipped")
                continue

            frame_count += 1

            if frame_count % 300 == 0:
                elapsed = time.time() - start_time
                print(f"Sent {frame_count} frames ({frame_count / elapsed:.1f} fps)")

            elapsed = time.time() - loop_start
            sleep_time = FRAME_DELAY - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        stop_event.set()
        print("\nStopping stream")

    release_camera(camera, use_picamera)
    sock.close()
    print(f"Total frames sent: {frame_count}")


if __name__ == "__main__":
    main()
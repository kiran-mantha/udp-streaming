import cv2
import numpy as np
import socket
import time

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000
BUFFER_SIZE = 65507

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

print(f"Live viewer running on {LISTEN_IP}:{LISTEN_PORT}")
print("Press 'q' or ESC to quit")

frame_count = 0
start_time = time.time()

try:
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)

        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            continue

        frame_count += 1

        elapsed = time.time() - start_time
        fps = frame_count / elapsed

        cv2.putText(frame, f"{fps:.1f} fps", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("UDP Stream", frame)

        key = cv2.pollKey() & 0xFF
        if key == ord('q') or key == 27:
            break

except KeyboardInterrupt:
    print("\nStopping viewer")

sock.close()
cv2.destroyAllWindows()
print(f"Received {frame_count} frames in {elapsed:.1f}s ({fps:.1f} fps)")
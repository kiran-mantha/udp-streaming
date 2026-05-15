# Secure Streaming Architecture – Future Upgrade Plan

## Current Architecture

```text
Camera Device
    ↓ UDP Stream
Receiver Node
    ↓ stores .ts files
HTTP Static Server
    ↓
Clients/Viewers
```

Additional communication channel:

```text
Camera ↔ Server Socket Connection
```

This socket channel can later become:

* Authentication channel
* Device registration channel
* Heartbeat channel
* Encryption key exchange channel
* Stream authorization layer
* Remote control plane

---

# Current Security Weaknesses

## 1. Plain UDP Streaming

Current UDP packets are likely unencrypted.

Risks:

* Packet sniffing
* Replay attacks
* Unauthorized viewing
* Fake camera injection
* Packet manipulation
* Stream hijacking

---

## 2. Public Static TS Files

If `.ts` files are directly accessible:

```text
http://server/cam1/001.ts
```

then anyone with the URL can access the stream.

---

# Future Secure Streaming Architecture

```text
Edge Camera
    ↓
Encrypted Transport (SRT/SRTP)
    ↓
Receiver Gateway
    ↓
Encrypted HLS Segments
    ↓
Secure Storage
    ↓
Authenticated API Gateway
    ↓
Authorized Viewers
```

---

# Phase 1 – Device Authentication

Before a camera can stream:

```text
Camera → Server
```

must authenticate.

## Recommended Authentication

### Option A — JWT Based

Each camera receives:

* Camera ID
* Secret Key
* JWT Token

Example:

```json
{
  "camera_id": "cam_01",
  "timestamp": 17100000,
  "signature": "HMAC_SHA256"
}
```

Server validates:

* Camera exists
* Signature valid
* Timestamp fresh
* Token not expired

---

## Better Future Option

Use:

* Mutual TLS
* Device certificates
* PKI infrastructure

Recommended for large deployments.

---

# Phase 2 – Secure Transport Layer

## Replace Raw UDP

Current:

```text
Raw UDP Video Stream
```

Target:

```text
Encrypted Media Transport
```

---

# Recommended Protocol – SRT

Use:

* Secure Reliable Transport (SRT)

Benefits:

* AES encryption
* Packet recovery
* Low latency
* UDP-based
* Internet friendly
* NAT traversal
* Production-grade reliability

Used by:

* Broadcasters
* Remote drone systems
* IPTV
* CCTV systems

---

## Example SRT Sender

```bash
ffmpeg \
-f v4l2 \
-i /dev/video0 \
-c:v h264 \
-f mpegts \
"srt://SERVER_IP:9000?mode=caller&passphrase=StrongPass123&pbkeylen=32"
```

---

## Example SRT Receiver

```bash
ffmpeg \
-i "srt://0.0.0.0:9000?mode=listener&passphrase=StrongPass123&pbkeylen=32" \
-c copy output.ts
```

---

# Alternative Protocol – SRTP

Another possible option:

* Secure RTP (SRTP)

Provides:

* AES encryption
* Replay protection
* Authentication
* Low latency

Used heavily in:

* VoIP
* WebRTC
* Real-time communications

However:

For surveillance + recording systems:

```text
SRT is generally simpler and more scalable.
```

---

# Phase 3 – Segment Encryption

Even after secure transport:

Stored `.ts` files should remain encrypted.

---

## Recommended Encryption

Use:

```text
AES-256-GCM
```

Benefits:

* Encryption
* Integrity verification
* Tamper detection

---

## Encrypted Storage Structure

```text
segments/
   segment_001.ts.enc
   segment_002.ts.enc
   segment_003.ts.enc
```

Keys:

```text
keys/
   cam_01/
      segment_001.key
```

---

# Phase 4 – HLS Streaming Layer

Current system already stores `.ts` files.

This makes migration to:

```text
HLS (HTTP Live Streaming)
```

very easy.

---

# Recommended HLS Structure

```text
stream.m3u8
segment_001.ts
segment_002.ts
segment_003.ts
```

---

# HLS Encryption

Use:

```text
AES-128 encrypted HLS
```

Example FFmpeg command:

```bash
ffmpeg \
-i input.mp4 \
-hls_time 2 \
-hls_key_info_file key_info.txt \
output.m3u8
```

Example `key_info.txt`

```text
https://server/key
local.key
01234567890123456789012345678901
```

---

# Phase 5 – Secure Viewer Access

Never expose direct static files publicly.

Bad:

```text
http://server/cam1/001.ts
```

Recommended:

```text
/api/stream/cam1/001.ts?token=SIGNED_TOKEN
```

---

# Signed URL Architecture

Token should contain:

* User ID
* Camera permission
* Expiry time
* Signature

Benefits:

* Expiring access
* Per-user authorization
* Revocable sessions
* Access logging

---

# Recommended Web Server

Use:

* Nginx

Features:

* JWT auth
* Signed URLs
* Secure proxying
* Rate limiting
* Scalable static delivery
* TLS termination

---

# Phase 6 – TLS Everywhere

All APIs should use:

```text
HTTPS/TLS
```

Protect:

* Authentication APIs
* Viewer APIs
* Key exchange APIs
* Device management APIs

---

# Future Viewer Architecture

```text
Client
   ↓ HTTPS
API Gateway
   ↓
Authenticated Stream Access
   ↓
Nginx HLS Server
   ↓
Encrypted TS Segments
```

---

# Future Scalability Architecture

```text
Multiple Cameras
       ↓
SRT Ingestion Cluster
       ↓
Receiver Workers
       ↓
Segment Processors
       ↓
Distributed Storage
       ↓
CDN/Nginx Layer
       ↓
Clients
```

---

# Recommended Technology Stack

## Transport Layer

Preferred:

* SRT

Optional:

* SRTP
* WebRTC

---

## Encoding

* H264
* H265 (future optimization)

---

## Segment Format

* HLS (.m3u8 + .ts)

---

## Encryption

* AES-256-GCM
* AES-128 HLS encryption

---

## Authentication

* JWT
* Mutual TLS (future)

---

## Web Layer

* Nginx
* Django/FastAPI/Spring Boot API Gateway

---

## Storage

* Local SSD
* MinIO
* S3-compatible object storage

---

# Future Advanced Direction

Eventually move toward:

* WebRTC

If requirements include:

* Sub-second latency
* Browser playback
* Interactive communication
* Remote drone control
* Real-time operations

---

# Recommended Upgrade Path

## Step 1

Replace raw UDP with:

```text
SRT encrypted transport
```

---

## Step 2

Migrate static TS serving into:

```text
HLS architecture
```

---

## Step 3

Enable:

```text
Encrypted HLS segments
```

---

## Step 4

Add:

```text
JWT-based authenticated viewing
```

---

## Step 5

Deploy:

```text
Nginx reverse proxy + TLS
```

---

## Step 6

Add:

```text
Distributed storage + CDN
```

for scalability.

---

# Important Security Principle

Never implement custom encryption protocols.

Always use:

* AES-GCM
* TLS
* SRT
* SRTP
* DTLS

because media streaming crypto is extremely easy to implement incorrectly.

---

# Final Recommended Production Architecture

```text
Camera Device
    ↓ SRT (Encrypted)
Receiver Gateway
    ↓
FFmpeg Segmenter
    ↓
Encrypted HLS Segments
    ↓
Object Storage
    ↓
Nginx Secure Delivery
    ↓
Authenticated Client Access
```

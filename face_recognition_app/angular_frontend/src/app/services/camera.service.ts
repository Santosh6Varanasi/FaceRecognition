import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { FaceApiService, Detection } from './face-api.service';

@Injectable({ providedIn: 'root' })
export class CameraService {
  sessionId: string | null = null;
  isCapturing = false;
  cameraError: string | null = null;
  totalUnknownsInSession = 0;

  private stream: MediaStream | null = null;
  private captureInterval: ReturnType<typeof setInterval> | null = null;
  private framesSent = 0;       // frames actually sent to API
  private pendingRequest = false;

  constructor(private faceApi: FaceApiService) {}

  async startCamera(videoEl: HTMLVideoElement): Promise<void> {
    this.cameraError = null;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoEl.srcObject = this.stream;
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Video timeout')), 10000);
        videoEl.onloadedmetadata = () => {
          videoEl.play().then(() => {
            clearTimeout(timeout);
            resolve();
          }).catch(reject);
        };
      });
    } catch (err) {
      this.cameraError = 'Camera access denied. Please allow camera permissions and reload.';
      throw err;
    }
  }

  startSession(): Observable<string> {
    return new Observable(observer => {
      this.faceApi.startSession().subscribe({
        next: res => {
          this.sessionId = res.session_id;
          this.totalUnknownsInSession = 0;
          this.framesSent = 0;
          observer.next(res.session_id);
          observer.complete();
        },
        error: err => observer.error(err)
      });
    });
  }

  endSession(sessionId: string): Observable<any> {
    // Use actual frames sent count
    return this.faceApi.endSession(sessionId, this.framesSent);
  }

  startCapture(
    videoEl: HTMLVideoElement,
    captureCanvas: HTMLCanvasElement,
    overlayCanvas: HTMLCanvasElement,
    sessionId: string,
    onDetections: (detections: Detection[]) => void
  ): void {
    this.isCapturing = true;
    this.pendingRequest = false;
    const captureCtx = captureCanvas.getContext('2d');

    this.captureInterval = setInterval(() => {
      // Only send frames when: session active, video ready, no request in flight
      if (!this.isCapturing) return;
      if (!captureCtx) return;
      if (videoEl.readyState < 2 || videoEl.videoWidth === 0) return;
      if (this.pendingRequest) return;

      captureCanvas.width = videoEl.videoWidth;
      captureCanvas.height = videoEl.videoHeight;
      captureCtx.drawImage(videoEl, 0, 0, captureCanvas.width, captureCanvas.height);

      const frameData = captureCanvas.toDataURL('image/jpeg', 0.8)
        .replace('data:image/jpeg;base64,', '');

      this.pendingRequest = true;
      this.framesSent++;

      this.faceApi.processFrame(frameData, sessionId).subscribe({
        next: result => {
          this.pendingRequest = false;
          if (!this.isCapturing) return; // session ended while request was in flight
          const unknowns = result.detections.filter(d => d.name === 'Unknown').length;
          this.totalUnknownsInSession += unknowns;
          onDetections(result.detections);
        },
        error: err => {
          this.pendingRequest = false;
          console.error('Frame processing error', err);
        }
      });
    }, 500);
  }

  stopCapture(): void {
    this.isCapturing = false;
    if (this.captureInterval !== null) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }
    this.pendingRequest = false;
  }

  stopCamera(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
  }
}

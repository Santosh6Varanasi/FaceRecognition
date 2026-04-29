import { Component, ViewChild, ElementRef, OnDestroy } from '@angular/core';
import { NgIf } from '@angular/common';
import { CameraService } from '../../services/camera.service';
import { Detection } from '../../services/face-api.service';

@Component({
  selector: 'app-camera-monitor',
  standalone: true,
  imports: [NgIf],
  template: `
    <div>
      <div class="page-header">
        <h1>Camera Monitor</h1>
      </div>

      <div class="camera-container" style="position:relative;display:inline-block;">
        <video #videoEl autoplay playsinline width="640" height="480"
               style="background:#000; border-radius:8px; display:block;"
               (playing)="onVideoPlaying()"></video>
        <!-- Overlay canvas sits on top of the video for bounding boxes -->
        <canvas #overlayCanvas width="640" height="480"
                style="position:absolute;top:0;left:0;pointer-events:none;border-radius:8px;"></canvas>
        <!-- Hidden capture canvas — used only to grab frames, never shown -->
        <canvas #captureCanvas width="640" height="480"
                style="display:none;"></canvas>
      </div>

      <div class="camera-controls">
        <button class="btn-primary"
                [disabled]="!!cameraService.cameraError || cameraService.isCapturing"
                (click)="onStartSession()">
          Start Session
        </button>
        <button class="btn-danger"
                [disabled]="!cameraService.isCapturing"
                (click)="onStopSession()">
          Stop Session
        </button>
      </div>

      <div class="camera-stats" *ngIf="cameraService.isCapturing">
        Faces in frame: {{ facesInFrame }} | Unknowns this session: {{ cameraService.totalUnknownsInSession }}
      </div>

      <div class="error-message" *ngIf="cameraService.cameraError">
        {{ cameraService.cameraError }}
      </div>

      <div class="toast" *ngIf="mlUnavailable">
        ML service unavailable — camera still active, no detections until model is trained.
      </div>
    </div>
  `
})
export class CameraMonitorComponent implements OnDestroy {
  @ViewChild('videoEl') videoElRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('overlayCanvas') overlayCanvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('captureCanvas') captureCanvasRef!: ElementRef<HTMLCanvasElement>;

  facesInFrame = 0;
  mlUnavailable = false;
  streamIsLive = false;
  hasReceivedFirstDetection = false;
  private sessionId: string | null = null;

  constructor(public cameraService: CameraService) {}

  onVideoPlaying(): void {
    this.streamIsLive = true;
  }

  async onStartSession(): Promise<void> {
    this.streamIsLive = false;
    this.hasReceivedFirstDetection = false;

    const videoEl = this.videoElRef.nativeElement;
    const overlayCanvas = this.overlayCanvasRef.nativeElement;
    const captureCanvas = this.captureCanvasRef.nativeElement;

    // Clear any stale overlay from previous session
    const ctx = overlayCanvas.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    try {
      await this.cameraService.startCamera(videoEl);
    } catch {
      return;
    }

    // Small delay to ensure video frame is rendering before we start capture
    await new Promise(resolve => setTimeout(resolve, 800));

    this.cameraService.startSession().subscribe({
      next: sessionId => {
        this.sessionId = sessionId;
        this.cameraService.startCapture(videoEl, captureCanvas, overlayCanvas, sessionId, detections => {
            if (!this.hasReceivedFirstDetection) this.hasReceivedFirstDetection = true;
            this.drawDetections(detections);
          });
      },
      error: err => {
        if (err?.status === 503) this.mlUnavailable = true;
        console.error('Failed to start session', err);
      }
    });
  }

  onStopSession(): void {
    this.streamIsLive = false;
    this.hasReceivedFirstDetection = false;

    // Stop frame capture immediately
    this.cameraService.stopCapture();

    // Clear overlay
    const overlayCanvas = this.overlayCanvasRef.nativeElement;
    const ctx = overlayCanvas.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    // End session on server (uses internal framesSent count)
    if (this.sessionId) {
      this.cameraService.endSession(this.sessionId).subscribe({
        error: err => console.error('Failed to end session', err)
      });
      this.sessionId = null;
    }

    this.cameraService.stopCamera();
    this.facesInFrame = 0;
  }

  private drawDetections(detections: Detection[]): void {
    if (!this.streamIsLive || !this.hasReceivedFirstDetection) return;

    const canvasEl = this.overlayCanvasRef.nativeElement;
    const videoEl = this.videoElRef.nativeElement;
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    // Match overlay size to actual video dimensions
    canvasEl.width = videoEl.videoWidth || 640;
    canvasEl.height = videoEl.videoHeight || 480;

    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    this.facesInFrame = detections.length;

    for (const det of detections) {
      const { x1, y1, x2, y2 } = det.bbox;
      const isUnknown = !det.name || det.name === 'Unknown';
      const label = `${isUnknown ? 'Unknown' : det.name} ${(det.confidence * 100).toFixed(0)}%`;

      // Draw bounding box
      ctx.strokeStyle = isUnknown ? '#ef4444' : '#22c55e';
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      // Draw label background
      ctx.font = 'bold 13px sans-serif';
      const textWidth = ctx.measureText(label).width;
      ctx.fillStyle = isUnknown ? '#ef4444' : '#22c55e';
      ctx.fillRect(x1, y1 - 22, textWidth + 10, 22);

      // Draw label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x1 + 5, y1 - 6);
    }
  }

  ngOnDestroy(): void {
    this.cameraService.stopCapture();
    this.cameraService.stopCamera();
  }
}

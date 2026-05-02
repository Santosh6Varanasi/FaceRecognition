import { Component, ViewChild, ElementRef, inject, signal, ChangeDetectionStrategy } from '@angular/core';

import { CameraService } from '../../services/camera.service';
import { Detection } from '../../services/face-api.service';

@Component({
    selector: 'app-camera-monitor',
    standalone: true,
    imports: [],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <div class="container mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div class="page-header">
        <h1 class="page-title">Camera Monitor</h1>
      </div>
    
      <div class="flex justify-center mb-6">
        <div class="relative inline-block rounded-lg overflow-hidden shadow-lg">
          <video #videoEl autoplay playsinline width="640" height="480"
            class="bg-black rounded-lg block max-w-full h-auto"
            (playing)="onVideoPlaying()"
            aria-label="Live camera feed for face detection">
          </video>
          <!-- Overlay canvas sits on top of the video for bounding boxes -->
          <canvas #overlayCanvas width="640" height="480"
            class="absolute top-0 left-0 pointer-events-none rounded-lg"
            aria-label="Face detection overlay">
          </canvas>
          <!-- Hidden capture canvas — used only to grab frames, never shown -->
          <canvas #captureCanvas width="640" height="480" class="hidden" aria-hidden="true"></canvas>
        </div>
      </div>
    
      <div class="flex flex-wrap gap-3 justify-center mb-6" role="group" aria-label="Camera controls">
        <button class="btn-primary"
          [disabled]="!!cameraService.cameraError || cameraService.isCapturing"
          (click)="onStartSession()"
          aria-label="Start camera session"
          [attr.aria-disabled]="!!cameraService.cameraError || cameraService.isCapturing">
          Start Session
        </button>
        <button class="btn-danger"
          [disabled]="!cameraService.isCapturing"
          (click)="onStopSession()"
          aria-label="Stop camera session"
          [attr.aria-disabled]="!cameraService.isCapturing">
          Stop Session
        </button>
      </div>
    
      @if (cameraService.isCapturing) {
        <div class="text-center text-slate-700 dark:text-slate-300 text-sm mb-4"
             role="status"
             aria-live="polite"
             aria-label="Detection statistics">
          Faces in frame: <span class="font-semibold">{{ facesInFrame() }}</span> | 
          Unknowns this session: <span class="font-semibold">{{ cameraService.totalUnknownsInSession }}</span>
        </div>
      }
    
      @if (cameraService.cameraError) {
        <div class="error-message max-w-2xl mx-auto"
             role="alert"
             aria-live="assertive">
          {{ cameraService.cameraError }}
        </div>
      }
    
      @if (mlUnavailable()) {
        <div class="toast"
             role="alert"
             aria-live="polite">
          ML service unavailable — camera still active, no detections until model is trained.
        </div>
      }
    </div>
    `
})
export class CameraMonitorComponent {
  @ViewChild('videoEl') videoElRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('overlayCanvas') overlayCanvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('captureCanvas') captureCanvasRef!: ElementRef<HTMLCanvasElement>;

  cameraService = inject(CameraService);
  
  // Signal-based state
  facesInFrame = signal(0);
  mlUnavailable = signal(false);
  streamIsLive = signal(false);
  hasReceivedFirstDetection = signal(false);
  private sessionId = signal<string | null>(null);

  onVideoPlaying(): void {
    this.streamIsLive.set(true);
  }

  async onStartSession(): Promise<void> {
    this.streamIsLive.set(false);
    this.hasReceivedFirstDetection.set(false);

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
        this.sessionId.set(sessionId);
        this.cameraService.startCapture(videoEl, captureCanvas, overlayCanvas, sessionId, detections => {
            if (!this.hasReceivedFirstDetection()) this.hasReceivedFirstDetection.set(true);
            this.drawDetections(detections);
          });
      },
      error: err => {
        if (err?.status === 503) this.mlUnavailable.set(true);
        console.error('Failed to start session', err);
      }
    });
  }

  onStopSession(): void {
    this.streamIsLive.set(false);
    this.hasReceivedFirstDetection.set(false);

    // Stop frame capture immediately
    this.cameraService.stopCapture();

    // Clear overlay
    const overlayCanvas = this.overlayCanvasRef.nativeElement;
    const ctx = overlayCanvas.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    // End session on server (uses internal framesSent count)
    const currentSessionId = this.sessionId();
    if (currentSessionId) {
      this.cameraService.endSession(currentSessionId).subscribe({
        error: err => console.error('Failed to end session', err)
      });
      this.sessionId.set(null);
    }

    this.cameraService.stopCamera();
    this.facesInFrame.set(0);
  }

  private drawDetections(detections: Detection[]): void {
    if (!this.streamIsLive() || !this.hasReceivedFirstDetection()) return;

    const canvasEl = this.overlayCanvasRef.nativeElement;
    const videoEl = this.videoElRef.nativeElement;
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    // Match overlay size to actual video dimensions
    canvasEl.width = videoEl.videoWidth || 640;
    canvasEl.height = videoEl.videoHeight || 480;

    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    this.facesInFrame.set(detections.length);

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
}

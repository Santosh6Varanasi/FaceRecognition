import {
  Component,
  Input,
  ViewChild,
  ElementRef,
  AfterViewInit,
  inject,
  signal,
  ChangeDetectionStrategy
} from '@angular/core';


import { VideoService, VideoDetection } from '../../services/video.service';

@Component({
    selector: 'app-detection-overlay',
    standalone: true,
    imports: [],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <canvas #overlayCanvas
            class="absolute top-0 left-0 pointer-events-none rounded-lg">
    </canvas>
  `,
    styles: []
})
export class DetectionOverlayComponent implements AfterViewInit {
  @Input() videoId!: number;
  @Input() currentTime: number = 0;
  @Input() videoWidth: number = 0;
  @Input() videoHeight: number = 0;
  @Input() displayWidth: number = 0;
  @Input() displayHeight: number = 0;

  @ViewChild('overlayCanvas') canvasRef?: ElementRef<HTMLCanvasElement>;

  private videoService = inject(VideoService);
  
  // Signal-based state
  private detections = signal<VideoDetection[]>([]);
  private lastFetchTime = signal<number>(-1);
  private readonly fetchThreshold: number = 0.25; // 250ms tolerance

  ngAfterViewInit(): void {
    this.updateCanvasSize();
  }

  // Called when video dimensions change
  updateCanvasSize(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;

    canvas.width = this.videoWidth;
    canvas.height = this.videoHeight;
    canvas.style.width = `${this.displayWidth}px`;
    canvas.style.height = `${this.displayHeight}px`;
  }

  // Called when currentTime changes (from parent video player)
  onTimeUpdate(timestamp: number): void {
    // Only fetch if timestamp changed significantly (> 250ms)
    if (Math.abs(timestamp - this.lastFetchTime()) > this.fetchThreshold) {
      this.fetchDetections(timestamp);
      this.lastFetchTime.set(timestamp);
    }
  }

  private fetchDetections(timestamp: number): void {
    this.videoService.getDetectionsAtTimestamp(this.videoId, timestamp, this.fetchThreshold)
      .subscribe({
        next: (detections) => {
          this.detections.set(detections);
          this.renderDetections();
        },
        error: (err) => {
          console.error('Error fetching detections:', err);
          this.clearCanvas();
        }
      });
  }

  private renderDetections(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // No detections to render
    const currentDetections = this.detections();
    if (currentDetections.length === 0) return;

    // Calculate scale factors
    const scaleX = this.videoWidth > 0 ? this.videoWidth / this.videoWidth : 1;
    const scaleY = this.videoHeight > 0 ? this.videoHeight / this.videoHeight : 1;

    // Render each detection
    for (const detection of currentDetections) {
      this.renderBoundingBox(ctx, detection, scaleX, scaleY);
      this.renderLabel(ctx, detection, scaleX, scaleY);
    }
  }

  private renderBoundingBox(
    ctx: CanvasRenderingContext2D,
    detection: VideoDetection,
    scaleX: number,
    scaleY: number
  ): void {
    // Scale coordinates
    const x1 = detection.bbox_x1 * scaleX;
    const y1 = detection.bbox_y1 * scaleY;
    const x2 = detection.bbox_x2 * scaleX;
    const y2 = detection.bbox_y2 * scaleY;

    // Color selection based on confidence
    const color = detection.recognition_confidence >= 0.5 ? '#22c55e' : '#ef4444';

    // Draw bounding box
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
  }

  private renderLabel(
    ctx: CanvasRenderingContext2D,
    detection: VideoDetection,
    scaleX: number,
    scaleY: number
  ): void {
    // Scale coordinates
    const x1 = detection.bbox_x1 * scaleX;
    const y1 = detection.bbox_y1 * scaleY;

    // Determine label content based on confidence
    const name = detection.recognition_confidence >= 0.5 
      ? detection.person_name 
      : 'Unknown';
    
    // Format confidence percentage
    const confidencePct = (detection.recognition_confidence * 100).toFixed(0);
    const label = `${name} ${confidencePct}%`;

    // Color selection
    const color = detection.recognition_confidence >= 0.5 ? '#22c55e' : '#ef4444';

    // Set font
    ctx.font = 'bold 13px sans-serif';
    const textWidth = ctx.measureText(label).width;

    // Draw background rectangle
    ctx.fillStyle = color;
    ctx.fillRect(x1, y1 - 22, textWidth + 10, 22);

    // Draw text
    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, x1 + 5, y1 - 6);
  }

  private clearCanvas(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // Public API for manual updates
  public refresh(): void {
    this.renderDetections();
  }

  public clear(): void {
    this.clearCanvas();
  }
}

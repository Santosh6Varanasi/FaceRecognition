import {
  Component, OnInit, OnDestroy, ViewChild, ElementRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HttpEventType, HttpResponse } from '@angular/common/http';
import {
  VideoService, VideoRecord, FrameDetection, Detection, UploadResponse, JobStatus
} from '../../services/video.service';

@Component({
  selector: 'app-video',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  template: `
    <!-- LIST VIEW -->
    <div *ngIf="view === 'list'">
      <div class="page-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h1>Video Processing</h1>
        <button class="btn-primary" (click)="view = 'upload'">Upload New Video</button>
      </div>

      <!-- Polling status banner -->
      <div *ngIf="pollingJobId" style="background:#1e3a5f;border:1px solid #3b82f6;border-radius:6px;padding:12px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="color:#93c5fd;">Processing job {{ pollingJobId }}...</span>
          <span style="color:#60a5fa;">{{ pollingStatus }}</span>
          <span style="color:#93c5fd;">{{ pollingProgress }}%</span>
        </div>
        <div style="background:#374151;border-radius:4px;height:6px;margin-top:8px;">
          <div style="background:#3b82f6;height:6px;border-radius:4px;transition:width 0.3s;"
               [style.width.%]="pollingProgress"></div>
        </div>
      </div>

      <!-- Success / error toasts -->
      <div *ngIf="successMessage" style="background:#14532d;border:1px solid #22c55e;border-radius:6px;padding:12px;margin-bottom:16px;color:#86efac;">
        {{ successMessage }}
      </div>
      <div *ngIf="listError" style="background:#450a0a;border:1px solid #ef4444;border-radius:6px;padding:12px;margin-bottom:16px;color:#fca5a5;">
        {{ listError }}
      </div>

      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="border-bottom:1px solid #374151;">
            <th style="text-align:left;padding:10px 8px;color:#9ca3af;">Filename</th>
            <th style="text-align:left;padding:10px 8px;color:#9ca3af;">Upload Date</th>
            <th style="text-align:left;padding:10px 8px;color:#9ca3af;">Status</th>
            <th style="text-align:left;padding:10px 8px;color:#9ca3af;">Known Faces</th>
            <th style="text-align:left;padding:10px 8px;color:#9ca3af;">Unknown Faces</th>
            <th style="text-align:left;padding:10px 8px;color:#9ca3af;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let v of videos" style="border-bottom:1px solid #1f2937;">
            <td style="padding:10px 8px;color:#e5e7eb;">{{ v.filename }}</td>
            <td style="padding:10px 8px;color:#9ca3af;">{{ v.uploaded_at | date:'short' }}</td>
            <td style="padding:10px 8px;">
              <span [style.background]="statusBg(v.status)"
                    [style.color]="statusColor(v.status)"
                    style="padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">
                {{ v.status }}
              </span>
            </td>
            <td style="padding:10px 8px;color:#e5e7eb;">{{ v.unique_known }}</td>
            <td style="padding:10px 8px;color:#e5e7eb;">{{ v.unique_unknowns }}</td>
            <td style="padding:10px 8px;display:flex;gap:8px;">
              <button *ngIf="v.status === 'processed'" class="btn-primary"
                      style="padding:4px 12px;font-size:13px;"
                      (click)="loadPlayback(v.id)">View</button>
              <button *ngIf="v.status === 'processed'" class="btn-secondary"
                      style="padding:4px 12px;font-size:13px;"
                      (click)="reprocess(v)">Re-process</button>
            </td>
          </tr>
          <tr *ngIf="videos.length === 0">
            <td colspan="6" style="padding:24px;text-align:center;color:#6b7280;">No videos uploaded yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- UPLOAD VIEW -->
    <div *ngIf="view === 'upload'" style="max-width:520px;">
      <div class="page-header" style="margin-bottom:16px;">
        <h1>Upload Video</h1>
      </div>

      <div style="margin-bottom:16px;">
        <label style="display:block;margin-bottom:8px;color:#9ca3af;">Select video file (MP4, AVI, MOV, MKV — max 500 MB)</label>
        <input type="file" accept=".mp4,.avi,.mov,.mkv"
               (change)="onFileSelected($event)"
               style="color:#e5e7eb;" />
      </div>

      <div *ngIf="uploadError" style="color:#f87171;margin-bottom:12px;">{{ uploadError }}</div>

      <div *ngIf="selectedFile" style="color:#86efac;margin-bottom:12px;">
        Selected: {{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})
      </div>

      <!-- Upload progress bar -->
      <div *ngIf="uploadProgress > 0 && uploadProgress < 100"
           style="margin-bottom:16px;">
        <div style="background:#374151;border-radius:4px;height:8px;">
          <div style="background:#3b82f6;height:8px;border-radius:4px;transition:width 0.2s;"
               [style.width.%]="uploadProgress"></div>
        </div>
        <div style="color:#93c5fd;font-size:13px;margin-top:4px;">{{ uploadProgress }}%</div>
      </div>

      <div style="display:flex;gap:12px;">
        <button class="btn-primary" [disabled]="!selectedFile || uploading" (click)="onUpload()">
          {{ uploading ? 'Uploading...' : 'Upload' }}
        </button>
        <button class="btn-secondary" (click)="view = 'list'">Cancel</button>
      </div>
    </div>

    <!-- PLAYBACK VIEW -->
    <div *ngIf="view === 'playback'">
      <div class="page-header" style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
        <button class="btn-secondary" (click)="backToList()">← Back to list</button>
        <h1 style="margin:0;">Video Playback</h1>
      </div>

      <div *ngIf="!localVideoUrl" style="margin-bottom:16px;">
        <div style="color:#fbbf24;margin-bottom:8px;">
          Re-upload the video file to enable playback.
        </div>
        <input type="file" accept=".mp4,.avi,.mov,.mkv"
               (change)="onLocalFileSelected($event)"
               style="color:#e5e7eb;" />
      </div>

      <div *ngIf="localVideoUrl" style="position:relative;display:inline-block;">
        <video #videoEl
               [src]="localVideoUrl"
               controls
               style="max-width:100%;border-radius:8px;display:block;background:#000;"
               (loadedmetadata)="onVideoMetadata()"
               (timeupdate)="onTimeUpdate()">
        </video>
        <canvas #overlayCanvas
                style="position:absolute;top:0;left:0;pointer-events:none;border-radius:8px;">
        </canvas>
      </div>

      <div *ngIf="playbackError" style="color:#f87171;margin-top:12px;">{{ playbackError }}</div>
    </div>
  `
})
export class VideoComponent implements OnInit, OnDestroy {
  @ViewChild('videoEl') videoElRef?: ElementRef<HTMLVideoElement>;
  @ViewChild('overlayCanvas') overlayCanvasRef?: ElementRef<HTMLCanvasElement>;

  view: 'list' | 'upload' | 'playback' = 'list';

  // List state
  videos: VideoRecord[] = [];
  listError = '';
  successMessage = '';

  // Upload state
  selectedFile: File | null = null;
  uploadError = '';
  uploadProgress = 0;
  uploading = false;

  // Polling state
  pollingJobId: string | null = null;
  pollingStatus = '';
  pollingProgress = 0;
  private pollingInterval: ReturnType<typeof setInterval> | null = null;

  // Playback state
  currentVideoId: number | null = null;
  cachedDetections: FrameDetection[] = [];
  localVideoUrl: string | null = null;
  playbackError = '';

  // Store uploaded file for playback
  private storedFile: File | null = null;

  constructor(private videoService: VideoService) {}

  ngOnInit(): void {
    this.loadVideos();
  }

  ngOnDestroy(): void {
    this.clearPolling();
    if (this.localVideoUrl) {
      URL.revokeObjectURL(this.localVideoUrl);
    }
  }

  loadVideos(): void {
    this.videoService.listVideos().subscribe({
      next: res => { this.videos = res.videos; },
      error: () => { this.listError = 'Failed to load videos.'; }
    });
  }

  statusBg(status: string): string {
    if (status === 'processed') return '#14532d';
    if (status === 'failed') return '#450a0a';
    return '#1e3a5f';
  }

  statusColor(status: string): string {
    if (status === 'processed') return '#86efac';
    if (status === 'failed') return '#fca5a5';
    return '#93c5fd';
  }

  formatSize(bytes: number): string {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / 1024).toFixed(1) + ' KB';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const allowed = ['mp4', 'avi', 'mov', 'mkv'];
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!allowed.includes(ext)) {
      this.uploadError = 'Unsupported file format. Please upload MP4, AVI, MOV, or MKV.';
      this.selectedFile = null;
      return;
    }
    if (file.size > 524288000) {
      this.uploadError = 'File size exceeds the 500 MB limit.';
      this.selectedFile = null;
      return;
    }
    this.uploadError = '';
    this.selectedFile = file;
  }

  onUpload(): void {
    if (!this.selectedFile) return;
    this.uploading = true;
    this.uploadProgress = 0;
    this.storedFile = this.selectedFile;

    this.videoService.uploadVideo(this.selectedFile).subscribe({
      next: event => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadProgress = Math.round((event.loaded / event.total) * 100);
        } else if (event instanceof HttpResponse) {
          const body = event.body as UploadResponse;
          this.uploading = false;
          this.selectedFile = null;
          this.uploadProgress = 0;
          this.view = 'list';
          this.startPolling(body.job_id);
        }
      },
      error: () => {
        this.uploading = false;
        this.uploadError = 'Upload failed. Please try again.';
      }
    });
  }

  startPolling(jobId: string): void {
    this.pollingJobId = jobId;
    this.pollingProgress = 0;
    this.pollingStatus = 'queued';
    this.clearPolling();

    this.pollingInterval = setInterval(() => {
      this.videoService.getJobStatus(jobId).subscribe({
        next: (status: JobStatus) => {
          this.pollingStatus = status.status;
          this.pollingProgress = status.progress_pct;

          if (status.status === 'completed') {
            this.clearPolling();
            this.pollingJobId = null;
            this.successMessage = 'Video processed successfully!';
            setTimeout(() => { this.successMessage = ''; }, 5000);
            this.loadVideos();
          } else if (status.status === 'failed') {
            this.clearPolling();
            this.pollingJobId = null;
            this.listError = `Processing failed: ${status.message}`;
          }
        },
        error: () => { /* ignore transient errors */ }
      });
    }, 3000);
  }

  private clearPolling(): void {
    if (this.pollingInterval !== null) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  loadPlayback(videoId: number): void {
    this.playbackError = '';
    this.videoService.getDetections(videoId).subscribe({
      next: detections => {
        this.cachedDetections = detections;
        this.currentVideoId = videoId;
        if (this.storedFile) {
          if (this.localVideoUrl) URL.revokeObjectURL(this.localVideoUrl);
          this.localVideoUrl = URL.createObjectURL(this.storedFile);
        } else {
          this.localVideoUrl = null;
        }
        this.view = 'playback';
      },
      error: () => {
        this.playbackError = 'Failed to load detection data.';
      }
    });
  }

  reprocess(video: VideoRecord): void {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.mp4,.avi,.mov,.mkv';
    input.onchange = (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      this.storedFile = file;
      this.selectedFile = file;
      this.view = 'upload';
    };
    input.click();
  }

  onLocalFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    if (this.localVideoUrl) URL.revokeObjectURL(this.localVideoUrl);
    this.localVideoUrl = URL.createObjectURL(file);
  }

  onVideoMetadata(): void {
    const video = this.videoElRef?.nativeElement;
    const canvas = this.overlayCanvasRef?.nativeElement;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.style.width = video.offsetWidth + 'px';
    canvas.style.height = video.offsetHeight + 'px';
  }

  onTimeUpdate(): void {
    const video = this.videoElRef?.nativeElement;
    if (!video || this.cachedDetections.length === 0) return;
    const currentMs = video.currentTime * 1000;
    const frame = this.cachedDetections.reduce((best, f) => {
      return Math.abs(f.frame_timestamp_ms - currentMs) < Math.abs(best.frame_timestamp_ms - currentMs)
        ? f : best;
    });
    if (Math.abs(frame.frame_timestamp_ms - currentMs) < 250) {
      this.drawOverlay(frame.detections);
    } else {
      this.clearCanvas();
    }
  }

  private drawOverlay(detections: Detection[]): void {
    const canvas = this.overlayCanvasRef?.nativeElement;
    const video = this.videoElRef?.nativeElement;
    if (!canvas || !video) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const det of detections) {
      const { x1, y1, x2, y2 } = det.bbox;
      const isKnown = det.confidence >= 0.5;
      const color = isKnown ? '#22c55e' : '#ef4444';
      const label = `${det.name} ${(det.confidence * 100).toFixed(0)}%`;

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      ctx.font = 'bold 13px sans-serif';
      const textWidth = ctx.measureText(label).width;
      ctx.fillStyle = color;
      ctx.fillRect(x1, y1 - 22, textWidth + 10, 22);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x1 + 5, y1 - 6);
    }
  }

  private clearCanvas(): void {
    const canvas = this.overlayCanvasRef?.nativeElement;
    if (!canvas) return;
    canvas.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
  }

  backToList(): void {
    this.clearCanvas();
    if (this.localVideoUrl) {
      URL.revokeObjectURL(this.localVideoUrl);
      this.localVideoUrl = null;
    }
    this.view = 'list';
  }
}

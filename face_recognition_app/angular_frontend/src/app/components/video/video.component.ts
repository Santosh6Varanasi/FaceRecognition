import {
  Component, OnInit, OnDestroy, ViewChild, ElementRef, signal, computed
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpEventType, HttpResponse } from '@angular/common/http';
import {
  VideoService, VideoRecord, FrameDetection, Detection, UploadResponse, JobStatus
} from '../../services/video.service';
import { TimelineComponent } from '../timeline/timeline.component';

@Component({
    selector: 'app-video',
    imports: [CommonModule, FormsModule, TimelineComponent],
    template: `
    <!-- LIST VIEW -->
    @if (view() === 'list') {
      <div>
        <div class="page-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <h1>Video Processing</h1>
          <button class="btn-primary" (click)="view.set('upload')">Upload New Video</button>
        </div>
        <!-- Polling status banner -->
        @if (pollingJobId()) {
          <div style="background:#1e3a5f;border:1px solid #3b82f6;border-radius:6px;padding:12px;margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:12px;">
              <span style="color:#93c5fd;">Processing job {{ pollingJobId() }}...</span>
              <span style="color:#60a5fa;">{{ pollingStatus() }}</span>
              <span style="color:#93c5fd;">{{ pollingProgress() }}%</span>
            </div>
            <div style="background:#374151;border-radius:4px;height:6px;margin-top:8px;">
              <div style="background:#3b82f6;height:6px;border-radius:4px;transition:width 0.3s;"
              [style.width.%]="pollingProgress()"></div>
            </div>
          </div>
        }
        <!-- Success / error toasts -->
        @if (successMessage()) {
          <div style="background:#14532d;border:1px solid #22c55e;border-radius:6px;padding:12px;margin-bottom:16px;color:#86efac;">
            {{ successMessage() }}
          </div>
        }
        @if (listError()) {
          <div style="background:#450a0a;border:1px solid #ef4444;border-radius:6px;padding:12px;margin-bottom:16px;color:#fca5a5;">
            {{ listError() }}
          </div>
        }
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
            @for (v of videos(); track v.id) {
              <tr style="border-bottom:1px solid #1f2937;">
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
                  @if (v.status === 'processed') {
                    <button class="btn-primary"
                      style="padding:4px 12px;font-size:13px;"
                    (click)="loadPlayback(v.id)">View</button>
                  }
                  <button class="btn-danger"
                    style="padding:4px 12px;font-size:13px;background:#7f1d1d;border:1px solid #991b1b;"
                  (click)="deleteVideo(v)">Delete</button>
                </td>
              </tr>
            }
            @if (videos().length === 0) {
              <tr>
                <td colspan="6" style="padding:24px;text-align:center;color:#6b7280;">No videos uploaded yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
    
    <!-- UPLOAD VIEW -->
    @if (view() === 'upload') {
      <div style="max-width:520px;">
        <div class="page-header" style="margin-bottom:16px;">
          <h1>Upload Video</h1>
        </div>
        <div style="margin-bottom:16px;">
          <label style="display:block;margin-bottom:8px;color:#9ca3af;">Select video file (MP4, AVI, MOV, MKV — max 500 MB)</label>
          <input type="file" accept=".mp4,.avi,.mov,.mkv"
            (change)="onFileSelected($event)"
            style="color:#e5e7eb;" />
          </div>
          @if (uploadError()) {
            <div style="color:#f87171;margin-bottom:12px;">{{ uploadError() }}</div>
          }
          @if (selectedFile()) {
            <div style="color:#86efac;margin-bottom:12px;">
              Selected: {{ selectedFile()!.name }} ({{ formatSize(selectedFile()!.size) }})
            </div>
          }
          <!-- Upload progress bar -->
          @if (uploadProgress() > 0 && uploadProgress() < 100) {
            <div
              style="margin-bottom:16px;">
              <div style="background:#374151;border-radius:4px;height:8px;">
                <div style="background:#3b82f6;height:8px;border-radius:4px;transition:width 0.2s;"
                [style.width.%]="uploadProgress()"></div>
              </div>
              <div style="color:#93c5fd;font-size:13px;margin-top:4px;">{{ uploadProgress() }}%</div>
            </div>
          }
          <div style="display:flex;gap:12px;">
            <button class="btn-primary" [disabled]="!selectedFile() || uploading()" (click)="onUpload()">
              {{ uploading() ? 'Uploading...' : 'Upload' }}
            </button>
            <button class="btn-secondary" (click)="view.set('list')">Cancel</button>
          </div>
        </div>
      }
    
      <!-- PLAYBACK VIEW -->
      @if (view() === 'playback') {
        <div>
          <div class="page-header" style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
            <button class="btn-secondary" (click)="backToList()">← Back to list</button>
            <h1 style="margin:0;">Video Playback</h1>
          </div>
          @if (localVideoUrl()) {
            <div style="display:flex;gap:24px;align-items:flex-start;">
              <!-- Timeline on Left -->
              <div style="flex:0 0 300px;min-width:300px;">
                <app-timeline
                  [videoId]="currentVideoId()!"
                  [videoDuration]="videoDuration()"
                  [currentTime]="currentVideoTime()"
                  [detections]="cachedDetections()"
                  (timelineClick)="onTimelineClick($event)">
                </app-timeline>
              </div>
              
              <!-- Video Player with Overlay on Right -->
              <div style="flex:1;max-width:900px;">
                <div style="position:relative;width:100%;">
                  <video #videoEl
                    [src]="localVideoUrl()"
                    controls
                    style="width:100%;max-width:100%;border-radius:8px;display:block;background:#000;"
                    (loadedmetadata)="onVideoMetadata()"
                    (timeupdate)="onTimeUpdate()">
                  </video>
                  <canvas #overlayCanvas
                    style="position:absolute;top:0;left:0;pointer-events:none;border-radius:8px;">
                  </canvas>
                </div>
              </div>
            </div>
          }
          @if (playbackError()) {
            <div style="color:#f87171;margin-top:12px;">{{ playbackError() }}</div>
          }
        </div>
      }
    `
})
export class VideoComponent implements OnInit, OnDestroy {
  @ViewChild('videoEl') videoElRef?: ElementRef<HTMLVideoElement>;
  @ViewChild('overlayCanvas') overlayCanvasRef?: ElementRef<HTMLCanvasElement>;

  // View state signals
  view = signal<'list' | 'upload' | 'playback'>('list');

  // List state signals
  videos = signal<VideoRecord[]>([]);
  listError = signal('');
  successMessage = signal('');

  // Upload state signals
  selectedFile = signal<File | null>(null);
  uploadError = signal('');
  uploadProgress = signal(0);
  uploading = signal(false);

  // Polling state signals
  pollingJobId = signal<string | null>(null);
  pollingStatus = signal('');
  pollingProgress = signal(0);
  private pollingInterval: ReturnType<typeof setInterval> | null = null;

  // Playback state signals
  currentVideoId = signal<number | null>(null);
  cachedDetections = signal<FrameDetection[]>([]);
  localVideoUrl = signal<string | null>(null);
  playbackError = signal('');
  videoDuration = signal(0);
  currentVideoTime = signal(0);

  // Computed signals
  hasVideos = computed(() => this.videos().length > 0);
  isPolling = computed(() => this.pollingJobId() !== null);

  constructor(private videoService: VideoService) {}

  ngOnInit(): void {
    this.loadVideos();
  }

  ngOnDestroy(): void {
    this.clearPolling();
  }

  loadVideos(): void {
    this.videoService.listVideos().subscribe({
      next: res => { 
        console.log('Loaded videos:', res);
        this.videos.set(res.videos);
      },
      error: (err) => { 
        console.error('Failed to load videos:', err);
        this.listError.set('Failed to load videos.');
      }
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
      this.uploadError.set('Unsupported file format. Please upload MP4, AVI, MOV, or MKV.');
      this.selectedFile.set(null);
      return;
    }
    if (file.size > 524288000) {
      this.uploadError.set('File size exceeds the 500 MB limit.');
      this.selectedFile.set(null);
      return;
    }
    this.uploadError.set('');
    this.selectedFile.set(file);
  }

  onUpload(): void {
    const file = this.selectedFile();
    if (!file) return;
    
    this.uploading.set(true);
    this.uploadProgress.set(0);

    this.videoService.uploadVideo(file).subscribe({
      next: event => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadProgress.set(Math.round((event.loaded / event.total) * 100));
        } else if (event instanceof HttpResponse) {
          const body = event.body as UploadResponse;
          this.uploading.set(false);
          this.selectedFile.set(null);
          this.uploadProgress.set(0);
          this.view.set('list');
          this.startPolling(body.job_id);
        }
      },
      error: () => {
        this.uploading.set(false);
        this.uploadError.set('Upload failed. Please try again.');
      }
    });
  }

  startPolling(jobId: string): void {
    console.log('Starting polling for job:', jobId);
    this.pollingJobId.set(jobId);
    this.pollingProgress.set(0);
    this.pollingStatus.set('queued');
    this.clearPolling();

    this.pollingInterval = setInterval(() => {
      this.videoService.getJobStatus(jobId).subscribe({
        next: (status: JobStatus) => {
          console.log('Job status update:', status);
          this.pollingStatus.set(status.status);
          this.pollingProgress.set(status.progress_pct);

          if (status.status === 'completed') {
            console.log('Job completed, clearing polling and reloading videos');
            this.clearPolling();
            this.pollingJobId.set(null);
            this.successMessage.set('Video processed successfully!');
            setTimeout(() => { 
              this.successMessage.set('');
            }, 5000);
            this.loadVideos();
          } else if (status.status === 'failed') {
            console.log('Job failed:', status.message);
            this.clearPolling();
            this.pollingJobId.set(null);
            this.listError.set(`Processing failed: ${status.message}`);
          }
        },
        error: (err) => { 
          console.error('Error polling job status:', err);
          /* ignore transient errors */ 
        }
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
    this.playbackError.set('');
    this.videoService.getDetections(videoId).subscribe({
      next: detections => {
        console.log('Loaded detections:', detections.length, 'frames');
        console.log('Sample detection:', detections[0]);
        this.cachedDetections.set(detections);
        this.currentVideoId.set(videoId);
        
        // Use backend video URL for streaming
        this.localVideoUrl.set(this.videoService.getVideoUrl(videoId));
        this.view.set('playback');
      },
      error: (err) => {
        console.error('Failed to load detections:', err);
        this.playbackError.set('Failed to load detection data.');
      }
    });
  }

  onVideoMetadata(): void {
    const video = this.videoElRef?.nativeElement;
    const canvas = this.overlayCanvasRef?.nativeElement;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.style.width = video.offsetWidth + 'px';
    canvas.style.height = video.offsetHeight + 'px';
    
    // Set video duration for timeline
    this.videoDuration.set(video.duration);
  }

  onTimeUpdate(): void {
    const video = this.videoElRef?.nativeElement;
    const detections = this.cachedDetections();
    
    if (!video || detections.length === 0) {
      if (!video) console.log('No video element');
      if (detections.length === 0) console.log('No cached detections');
      return;
    }
    
    // Update current time for timeline
    this.currentVideoTime.set(video.currentTime);
    
    const currentMs = video.currentTime * 1000;
    const frame = detections.reduce((best, f) => {
      return Math.abs(f.frame_timestamp_ms - currentMs) < Math.abs(best.frame_timestamp_ms - currentMs)
        ? f : best;
    });
    
    const timeDiff = Math.abs(frame.frame_timestamp_ms - currentMs);
    if (timeDiff < 250) {
      console.log(`Drawing ${frame.detections.length} detections at ${currentMs}ms (frame: ${frame.frame_timestamp_ms}ms, diff: ${timeDiff}ms)`);
      this.drawOverlay(frame.detections);
    } else {
      this.clearCanvas();
    }
  }

  private drawOverlay(detections: Detection[]): void {
    const canvas = this.overlayCanvasRef?.nativeElement;
    const video = this.videoElRef?.nativeElement;
    if (!canvas || !video) {
      console.log('Canvas or video missing:', { canvas: !!canvas, video: !!video });
      return;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      console.log('No canvas context');
      return;
    }

    console.log('Drawing overlay with', detections.length, 'detections');
    console.log('Canvas size:', canvas.width, 'x', canvas.height);
    console.log('Video size:', video.videoWidth, 'x', video.videoHeight);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const det of detections) {
      const { x1, y1, x2, y2 } = det.bbox;
      const isKnown = det.confidence >= 0.5;
      const color = isKnown ? '#22c55e' : '#ef4444';
      const label = `${det.name} ${(det.confidence * 100).toFixed(0)}%`;

      console.log(`Drawing box: ${label} at (${x1},${y1}) to (${x2},${y2})`);

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
    this.localVideoUrl.set(null);
    this.videoDuration.set(0);
    this.currentVideoTime.set(0);
    this.view.set('list');
  }

  onTimelineClick(timestamp: number): void {
    const video = this.videoElRef?.nativeElement;
    if (video) {
      video.currentTime = timestamp;
    }
  }

  deleteVideo(video: VideoRecord): void {
    if (!confirm(`Are you sure you want to delete "${video.filename}"? This action cannot be undone.`)) {
      return;
    }

    this.videoService.deleteVideo(video.id).subscribe({
      next: (response) => {
        this.successMessage.set(`Video "${response.filename}" deleted successfully`);
        setTimeout(() => { 
          this.successMessage.set('');
        }, 5000);
        this.loadVideos();
      },
      error: (err) => {
        this.listError.set(`Failed to delete video: ${err.error?.error || err.message || 'Unknown error'}`);
        setTimeout(() => { 
          this.listError.set('');
        }, 5000);
      }
    });
  }
}

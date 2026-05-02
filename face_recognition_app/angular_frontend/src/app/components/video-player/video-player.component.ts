import {
  Component,
  Input,
  Output,
  EventEmitter,
  ViewChild,
  ElementRef,
  OnInit,
  signal,
  computed
} from '@angular/core';

import { VideoService, VideoRecord } from '../../services/video.service';

export interface VideoPlayerState {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  isSeeking: boolean;
  videoWidth: number;
  videoHeight: number;
  displayWidth: number;
  displayHeight: number;
}

@Component({
    selector: 'app-video-player',
    imports: [],
    template: `
    @if (videoMetadata) {
      <div class="video-player-container">
        <!-- Video metadata header -->
        <div class="video-header" style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <h3 style="margin:0;color:#e5e7eb;">{{ videoMetadata.filename }}</h3>
            <div style="color:#9ca3af;font-size:13px;margin-top:4px;">
              {{ formatDuration(videoMetadata.duration || 0) }} •
              {{ videoMetadata.width }}x{{ videoMetadata.height }} •
              {{ videoMetadata.fps?.toFixed(1) }} FPS
              @if (videoMetadata.reprocessed_at) {
                <span
                  style="background:#1e3a5f;color:#93c5fd;padding:2px 8px;border-radius:4px;margin-left:8px;font-size:11px;">
                  Reprocessed
                </span>
              }
            </div>
          </div>
        </div>
        <!-- Video element with controls -->
        <div class="video-wrapper" style="position:relative;display:inline-block;max-width:100%;">
          <video #videoElement
            [src]="videoUrl"
            controls
            style="max-width:100%;border-radius:8px;display:block;background:#000;"
            (loadedmetadata)="onLoadedMetadata()"
            (timeupdate)="onTimeUpdate()"
            (seeking)="onSeeking()"
            (seeked)="onSeeked()"
            (play)="onPlay()"
            (pause)="onPause()">
          </video>
          <!-- Slot for overlay components -->
          <ng-content></ng-content>
        </div>
        <!-- Error message -->
        @if (errorMessage) {
          <div style="color:#f87171;margin-top:12px;">
            {{ errorMessage }}
          </div>
        }
      </div>
    }
    
    <!-- Loading state -->
    @if (!videoMetadata && !errorMessage) {
      <div style="color:#9ca3af;padding:24px;">
        Loading video...
      </div>
    }
    `,
    styles: [`
    .video-player-container {
      width: 100%;
    }
    .video-wrapper {
      position: relative;
      display: inline-block;
    }
  `]
})
export class VideoPlayerComponent implements OnInit {
  @Input() videoId!: number;
  @Input() videoUrl!: string;
  
  @Output() timeUpdate = new EventEmitter<number>();
  @Output() seeking = new EventEmitter<void>();
  @Output() seeked = new EventEmitter<void>();
  @Output() playStateChange = new EventEmitter<boolean>();
  @Output() metadataLoaded = new EventEmitter<VideoPlayerState>();

  @ViewChild('videoElement') videoElementRef?: ElementRef<HTMLVideoElement>;

  videoMetadata: VideoRecord | null = null;
  errorMessage = '';

  // Signal-based state management
  private stateSignal = signal<VideoPlayerState>({
    currentTime: 0,
    duration: 0,
    isPlaying: false,
    isSeeking: false,
    videoWidth: 0,
    videoHeight: 0,
    displayWidth: 0,
    displayHeight: 0
  });

  // Public readonly signal
  readonly state = this.stateSignal.asReadonly();
  
  // Computed signals for derived state
  readonly isPlaying = computed(() => this.state().isPlaying);
  readonly isSeeking = computed(() => this.state().isSeeking);
  readonly currentTime = computed(() => this.state().currentTime);
  readonly duration = computed(() => this.state().duration);

  constructor(private videoService: VideoService) {}

  ngOnInit(): void {
    if (this.videoId) {
      this.loadVideoMetadata();
    }
  }

  private loadVideoMetadata(): void {
    this.videoService.getVideoMetadata(this.videoId).subscribe({
      next: (metadata) => {
        this.videoMetadata = metadata;
      },
      error: (err) => {
        this.errorMessage = 'Failed to load video metadata';
        console.error('Error loading video metadata:', err);
      }
    });
  }

  onLoadedMetadata(): void {
    const video = this.videoElementRef?.nativeElement;
    if (!video) return;

    const state: VideoPlayerState = {
      currentTime: video.currentTime,
      duration: video.duration,
      isPlaying: !video.paused,
      isSeeking: false,
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight,
      displayWidth: video.offsetWidth,
      displayHeight: video.offsetHeight
    };

    this.stateSignal.set(state);
    this.metadataLoaded.emit(state);
  }

  onTimeUpdate(): void {
    const video = this.videoElementRef?.nativeElement;
    if (!video) return;

    this.stateSignal.update(currentState => ({
      ...currentState,
      currentTime: video.currentTime
    }));

    this.timeUpdate.emit(video.currentTime);
  }

  onSeeking(): void {
    this.stateSignal.update(currentState => ({
      ...currentState,
      isSeeking: true
    }));
    this.seeking.emit();
  }

  onSeeked(): void {
    this.stateSignal.update(currentState => ({
      ...currentState,
      isSeeking: false
    }));
    this.seeked.emit();
  }

  onPlay(): void {
    this.stateSignal.update(currentState => ({
      ...currentState,
      isPlaying: true
    }));
    this.playStateChange.emit(true);
  }

  onPause(): void {
    this.stateSignal.update(currentState => ({
      ...currentState,
      isPlaying: false
    }));
    this.playStateChange.emit(false);
  }

  // Public API methods
  play(): void {
    this.videoElementRef?.nativeElement.play();
  }

  pause(): void {
    this.videoElementRef?.nativeElement.pause();
  }

  seekTo(time: number): void {
    const video = this.videoElementRef?.nativeElement;
    if (video) {
      video.currentTime = time;
    }
  }

  getCurrentState(): VideoPlayerState {
    return this.stateSignal();
  }

  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
}

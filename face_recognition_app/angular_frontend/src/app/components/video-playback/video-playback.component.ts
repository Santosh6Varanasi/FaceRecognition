import { Component, ViewChild, inject, signal, effect, ChangeDetectionStrategy } from '@angular/core';

import { ActivatedRoute, Router } from '@angular/router';
import { VideoPlayerComponent } from '../video-player/video-player.component';
import { DetectionOverlayComponent } from '../detection-overlay/detection-overlay.component';
import { TimelineComponent } from '../timeline/timeline.component';
import { VideoService } from '../../services/video.service';

@Component({
    selector: 'app-video-playback',
    standalone: true,
    imports: [VideoPlayerComponent, DetectionOverlayComponent, TimelineComponent],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <div class="container mx-auto px-4 py-6 sm:px-6 lg:px-8 max-w-7xl">
      <div class="flex items-center gap-4 mb-6">
        <button class="btn-secondary" (click)="goBack()">← Back</button>
        <h1 class="page-title m-0">Video Playback</h1>
      </div>
    
      @if (videoId() && videoUrl()) {
        <div class="space-y-4">
          <!-- Video Player with Detection Overlay -->
          <app-video-player
            [videoId]="videoId()!"
            [videoUrl]="videoUrl()"
            (timeUpdate)="onTimeUpdate($event)"
            (metadataLoaded)="onMetadataLoaded($event)">
            <!-- Detection Overlay as child of Video Player -->
            <app-detection-overlay
              #detectionOverlay
              [videoId]="videoId()!"
              [currentTime]="currentTime()"
              [videoWidth]="videoWidth()"
              [videoHeight]="videoHeight()"
              [displayWidth]="displayWidth()"
              [displayHeight]="displayHeight()">
            </app-detection-overlay>
          </app-video-player>
          <!-- Timeline Component -->
          <app-timeline
            #timeline
            [videoId]="videoId()!"
            [videoDuration]="videoDuration()"
            [currentTime]="currentTime()"
            (timelineClick)="onTimelineClick($event)">
          </app-timeline>
        </div>
      }
    
      @if (!videoId()) {
        <div class="text-slate-500 dark:text-slate-400 p-6 text-center">
          No video selected.
        </div>
      }
    </div>
    `,
    styles: []
})
export class VideoPlaybackComponent {
  @ViewChild('detectionOverlay') detectionOverlay?: DetectionOverlayComponent;
  @ViewChild(VideoPlayerComponent) videoPlayer?: VideoPlayerComponent;
  @ViewChild('timeline') timeline?: TimelineComponent;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private videoService = inject(VideoService);
  
  // Signal-based state
  videoId = signal<number | null>(null);
  videoUrl = signal<string>('');
  currentTime = signal<number>(0);
  videoDuration = signal<number>(0);
  videoWidth = signal<number>(0);
  videoHeight = signal<number>(0);
  displayWidth = signal<number>(0);
  displayHeight = signal<number>(0);

  constructor() {
    // Subscribe to route params using effect
    effect(() => {
      this.route.params.subscribe(params => {
        const id = params['id'];
        if (id) {
          const videoIdNum = parseInt(id, 10);
          this.videoId.set(videoIdNum);
          this.videoUrl.set(this.videoService.getVideoUrl(videoIdNum));
        }
      });
    });
  }

  onTimeUpdate(time: number): void {
    this.currentTime.set(time);
    
    // Update detection overlay
    if (this.detectionOverlay) {
      this.detectionOverlay.onTimeUpdate(time);
    }
  }

  onMetadataLoaded(state: any): void {
    this.videoDuration.set(state.duration);
    this.videoWidth.set(state.videoWidth);
    this.videoHeight.set(state.videoHeight);
    this.displayWidth.set(state.displayWidth);
    this.displayHeight.set(state.displayHeight);

    // Update detection overlay canvas size
    if (this.detectionOverlay) {
      this.detectionOverlay.videoWidth = this.videoWidth();
      this.detectionOverlay.videoHeight = this.videoHeight();
      this.detectionOverlay.displayWidth = this.displayWidth();
      this.detectionOverlay.displayHeight = this.displayHeight();
      this.detectionOverlay.updateCanvasSize();
    }
  }

  onTimelineClick(timestamp: number): void {
    // Seek video player to clicked timestamp
    if (this.videoPlayer) {
      this.videoPlayer.seekTo(timestamp);
    }
  }

  goBack(): void {
    this.router.navigate(['/video']);
  }
}

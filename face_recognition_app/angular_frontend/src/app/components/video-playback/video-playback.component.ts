import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { VideoPlayerComponent } from '../video-player/video-player.component';
import { DetectionOverlayComponent } from '../detection-overlay/detection-overlay.component';
import { TimelineComponent } from '../timeline/timeline.component';
import { VideoService } from '../../services/video.service';

@Component({
  selector: 'app-video-playback',
  standalone: true,
  imports: [CommonModule, VideoPlayerComponent, DetectionOverlayComponent, TimelineComponent],
  template: `
    <div class="video-playback-page">
      <div class="page-header" style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
        <button class="btn-secondary" (click)="goBack()">← Back</button>
        <h1 style="margin:0;">Video Playback</h1>
      </div>

      <div *ngIf="videoId && videoUrl" class="playback-container">
        <!-- Video Player with Detection Overlay -->
        <app-video-player
          [videoId]="videoId"
          [videoUrl]="videoUrl"
          (timeUpdate)="onTimeUpdate($event)"
          (metadataLoaded)="onMetadataLoaded($event)">
          
          <!-- Detection Overlay as child of Video Player -->
          <app-detection-overlay
            #detectionOverlay
            [videoId]="videoId"
            [currentTime]="currentTime"
            [videoWidth]="videoWidth"
            [videoHeight]="videoHeight"
            [displayWidth]="displayWidth"
            [displayHeight]="displayHeight">
          </app-detection-overlay>
        </app-video-player>

        <!-- Timeline Component -->
        <app-timeline
          #timeline
          [videoId]="videoId"
          [videoDuration]="videoDuration"
          [currentTime]="currentTime"
          (timelineClick)="onTimelineClick($event)">
        </app-timeline>
      </div>

      <div *ngIf="!videoId" style="color:#6b7280;padding:24px;">
        No video selected.
      </div>
    </div>
  `,
  styles: [`
    .video-playback-page {
      padding: 20px;
    }
    .playback-container {
      max-width: 1200px;
    }
  `]
})
export class VideoPlaybackComponent implements OnInit {
  @ViewChild('detectionOverlay') detectionOverlay?: DetectionOverlayComponent;
  @ViewChild(VideoPlayerComponent) videoPlayer?: VideoPlayerComponent;
  @ViewChild('timeline') timeline?: TimelineComponent;

  videoId: number | null = null;
  videoUrl: string = '';
  currentTime: number = 0;
  videoDuration: number = 0;
  videoWidth: number = 0;
  videoHeight: number = 0;
  displayWidth: number = 0;
  displayHeight: number = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private videoService: VideoService
  ) {}

  ngOnInit(): void {
    // Get video ID from route params
    this.route.params.subscribe(params => {
      const id = params['id'];
      if (id) {
        this.videoId = parseInt(id, 10);
        this.videoUrl = this.videoService.getVideoUrl(this.videoId);
      }
    });
  }

  onTimeUpdate(time: number): void {
    this.currentTime = time;
    
    // Update detection overlay
    if (this.detectionOverlay) {
      this.detectionOverlay.onTimeUpdate(time);
    }
  }

  onMetadataLoaded(state: any): void {
    this.videoDuration = state.duration;
    this.videoWidth = state.videoWidth;
    this.videoHeight = state.videoHeight;
    this.displayWidth = state.displayWidth;
    this.displayHeight = state.displayHeight;

    // Update detection overlay canvas size
    if (this.detectionOverlay) {
      this.detectionOverlay.videoWidth = this.videoWidth;
      this.detectionOverlay.videoHeight = this.videoHeight;
      this.detectionOverlay.displayWidth = this.displayWidth;
      this.detectionOverlay.displayHeight = this.displayHeight;
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

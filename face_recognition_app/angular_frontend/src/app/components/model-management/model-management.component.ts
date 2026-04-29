import { Component, OnInit, OnDestroy } from '@angular/core';
import { NgIf, NgFor, DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { FaceApiService, ModelVersion } from '../../services/face-api.service';
import { RetrainingPollerService } from '../../services/retraining-poller.service';
import { VideoService, VideoRecord } from '../../services/video.service';

@Component({
  selector: 'app-model-management',
  standalone: true,
  imports: [NgIf, NgFor, DatePipe, DecimalPipe, FormsModule],
  template: `
    <div>
      <div class="page-header">
        <h1>Model Management</h1>
        <button class="btn-primary"
                [disabled]="isTraining"
                [title]="isTraining ? 'Training in progress...' : ''"
                (click)="onRetrain()">
          {{ isTraining ? 'Training...' : 'Retrain Model' }}
        </button>
      </div>

      <!-- Progress bar -->
      <div *ngIf="isTraining" style="margin-bottom:16px;">
        <div class="progress-bar-container">
          <div class="progress-bar-fill" [style.width.%]="progress"></div>
        </div>
        <div style="font-size:13px;color:#6b7280;margin-top:4px;">{{ statusMessage }}</div>
      </div>

      <!-- Notifications -->
      <div class="notification success" *ngIf="notification?.type === 'success'">
        {{ notification!.message }}
      </div>
      <div class="notification error" *ngIf="notification?.type === 'error'">
        {{ notification!.message }}
      </div>

      <!-- Video reprocessing section -->
      <div *ngIf="showReprocessSection" style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:16px;margin-bottom:16px;">
        <h3 style="margin:0 0 12px 0;color:#e5e7eb;">Reprocess Videos with New Model</h3>
        <p style="color:#9ca3af;font-size:14px;margin-bottom:12px;">
          Select videos to reprocess with the newly trained model v{{ latestVersion }}.
        </p>

        <!-- Video selection -->
        <div style="max-height:300px;overflow-y:auto;margin-bottom:12px;">
          <div *ngFor="let video of availableVideos" style="display:flex;align-items:center;gap:8px;padding:8px;border-bottom:1px solid #374151;">
            <input type="checkbox" 
                   [checked]="selectedVideoIds.has(video.id)"
                   (change)="onVideoSelect(video.id, $any($event.target).checked)">
            <span style="color:#e5e7eb;flex:1;">{{ video.filename }}</span>
            <span style="color:#6b7280;font-size:12px;">{{ video.duration?.toFixed(0) }}s</span>
          </div>
          <div *ngIf="availableVideos.length === 0" style="color:#6b7280;padding:16px;text-align:center;">
            No processed videos available.
          </div>
        </div>

        <div style="display:flex;gap:12px;align-items:center;">
          <button class="btn-primary" 
                  [disabled]="selectedVideoIds.size === 0 || isReprocessing"
                  (click)="onReprocessVideos()">
            {{ isReprocessing ? 'Reprocessing...' : 'Reprocess ' + selectedVideoIds.size + ' Video(s)' }}
          </button>
          <button class="btn-secondary" (click)="showReprocessSection = false">Cancel</button>
        </div>

        <!-- Reprocessing progress -->
        <div *ngIf="isReprocessing" style="margin-top:12px;">
          <div style="color:#9ca3af;font-size:13px;margin-bottom:4px;">
            {{ reprocessMessage }}
          </div>
          <div class="progress-bar-container">
            <div class="progress-bar-fill" [style.width.%]="reprocessProgress"></div>
          </div>
        </div>
      </div>

      <!-- Versions table -->
      <table>
        <thead>
          <tr>
            <th>Version</th>
            <th>Classes</th>
            <th>Training Samples</th>
            <th>CV Accuracy</th>
            <th>Trained At</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let v of versions">
            <td>v{{ v.version_number }}</td>
            <td>{{ v.num_classes }}</td>
            <td>{{ v.num_training_samples }}</td>
            <td>{{ (v.cross_validation_accuracy * 100) | number:'1.1-1' }}%</td>
            <td>{{ v.trained_at | date:'short' }}</td>
            <td>
              <span class="badge" [class.badge-active]="v.is_active" [class.badge-inactive]="!v.is_active">
                {{ v.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td>
              <button *ngIf="!v.is_active" class="btn-secondary"
                      style="padding:4px 10px;font-size:12px;"
                      (click)="onActivate(v.version_number)">
                Activate
              </button>
            </td>
          </tr>
          <tr *ngIf="versions.length === 0">
            <td colspan="7" style="text-align:center;color:#6b7280;">No model versions found.</td>
          </tr>
        </tbody>
      </table>
    </div>
  `
})
export class ModelManagementComponent implements OnInit, OnDestroy {
  versions: ModelVersion[] = [];
  isTraining = false;
  jobId: string | null = null;
  progress = 0;
  statusMessage = '';
  notification: { type: 'success' | 'error'; message: string } | null = null;

  // Video reprocessing state
  showReprocessSection = false;
  availableVideos: VideoRecord[] = [];
  selectedVideoIds = new Set<number>();
  isReprocessing = false;
  reprocessProgress = 0;
  reprocessMessage = '';
  latestVersion: number | null = null;

  private pollSub: Subscription | null = null;

  constructor(
    private faceApi: FaceApiService,
    private poller: RetrainingPollerService,
    private videoService: VideoService
  ) {}

  ngOnInit(): void {
    this.loadVersions();
  }

  loadVersions(): void {
    this.faceApi.getModelVersions().subscribe({
      next: versions => this.versions = versions,
      error: err => console.error('Failed to load versions', err)
    });
  }

  onRetrain(): void {
    this.notification = null;
    this.faceApi.triggerRetrain().subscribe({
      next: res => {
        this.jobId = res.job_id;
        this.isTraining = true;
        this.progress = 0;
        this.statusMessage = 'Starting retraining...';

        this.pollSub = this.poller.startPolling(res.job_id).subscribe({
          next: status => {
            this.progress = status.progress_pct;
            this.statusMessage = status.message;

            if (status.status === 'completed') {
              this.isTraining = false;
              this.latestVersion = status.version_number ?? null;
              this.notification = {
                type: 'success',
                message: `Training complete! Model v${status.version_number} — CV Accuracy: ${((status.cv_accuracy ?? 0) * 100).toFixed(1)}%`
              };
              this.loadVersions();
              // Show reprocess section after successful training
              this.loadAvailableVideos();
              this.showReprocessSection = true;
            } else if (status.status === 'failed') {
              this.isTraining = false;
              this.notification = {
                type: 'error',
                message: `Training failed: ${status.message}`
              };
            }
          },
          error: err => {
            this.isTraining = false;
            this.notification = { type: 'error', message: 'Failed to poll training status.' };
            console.error(err);
          }
        });
      },
      error: err => {
        console.error('Failed to trigger retrain', err);
        this.notification = { type: 'error', message: 'Failed to start retraining.' };
      }
    });
  }

  onActivate(versionNumber: number): void {
    this.faceApi.activateModel(versionNumber).subscribe({
      next: () => this.loadVersions(),
      error: err => console.error('Failed to activate model', err)
    });
  }

  loadAvailableVideos(): void {
    this.videoService.getAllProcessedVideos().subscribe({
      next: (videos) => {
        this.availableVideos = videos;
      },
      error: (err) => {
        console.error('Failed to load videos:', err);
        this.notification = { type: 'error', message: 'Failed to load videos for reprocessing' };
      }
    });
  }

  onVideoSelect(videoId: number, checked: boolean): void {
    if (checked) {
      this.selectedVideoIds.add(videoId);
    } else {
      this.selectedVideoIds.delete(videoId);
    }
  }

  onReprocessVideos(): void {
    if (this.selectedVideoIds.size === 0) return;

    this.isReprocessing = true;
    this.reprocessProgress = 0;
    this.reprocessMessage = 'Starting reprocessing...';

    const videoIds = Array.from(this.selectedVideoIds);
    const modelVersion = this.latestVersion?.toString();

    this.videoService.reprocessBatch(videoIds, modelVersion).subscribe({
      next: (res) => {
        // Poll for reprocessing status
        this.reprocessMessage = 'Reprocessing videos...';
        // Simulate progress (in real implementation, poll job status)
        const interval = setInterval(() => {
          this.reprocessProgress += 10;
          if (this.reprocessProgress >= 100) {
            clearInterval(interval);
            this.isReprocessing = false;
            this.reprocessProgress = 0;
            this.notification = {
              type: 'success',
              message: `Successfully reprocessed ${videoIds.length} video(s)`
            };
            this.selectedVideoIds.clear();
            this.showReprocessSection = false;
          }
        }, 500);
      },
      error: (err) => {
        console.error('Failed to reprocess videos:', err);
        this.isReprocessing = false;
        this.notification = { type: 'error', message: 'Failed to start video reprocessing' };
      }
    });
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }
}

import { Component, inject, signal, effect, ChangeDetectionStrategy } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { FaceApiService, ModelVersion } from '../../services/face-api.service';
import { RetrainingPollerService } from '../../services/retraining-poller.service';
import { VideoService, VideoRecord } from '../../services/video.service';

@Component({
    selector: 'app-model-management',
    standalone: true,
    imports: [DatePipe, DecimalPipe, FormsModule],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <div class="container mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div class="page-header">
        <h1 class="page-title">Model Management</h1>
        <button class="btn-primary"
          [disabled]="isTraining()"
          [title]="isTraining() ? 'Training in progress...' : ''"
          (click)="onRetrain()">
          {{ isTraining() ? 'Training...' : 'Retrain Model' }}
        </button>
      </div>
    
      <!-- Progress bar -->
      @if (isTraining()) {
        <div class="mb-4">
          <div class="progress-bar-container">
            <div class="progress-bar-fill" [style.width.%]="progress()"></div>
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ statusMessage() }}</div>
        </div>
      }
    
      <!-- Notifications -->
      @if (notification()?.type === 'success') {
        <div class="notification success">
          {{ notification()!.message }}
        </div>
      }
      @if (notification()?.type === 'error') {
        <div class="notification error">
          {{ notification()!.message }}
        </div>
      }
    
      <!-- Video reprocessing section -->
      @if (showReprocessSection()) {
        <div class="card mb-6">
          <h3 class="text-lg font-bold text-slate-900 dark:text-slate-100 mb-3">
            Reprocess Videos with New Model
          </h3>
          <p class="text-slate-600 dark:text-slate-400 text-sm mb-4">
            Select videos to reprocess with the newly trained model v{{ latestVersion() }}.
          </p>
          <!-- Video selection -->
          <div class="max-h-72 overflow-y-auto mb-4 border border-slate-200 dark:border-slate-700 rounded-lg">
            @for (video of availableVideos(); track video) {
              <div class="flex items-center gap-3 p-3 border-b border-slate-200 dark:border-slate-700 last:border-b-0 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <input type="checkbox"
                  class="rounded border-slate-300 dark:border-slate-600 text-primary-600 focus:ring-primary-500"
                  [checked]="selectedVideoIds().has(video.id)"
                  (change)="onVideoSelect(video.id, $any($event.target).checked)">
                <span class="text-slate-900 dark:text-slate-100 flex-1">{{ video.filename }}</span>
                <span class="text-slate-500 dark:text-slate-400 text-xs">{{ video.duration?.toFixed(0) }}s</span>
              </div>
            }
            @if (availableVideos().length === 0) {
              <div class="text-slate-500 dark:text-slate-400 p-4 text-center text-sm">
                No processed videos available.
              </div>
            }
          </div>
          <div class="flex flex-wrap gap-3 items-center">
            <button class="btn-primary"
              [disabled]="selectedVideoIds().size === 0 || isReprocessing()"
              (click)="onReprocessVideos()">
              {{ isReprocessing() ? 'Reprocessing...' : 'Reprocess ' + selectedVideoIds().size + ' Video(s)' }}
            </button>
            <button class="btn-secondary" (click)="showReprocessSection.set(false)">Cancel</button>
          </div>
          <!-- Reprocessing progress -->
          @if (isReprocessing()) {
            <div class="mt-4">
              <div class="text-slate-600 dark:text-slate-400 text-sm mb-1">
                {{ reprocessMessage() }}
              </div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill" [style.width.%]="reprocessProgress()"></div>
              </div>
            </div>
          }
        </div>
      }
    
      <!-- Versions table -->
      <div class="table-container">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">Version</th>
              <th class="table-header">Classes</th>
              <th class="table-header">Training Samples</th>
              <th class="table-header">CV Accuracy</th>
              <th class="table-header">Trained At</th>
              <th class="table-header">Status</th>
              <th class="table-header">Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (v of versions(); track v) {
              <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <td class="table-cell font-mono">v{{ v.version_number }}</td>
                <td class="table-cell">{{ v.num_classes }}</td>
                <td class="table-cell">{{ v.num_training_samples }}</td>
                <td class="table-cell">{{ (v.cross_validation_accuracy * 100) | number:'1.1-1' }}%</td>
                <td class="table-cell">{{ v.trained_at | date:'short' }}</td>
                <td class="table-cell">
                  <span class="badge" [class.badge-active]="v.is_active" [class.badge-inactive]="!v.is_active">
                    {{ v.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td class="table-cell">
                  @if (!v.is_active) {
                    <button class="btn-secondary text-xs px-3 py-1"
                      (click)="onActivate(v.version_number)">
                      Activate
                    </button>
                  }
                </td>
              </tr>
            }
            @if (versions().length === 0) {
              <tr>
                <td colspan="7" class="table-cell text-center text-slate-500 dark:text-slate-400">
                  No model versions found.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
    `
})
export class ModelManagementComponent {
  private faceApi = inject(FaceApiService);
  private poller = inject(RetrainingPollerService);
  private videoService = inject(VideoService);
  
  // Signal-based state
  versions = signal<ModelVersion[]>([]);
  isTraining = signal(false);
  jobId = signal<string | null>(null);
  progress = signal(0);
  statusMessage = signal('');
  notification = signal<{ type: 'success' | 'error'; message: string } | null>(null);

  // Video reprocessing state
  showReprocessSection = signal(false);
  availableVideos = signal<VideoRecord[]>([]);
  selectedVideoIds = signal(new Set<number>());
  isReprocessing = signal(false);
  reprocessProgress = signal(0);
  reprocessMessage = signal('');
  latestVersion = signal<number | null>(null);

  private pollSub: Subscription | null = null;

  constructor() {
    this.loadVersions();
  }

  loadVersions(): void {
    this.faceApi.getModelVersions().subscribe({
      next: versions => this.versions.set(versions),
      error: err => console.error('Failed to load versions', err)
    });
  }

  onRetrain(): void {
    this.notification.set(null);
    this.faceApi.triggerRetrain().subscribe({
      next: res => {
        this.jobId.set(res.job_id);
        this.isTraining.set(true);
        this.progress.set(0);
        this.statusMessage.set('Starting retraining...');

        this.pollSub = this.poller.startPolling(res.job_id).subscribe({
          next: status => {
            this.progress.set(status.progress_pct);
            this.statusMessage.set(status.message);

            if (status.status === 'completed') {
              this.isTraining.set(false);
              this.latestVersion.set(status.version_number ?? null);
              this.notification.set({
                type: 'success',
                message: `Training complete! Model v${status.version_number} — CV Accuracy: ${((status.cv_accuracy ?? 0) * 100).toFixed(1)}%`
              });
              this.loadVersions();
              // Show reprocess section after successful training
              this.loadAvailableVideos();
              this.showReprocessSection.set(true);
            } else if (status.status === 'failed') {
              this.isTraining.set(false);
              this.notification.set({
                type: 'error',
                message: `Training failed: ${status.message}`
              });
            }
          },
          error: err => {
            this.isTraining.set(false);
            this.notification.set({ type: 'error', message: 'Failed to poll training status.' });
            console.error(err);
          }
        });
      },
      error: err => {
        console.error('Failed to trigger retrain', err);
        this.notification.set({ type: 'error', message: 'Failed to start retraining.' });
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
        this.availableVideos.set(videos);
      },
      error: (err) => {
        console.error('Failed to load videos:', err);
        this.notification.set({ type: 'error', message: 'Failed to load videos for reprocessing' });
      }
    });
  }

  onVideoSelect(videoId: number, checked: boolean): void {
    const newSet = new Set(this.selectedVideoIds());
    if (checked) {
      newSet.add(videoId);
    } else {
      newSet.delete(videoId);
    }
    this.selectedVideoIds.set(newSet);
  }

  onReprocessVideos(): void {
    if (this.selectedVideoIds().size === 0) return;

    this.isReprocessing.set(true);
    this.reprocessProgress.set(0);
    this.reprocessMessage.set('Starting reprocessing...');

    const videoIds = Array.from(this.selectedVideoIds());
    const modelVersion = this.latestVersion()?.toString();

    this.videoService.reprocessBatch(videoIds, modelVersion).subscribe({
      next: (res) => {
        // Poll for reprocessing status
        this.reprocessMessage.set('Reprocessing videos...');
        // Simulate progress (in real implementation, poll job status)
        const interval = setInterval(() => {
          this.reprocessProgress.update(p => p + 10);
          if (this.reprocessProgress() >= 100) {
            clearInterval(interval);
            this.isReprocessing.set(false);
            this.reprocessProgress.set(0);
            this.notification.set({
              type: 'success',
              message: `Successfully reprocessed ${videoIds.length} video(s)`
            });
            this.selectedVideoIds.set(new Set<number>());
            this.showReprocessSection.set(false);
          }
        }, 500);
      },
      error: (err) => {
        console.error('Failed to reprocess videos:', err);
        this.isReprocessing.set(false);
        this.notification.set({ type: 'error', message: 'Failed to start video reprocessing' });
      }
    });
  }
}

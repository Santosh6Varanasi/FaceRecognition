import { Component, Input, Output, EventEmitter } from '@angular/core';
import { NgIf, SlicePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { FaceApiService, UnknownFaceItem } from '../../services/face-api.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-face-card',
  standalone: true,
  imports: [NgIf, SlicePipe, FormsModule, RouterLink],
  template: `
    <div class="face-card" [class.selected]="selected">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <input type="checkbox" [checked]="selected"
               (change)="selectChange.emit({id: face.id, checked: $any($event.target).checked})">
        <span class="badge" [class.badge-active]="face.status === 'labeled'"
              [class.badge-inactive]="face.status !== 'labeled'">
          {{ face.status }}
        </span>
      </div>

      <img [src]="thumbnailUrl" [alt]="'Face ' + face.id"
           onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23e5e7eb%22 width=%22100%22 height=%22100%22/><text x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%236b7280%22>No image</text></svg>'">

      <div class="face-meta">
        <div>Prediction: <strong>{{ face.svm_prediction }}</strong></div>
        <div>Probability: {{ (face.svm_probability * 100).toFixed(1) }}%</div>
        <div>Detected: {{ face.created_at | slice:0:10 }}</div>
        <div *ngIf="face.source_video_id" style="margin-top:4px;">
          <a [routerLink]="['/video/playback', face.source_video_id]"
             [queryParams]="{t: face.frame_timestamp}"
             style="color:#3b82f6;text-decoration:none;font-size:12px;">
            📹 View in Video ({{ formatTimestamp(face.frame_timestamp) }})
          </a>
        </div>
      </div>

      <div class="face-actions" *ngIf="face.status === 'pending'">
        <input type="text" [(ngModel)]="inlineLabel" placeholder="Person name">
        <button class="btn-primary" [disabled]="!inlineLabel || assigning"
                (click)="onAssign()">
          {{ assigning ? '...' : 'Assign' }}
        </button>
      </div>

      <div style="margin-top:6px;" *ngIf="face.status === 'pending'">
        <button class="btn-danger" style="width:100%;" [disabled]="rejecting"
                (click)="onReject()">
          {{ rejecting ? '...' : 'Reject' }}
        </button>
      </div>
    </div>
  `
})
export class FaceCardComponent {
  @Input() face!: UnknownFaceItem;
  @Input() selected = false;
  @Output() selectChange = new EventEmitter<{ id: number; checked: boolean }>();
  @Output() labeled = new EventEmitter<number>();
  @Output() rejected = new EventEmitter<number>();

  inlineLabel = '';
  assigning = false;
  rejecting = false;

  get thumbnailUrl(): string {
    return `${environment.apiBaseUrl}${this.face.thumbnail_url}`;
  }

  constructor(private faceApi: FaceApiService) {}

  onAssign(): void {
    if (!this.inlineLabel) return;
    this.assigning = true;
    this.faceApi.labelFace(this.face.id, this.inlineLabel).subscribe({
      next: () => {
        this.assigning = false;
        this.labeled.emit(this.face.id);
      },
      error: () => { this.assigning = false; }
    });
  }

  onReject(): void {
    this.rejecting = true;
    this.faceApi.rejectFace(this.face.id).subscribe({
      next: () => {
        this.rejecting = false;
        this.rejected.emit(this.face.id);
      },
      error: () => { this.rejecting = false; }
    });
  }

  formatTimestamp(timestamp: number | null | undefined): string {
    if (!timestamp) return '0:00';
    const seconds = Math.floor(timestamp);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
}

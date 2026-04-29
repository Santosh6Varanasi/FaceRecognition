import { Component, OnInit, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';
import { FaceApiService, DashboardStats } from '../../services/face-api.service';
import { KpiCardComponent } from './kpi-card.component';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [KpiCardComponent, NgIf],
  template: `
    <div>
      <div class="page-header">
        <h1>Dashboard</h1>
      </div>

      <div *ngIf="stats" class="kpi-grid">
        <app-kpi-card
          title="Total Registered People"
          [value]="stats.total_people">
        </app-kpi-card>

        <app-kpi-card
          title="Total Training Faces"
          [value]="stats.total_faces">
        </app-kpi-card>

        <app-kpi-card
          title="Pending Unknown Faces"
          [value]="stats.pending_unknowns"
          [warning]="stats.pending_unknowns > 0"
          [link]="stats.pending_unknowns > 0 ? '/unknown-faces' : undefined">
        </app-kpi-card>

        <app-kpi-card
          title="Active Model Version"
          [value]="stats.active_model_version ?? 'None'">
        </app-kpi-card>

        <app-kpi-card
          title="Active Model CV Accuracy"
          [value]="stats.active_model_accuracy != null ? (stats.active_model_accuracy * 100).toFixed(1) + '%' : 'N/A'">
        </app-kpi-card>

        <app-kpi-card
          title="Total Detections Today"
          [value]="stats.total_detections_today">
        </app-kpi-card>
      </div>

      <div *ngIf="!stats" style="color: #6b7280; margin-top: 20px;">
        Loading stats...
      </div>
    </div>
  `
})
export class DashboardComponent implements OnInit {
  stats: DashboardStats | null = null;

  private destroyRef = inject(DestroyRef);

  constructor(private faceApi: FaceApiService) {}

  ngOnInit(): void {
    interval(30000).pipe(
      startWith(0),
      switchMap(() => this.faceApi.getDashboardStats()),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: stats => this.stats = stats,
      error: err => console.error('Failed to load dashboard stats', err)
    });
  }
}

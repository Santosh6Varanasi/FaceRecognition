import { Component, inject, signal, effect, ChangeDetectionStrategy } from '@angular/core';
import { FaceApiService, DashboardStats } from '../../services/face-api.service';
import { KpiCardComponent } from './kpi-card.component';


@Component({
    selector: 'app-dashboard',
    standalone: true,
    imports: [KpiCardComponent],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <div class="container mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <header class="page-header">
        <h1 class="page-title">Dashboard</h1>
      </header>
    
      @if (stats()) {
        <section 
          class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6"
          aria-label="Dashboard statistics"
        >
          <app-kpi-card
            title="Total Registered People"
            [value]="stats()!.total_people">
          </app-kpi-card>
          <app-kpi-card
            title="Total Training Faces"
            [value]="stats()!.total_faces">
          </app-kpi-card>
          <app-kpi-card
            title="Pending Unknown Faces"
            [value]="stats()!.pending_unknowns"
            [warning]="stats()!.pending_unknowns > 0"
            [link]="stats()!.pending_unknowns > 0 ? '/unknown-faces' : undefined">
          </app-kpi-card>
          <app-kpi-card
            title="Active Model Version"
            [value]="stats()!.active_model_version ?? 'None'">
          </app-kpi-card>
          <app-kpi-card
            title="Active Model CV Accuracy"
            [value]="stats()!.active_model_accuracy != null ? (stats()!.active_model_accuracy! * 100).toFixed(1) + '%' : 'N/A'">
          </app-kpi-card>
          <app-kpi-card
            title="Total Detections Today"
            [value]="stats()!.total_detections_today">
          </app-kpi-card>
        </section>
      }
    
      @if (!stats()) {
        <div 
          class="text-slate-500 dark:text-slate-400 mt-5 text-center"
          role="status"
          aria-live="polite"
          aria-label="Loading dashboard statistics"
        >
          Loading stats...
        </div>
      }
    </div>
    `
})
export class DashboardComponent {
  private faceApi = inject(FaceApiService);
  
  // Signal-based state
  stats = signal<DashboardStats | null>(null);
  
  private intervalId: number | null = null;

  constructor() {
    // Load stats immediately
    this.loadStats();
    
    // Set up polling with effect
    effect(() => {
      // Start polling interval
      this.intervalId = window.setInterval(() => {
        this.loadStats();
      }, 30000);
      
      // Cleanup function
      return () => {
        if (this.intervalId !== null) {
          clearInterval(this.intervalId);
          this.intervalId = null;
        }
      };
    });
  }
  
  private async loadStats(): Promise<void> {
    try {
      const stats = await this.faceApi.getDashboardStats().toPromise();
      if (stats) {
        this.stats.set(stats);
      }
    } catch (err) {
      console.error('Failed to load dashboard stats', err);
    }
  }
}

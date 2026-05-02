import { Component, inject, signal, computed, effect, ChangeDetectionStrategy } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { FaceApiService, UnknownFaceItem } from '../../services/face-api.service';
import { FaceCardComponent } from './face-card.component';
import { ConfirmationDialogComponent } from '../confirmation-dialog/confirmation-dialog.component';

@Component({
    selector: 'app-unknown-faces',
    standalone: true,
    imports: [FormsModule, RouterLink, FaceCardComponent, TitleCasePipe, ConfirmationDialogComponent],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <div class="container mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div class="page-header">
        <h1 class="page-title">Unknown Faces</h1>
        <div class="flex flex-wrap gap-3">
          <button class="btn-danger" (click)="onDeleteAllClick()">Delete All</button>
          <button class="btn-secondary" (click)="onRejectAllClick()">Reject All</button>
        </div>
      </div>
    
      <!-- Status counts -->
      <div class="flex flex-wrap gap-4 mb-4 text-slate-500 dark:text-slate-400 text-sm">
        <span>Pending: <span class="font-semibold">{{ statusCounts().pending }}</span></span>
        <span>Labeled: <span class="font-semibold">{{ statusCounts().labeled }}</span></span>
        <span>Rejected: <span class="font-semibold">{{ statusCounts().rejected }}</span></span>
      </div>
    
      <!-- Status filter tabs -->
      <div class="flex flex-wrap gap-2 mb-4">
        @for (s of statuses; track s) {
          <button
            class="filter-tab"
            [class.active]="statusFilter() === s"
            (click)="onStatusChange(s)">
            {{ s === '' ? 'All' : s | titlecase }}
          </button>
        }
      </div>
    
      <!-- Select all + bulk action bar -->
      <div class="flex flex-wrap items-center gap-3 mb-4">
        <label class="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
          <input type="checkbox" 
                 class="rounded border-slate-300 dark:border-slate-600 text-primary-600 focus:ring-primary-500"
                 (change)="onSelectAll($any($event.target).checked)">
          <span class="text-sm">Select All</span>
        </label>
        <span class="text-slate-500 dark:text-slate-400 text-sm">{{ total() }} total</span>
      </div>
    
      @if (selectedIds().size > 0) {
        <div class="bulk-action-bar">
          <span class="text-slate-700 dark:text-slate-300 font-medium">{{ selectedIds().size }} selected</span>
          <input type="text" 
                 [(ngModel)]="bulkName" 
                 placeholder="Person name" 
                 class="input-field w-full sm:w-48">
          <button class="btn-primary" [disabled]="!bulkName" (click)="onApplyBulkLabel()">
            Apply Label
          </button>
          @if (bulkSummary()) {
            <span class="text-sm text-green-700 dark:text-green-400">{{ bulkSummary() }}</span>
          }
        </div>
      }
    
      <!-- Loading -->
      @if (loading()) {
        <div class="text-slate-500 dark:text-slate-400 my-5 text-center">Loading...</div>
      }
    
      <!-- Face grid -->
      @if (!loading()) {
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4">
          @for (face of faces(); track face) {
            <app-face-card
              [face]="face"
              [selected]="selectedIds().has(face.id)"
              (selectChange)="onFaceSelect($event.id, $event.checked)"
              (labeled)="onFaceLabeled($event)"
              (rejected)="onFaceRejected($event)">
            </app-face-card>
          }
        </div>
      }
    
      @if (!loading() && faces().length === 0) {
        <div class="text-slate-500 dark:text-slate-400 my-5 text-center">
          No faces found.
        </div>
      }
    
      <!-- Pagination -->
      @if (total() > pageSize()) {
        <div class="flex items-center justify-center gap-4 mt-6">
          <button class="btn-secondary" [disabled]="page() <= 1" (click)="onPageChange(page() - 1)">
            ← Prev
          </button>
          <span class="text-slate-700 dark:text-slate-300">Page {{ page() }} of {{ totalPages() }}</span>
          <button class="btn-secondary" [disabled]="page() >= totalPages()" (click)="onPageChange(page() + 1)">
            Next →
          </button>
        </div>
      }
    
      <!-- Ready to retrain banner -->
      @if (!loading() && pendingCount() === 0 && total() > 0) {
        <div class="retrain-banner mt-6">
          <p>✅ All faces labeled or rejected — ready to retrain!</p>
          <a routerLink="/model">
            <button class="btn-primary">Retrain Model</button>
          </a>
        </div>
      }
    
      <!-- Confirmation dialogs -->
      <app-confirmation-dialog
        [isOpen]="showDeleteConfirm()"
        [title]="'Confirm Delete All'"
        [message]="deleteConfirmMessage()"
        [confirmText]="'Delete'"
        [isDanger]="true"
        (confirm)="onDeleteAllConfirm()"
        (cancel)="showDeleteConfirm.set(false)">
      </app-confirmation-dialog>
    
      <app-confirmation-dialog
        [isOpen]="showRejectConfirm()"
        [title]="'Confirm Reject All'"
        [message]="rejectConfirmMessage()"
        [confirmText]="'Reject'"
        [isDanger]="false"
        (confirm)="onRejectAllConfirm()"
        (cancel)="showRejectConfirm.set(false)">
      </app-confirmation-dialog>
    
      <!-- Success/Error messages -->
      @if (successMessage()) {
        <div class="notification success mt-4">
          {{ successMessage() }}
        </div>
      }
      @if (errorMessage()) {
        <div class="notification error mt-4">
          {{ errorMessage() }}
        </div>
      }
    </div>
    `
})
export class UnknownFacesComponent {
  private faceApi = inject(FaceApiService);
  
  // Signal-based state
  faces = signal<UnknownFaceItem[]>([]);
  total = signal(0);
  page = signal(1);
  pageSize = signal(20);
  statusFilter = signal('pending');
  selectedIds = signal(new Set<number>());
  bulkName = '';
  bulkSummary = signal('');
  loading = signal(false);
  pendingCount = signal(0);

  // Bulk operations state
  showDeleteConfirm = signal(false);
  showRejectConfirm = signal(false);
  deleteConfirmMessage = signal('');
  rejectConfirmMessage = signal('');
  successMessage = signal('');
  errorMessage = signal('');

  // Status counts
  statusCounts = signal({
    pending: 0,
    labeled: 0,
    rejected: 0
  });

  readonly statuses = ['', 'pending', 'labeled', 'rejected'];

  totalPages = computed(() => Math.ceil(this.total() / this.pageSize()));

  constructor() {
    this.loadFaces();
    this.loadStatusCounts();
  }

  loadStatusCounts(): void {
    // Load counts for each status
    ['pending', 'labeled', 'rejected'].forEach(status => {
      this.faceApi.getAffectedCount(status).subscribe({
        next: (res) => {
          this.statusCounts.update(counts => ({
            ...counts,
            [status]: res.count
          }));
        },
        error: (err) => {
          console.error(`Error loading ${status} count:`, err);
        }
      });
    });
  }

  loadFaces(): void {
    this.loading.set(true);
    this.selectedIds.set(new Set<number>());
    this.faceApi.getUnknownFaces(this.statusFilter() || undefined, this.page(), this.pageSize()).subscribe({
      next: res => {
        this.faces.set(res.items);
        this.total.set(res.total);
        this.loading.set(false);
        if (this.statusFilter() === 'pending' || this.statusFilter() === '') {
          this.pendingCount.set(this.statusFilter() === 'pending' ? res.total : res.items.filter(f => f.status === 'pending').length);
        }
      },
      error: () => { this.loading.set(false); }
    });
  }

  onStatusChange(status: string): void {
    this.statusFilter.set(status);
    this.page.set(1);
    this.loadFaces();
  }

  onSelectAll(checked: boolean): void {
    if (checked) {
      const newSet = new Set<number>();
      this.faces().forEach(f => newSet.add(f.id));
      this.selectedIds.set(newSet);
    } else {
      this.selectedIds.set(new Set<number>());
    }
  }

  onFaceSelect(id: number, checked: boolean): void {
    const newSet = new Set(this.selectedIds());
    if (checked) {
      newSet.add(id);
    } else {
      newSet.delete(id);
    }
    this.selectedIds.set(newSet);
  }

  onApplyBulkLabel(): void {
    if (!this.bulkName || this.bulkName.length < 2) {
      this.errorMessage.set('Label must be at least 2 characters');
      setTimeout(() => { this.errorMessage.set(''); }, 3000);
      return;
    }
    const labels = Array.from(this.selectedIds()).map(id => ({ id, person_name: this.bulkName }));
    this.faceApi.bulkLabelFaces(labels).subscribe({
      next: result => {
        this.bulkSummary.set(`${result.labeled_count} labeled, ${result.failed_ids.length} failed`);
        this.bulkName = '';
        this.loadFaces();
        this.loadStatusCounts();
      },
      error: () => {
        this.bulkSummary.set('Bulk label failed');
      }
    });
  }

  onDeleteAllClick(): void {
    const filterStatus = this.statusFilter() || 'all';
    this.faceApi.getAffectedCount(filterStatus).subscribe({
      next: (res) => {
        this.deleteConfirmMessage.set(`This will permanently delete ${res.count} face(s) matching the current filter (${filterStatus}). This action cannot be undone.`);
        this.showDeleteConfirm.set(true);
      },
      error: () => {
        this.errorMessage.set('Failed to get affected count');
        setTimeout(() => { this.errorMessage.set(''); }, 3000);
      }
    });
  }

  onDeleteAllConfirm(): void {
    this.showDeleteConfirm.set(false);
    const filterStatus = this.statusFilter() || 'all';
    
    this.faceApi.bulkDeleteFaces(filterStatus).subscribe({
      next: (result) => {
        this.successMessage.set(`Successfully deleted ${result.success_count} face(s)`);
        setTimeout(() => { this.successMessage.set(''); }, 5000);
        this.loadFaces();
        this.loadStatusCounts();
      },
      error: () => {
        this.errorMessage.set('Bulk delete operation failed');
        setTimeout(() => { this.errorMessage.set(''); }, 5000);
      }
    });
  }

  onRejectAllClick(): void {
    const filterStatus = this.statusFilter() || 'all';
    this.faceApi.getAffectedCount(filterStatus).subscribe({
      next: (res) => {
        this.rejectConfirmMessage.set(`This will reject ${res.count} face(s) matching the current filter (${filterStatus}).`);
        this.showRejectConfirm.set(true);
      },
      error: () => {
        this.errorMessage.set('Failed to get affected count');
        setTimeout(() => { this.errorMessage.set(''); }, 3000);
      }
    });
  }

  onRejectAllConfirm(): void {
    this.showRejectConfirm.set(false);
    const filterStatus = this.statusFilter() || 'all';
    
    this.faceApi.bulkRejectFaces(filterStatus).subscribe({
      next: (result) => {
        this.successMessage.set(`Successfully rejected ${result.success_count} face(s)`);
        setTimeout(() => { this.successMessage.set(''); }, 5000);
        this.loadFaces();
        this.loadStatusCounts();
      },
      error: () => {
        this.errorMessage.set('Bulk reject operation failed');
        setTimeout(() => { this.errorMessage.set(''); }, 5000);
      }
    });
  }

  onPageChange(newPage: number): void {
    this.page.set(newPage);
    this.loadFaces();
  }

  onFaceLabeled(id: number): void {
    this.faces.update(faces => faces.filter(f => f.id !== id));
    this.total.update(t => Math.max(0, t - 1));
    this.pendingCount.update(p => Math.max(0, p - 1));
    this.loadStatusCounts();
  }

  onFaceRejected(id: number): void {
    this.faces.update(faces => faces.filter(f => f.id !== id));
    this.total.update(t => Math.max(0, t - 1));
    this.pendingCount.update(p => Math.max(0, p - 1));
    this.loadStatusCounts();
  }
}

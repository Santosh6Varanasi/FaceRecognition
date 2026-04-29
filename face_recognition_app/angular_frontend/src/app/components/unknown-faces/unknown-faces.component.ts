import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { FaceApiService, UnknownFaceItem } from '../../services/face-api.service';
import { FaceCardComponent } from './face-card.component';
import { ConfirmationDialogComponent } from '../confirmation-dialog/confirmation-dialog.component';

@Component({
  selector: 'app-unknown-faces',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, RouterLink, FaceCardComponent, TitleCasePipe, ConfirmationDialogComponent],
  template: `
    <div>
      <div class="page-header">
        <h1>Unknown Faces</h1>
        <div style="display:flex;gap:12px;">
          <button class="btn-danger" (click)="onDeleteAllClick()">Delete All</button>
          <button class="btn-secondary" (click)="onRejectAllClick()">Reject All</button>
        </div>
      </div>

      <!-- Status counts -->
      <div style="display:flex;gap:16px;margin-bottom:16px;color:#9ca3af;font-size:14px;">
        <span>Pending: {{ statusCounts.pending }}</span>
        <span>Labeled: {{ statusCounts.labeled }}</span>
        <span>Rejected: {{ statusCounts.rejected }}</span>
      </div>

      <!-- Status filter tabs -->
      <div class="filter-tabs">
        <button *ngFor="let s of statuses"
                [class.active]="statusFilter === s"
                (click)="onStatusChange(s)">
          {{ s === '' ? 'All' : s | titlecase }}
        </button>
      </div>

      <!-- Select all + bulk action bar -->
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" (change)="onSelectAll($any($event.target).checked)">
          Select All
        </label>
        <span style="color:#6b7280;font-size:13px;">{{ total }} total</span>
      </div>

      <div class="bulk-action-bar" *ngIf="selectedIds.size > 0">
        <span>{{ selectedIds.size }} selected</span>
        <input type="text" [(ngModel)]="bulkName" placeholder="Person name" style="width:200px;">
        <button class="btn-primary" [disabled]="!bulkName" (click)="onApplyBulkLabel()">
          Apply Label
        </button>
        <span *ngIf="bulkSummary" style="font-size:13px;color:#065f46;">{{ bulkSummary }}</span>
      </div>

      <!-- Loading -->
      <div *ngIf="loading" style="color:#6b7280;margin:20px 0;">Loading...</div>

      <!-- Face grid -->
      <div class="face-grid" *ngIf="!loading">
        <app-face-card
          *ngFor="let face of faces"
          [face]="face"
          [selected]="selectedIds.has(face.id)"
          (selectChange)="onFaceSelect($event.id, $event.checked)"
          (labeled)="onFaceLabeled($event)"
          (rejected)="onFaceRejected($event)">
        </app-face-card>
      </div>

      <div *ngIf="!loading && faces.length === 0" style="color:#6b7280;margin:20px 0;">
        No faces found.
      </div>

      <!-- Pagination -->
      <div class="pagination" *ngIf="total > pageSize">
        <button class="btn-secondary" [disabled]="page <= 1" (click)="onPageChange(page - 1)">
          ← Prev
        </button>
        <span>Page {{ page }} of {{ totalPages }}</span>
        <button class="btn-secondary" [disabled]="page >= totalPages" (click)="onPageChange(page + 1)">
          Next →
        </button>
      </div>

      <!-- Ready to retrain banner -->
      <div class="retrain-banner" *ngIf="!loading && pendingCount === 0 && total > 0">
        <p>✅ All faces labeled or rejected — ready to retrain!</p>
        <a routerLink="/model">
          <button class="btn-primary">Retrain Model</button>
        </a>
      </div>

      <!-- Confirmation dialogs -->
      <app-confirmation-dialog
        [isOpen]="showDeleteConfirm"
        [title]="'Confirm Delete All'"
        [message]="deleteConfirmMessage"
        [confirmText]="'Delete'"
        [isDanger]="true"
        (confirm)="onDeleteAllConfirm()"
        (cancel)="showDeleteConfirm = false">
      </app-confirmation-dialog>

      <app-confirmation-dialog
        [isOpen]="showRejectConfirm"
        [title]="'Confirm Reject All'"
        [message]="rejectConfirmMessage"
        [confirmText]="'Reject'"
        [isDanger]="false"
        (confirm)="onRejectAllConfirm()"
        (cancel)="showRejectConfirm = false">
      </app-confirmation-dialog>

      <!-- Success/Error messages -->
      <div *ngIf="successMessage" style="background:#14532d;border:1px solid #22c55e;border-radius:6px;padding:12px;margin:16px 0;color:#86efac;">
        {{ successMessage }}
      </div>
      <div *ngIf="errorMessage" style="background:#450a0a;border:1px solid #ef4444;border-radius:6px;padding:12px;margin:16px 0;color:#fca5a5;">
        {{ errorMessage }}
      </div>
    </div>
  `
})
export class UnknownFacesComponent implements OnInit {
  faces: UnknownFaceItem[] = [];
  total = 0;
  page = 1;
  pageSize = 20;
  statusFilter = 'pending';
  selectedIds = new Set<number>();
  bulkName = '';
  bulkSummary = '';
  loading = false;
  pendingCount = 0;

  // Bulk operations state
  showDeleteConfirm = false;
  showRejectConfirm = false;
  deleteConfirmMessage = '';
  rejectConfirmMessage = '';
  successMessage = '';
  errorMessage = '';

  // Status counts
  statusCounts = {
    pending: 0,
    labeled: 0,
    rejected: 0
  };

  readonly statuses = ['', 'pending', 'labeled', 'rejected'];

  get totalPages(): number {
    return Math.ceil(this.total / this.pageSize);
  }

  constructor(private faceApi: FaceApiService) {}

  ngOnInit(): void {
    this.loadFaces();
    this.loadStatusCounts();
  }

  loadStatusCounts(): void {
    // Load counts for each status
    ['pending', 'labeled', 'rejected'].forEach(status => {
      this.faceApi.getAffectedCount(status).subscribe({
        next: (res) => {
          this.statusCounts[status as keyof typeof this.statusCounts] = res.count;
        },
        error: (err) => {
          console.error(`Error loading ${status} count:`, err);
        }
      });
    });
  }

  loadFaces(): void {
    this.loading = true;
    this.selectedIds.clear();
    this.faceApi.getUnknownFaces(this.statusFilter || undefined, this.page, this.pageSize).subscribe({
      next: res => {
        this.faces = res.items;
        this.total = res.total;
        this.loading = false;
        if (this.statusFilter === 'pending' || this.statusFilter === '') {
          this.pendingCount = this.statusFilter === 'pending' ? res.total : res.items.filter(f => f.status === 'pending').length;
        }
      },
      error: () => { this.loading = false; }
    });
  }

  onStatusChange(status: string): void {
    this.statusFilter = status;
    this.page = 1;
    this.loadFaces();
  }

  onSelectAll(checked: boolean): void {
    if (checked) {
      this.faces.forEach(f => this.selectedIds.add(f.id));
    } else {
      this.selectedIds.clear();
    }
  }

  onFaceSelect(id: number, checked: boolean): void {
    if (checked) {
      this.selectedIds.add(id);
    } else {
      this.selectedIds.delete(id);
    }
  }

  onApplyBulkLabel(): void {
    if (!this.bulkName || this.bulkName.length < 2) {
      this.errorMessage = 'Label must be at least 2 characters';
      setTimeout(() => { this.errorMessage = ''; }, 3000);
      return;
    }
    const labels = Array.from(this.selectedIds).map(id => ({ id, person_name: this.bulkName }));
    this.faceApi.bulkLabelFaces(labels).subscribe({
      next: result => {
        this.bulkSummary = `${result.labeled_count} labeled, ${result.failed_ids.length} failed`;
        this.bulkName = '';
        this.loadFaces();
        this.loadStatusCounts();
      },
      error: () => {
        this.bulkSummary = 'Bulk label failed';
      }
    });
  }

  onDeleteAllClick(): void {
    const filterStatus = this.statusFilter || 'all';
    this.faceApi.getAffectedCount(filterStatus).subscribe({
      next: (res) => {
        this.deleteConfirmMessage = `This will permanently delete ${res.count} face(s) matching the current filter (${filterStatus}). This action cannot be undone.`;
        this.showDeleteConfirm = true;
      },
      error: () => {
        this.errorMessage = 'Failed to get affected count';
        setTimeout(() => { this.errorMessage = ''; }, 3000);
      }
    });
  }

  onDeleteAllConfirm(): void {
    this.showDeleteConfirm = false;
    const filterStatus = this.statusFilter || 'all';
    
    this.faceApi.bulkDeleteFaces(filterStatus).subscribe({
      next: (result) => {
        this.successMessage = `Successfully deleted ${result.success_count} face(s)`;
        setTimeout(() => { this.successMessage = ''; }, 5000);
        this.loadFaces();
        this.loadStatusCounts();
      },
      error: () => {
        this.errorMessage = 'Bulk delete operation failed';
        setTimeout(() => { this.errorMessage = ''; }, 5000);
      }
    });
  }

  onRejectAllClick(): void {
    const filterStatus = this.statusFilter || 'all';
    this.faceApi.getAffectedCount(filterStatus).subscribe({
      next: (res) => {
        this.rejectConfirmMessage = `This will reject ${res.count} face(s) matching the current filter (${filterStatus}).`;
        this.showRejectConfirm = true;
      },
      error: () => {
        this.errorMessage = 'Failed to get affected count';
        setTimeout(() => { this.errorMessage = ''; }, 3000);
      }
    });
  }

  onRejectAllConfirm(): void {
    this.showRejectConfirm = false;
    const filterStatus = this.statusFilter || 'all';
    
    this.faceApi.bulkRejectFaces(filterStatus).subscribe({
      next: (result) => {
        this.successMessage = `Successfully rejected ${result.success_count} face(s)`;
        setTimeout(() => { this.successMessage = ''; }, 5000);
        this.loadFaces();
        this.loadStatusCounts();
      },
      error: () => {
        this.errorMessage = 'Bulk reject operation failed';
        setTimeout(() => { this.errorMessage = ''; }, 5000);
      }
    });
  }

  onPageChange(newPage: number): void {
    this.page = newPage;
    this.loadFaces();
  }

  onFaceLabeled(id: number): void {
    this.faces = this.faces.filter(f => f.id !== id);
    this.total = Math.max(0, this.total - 1);
    this.pendingCount = Math.max(0, this.pendingCount - 1);
    this.loadStatusCounts();
  }

  onFaceRejected(id: number): void {
    this.faces = this.faces.filter(f => f.id !== id);
    this.total = Math.max(0, this.total - 1);
    this.pendingCount = Math.max(0, this.pendingCount - 1);
    this.loadStatusCounts();
  }
}

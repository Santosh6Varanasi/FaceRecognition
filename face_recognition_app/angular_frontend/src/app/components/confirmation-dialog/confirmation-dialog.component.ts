import { Component, Input, Output, EventEmitter } from '@angular/core';


@Component({
    selector: 'app-confirmation-dialog',
    imports: [],
    template: `
    @if (isOpen) {
      <div class="dialog-overlay" (click)="onCancel()">
        <div class="dialog-content" (click)="$event.stopPropagation()">
          <h3 style="margin:0 0 12px 0;color:#e5e7eb;">{{ title }}</h3>
          <p style="color:#9ca3af;margin:0 0 20px 0;">{{ message }}</p>
          <div style="display:flex;gap:12px;justify-content:flex-end;">
            <button class="btn-secondary" (click)="onCancel()">Cancel</button>
            <button class="btn-primary" [class.btn-danger]="isDanger" (click)="onConfirm()">
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    }
    `,
    styles: [`
    .dialog-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    .dialog-content {
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 8px;
      padding: 24px;
      min-width: 400px;
      max-width: 500px;
    }
    .btn-danger {
      background: #dc2626;
    }
    .btn-danger:hover {
      background: #b91c1c;
    }
  `]
})
export class ConfirmationDialogComponent {
  @Input() isOpen = false;
  @Input() title = 'Confirm Action';
  @Input() message = 'Are you sure you want to proceed?';
  @Input() confirmText = 'Confirm';
  @Input() isDanger = false;

  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  onConfirm(): void {
    this.confirm.emit();
  }

  onCancel(): void {
    this.cancel.emit();
  }
}

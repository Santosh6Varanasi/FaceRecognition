import { Component, inject, signal, computed, ChangeDetectionStrategy } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { FaceApiService, Person } from '../../services/face-api.service';

@Component({
    selector: 'app-people-list',
    standalone: true,
    imports: [FormsModule, DatePipe],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <div class="container mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div class="page-header">
        <h1 class="page-title">People</h1>
        <button class="btn-primary" (click)="showModal.set(true); addError.set('')">
          Add Person
        </button>
      </div>
    
      <!-- Search -->
      <div class="mb-4">
        <input type="search" 
               [(ngModel)]="searchQuery"
               (input)="onSearch(searchQuery)"
               placeholder="Search by name..."
               class="input-field max-w-sm">
      </div>
    
      <!-- Table -->
      <div class="table-container">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">Name</th>
              <th class="table-header">Role</th>
              <th class="table-header">Face Count</th>
              <th class="table-header">Registered Date</th>
            </tr>
          </thead>
          <tbody>
            @for (person of filteredPeople(); track person) {
              <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <td class="table-cell">{{ person.name }}</td>
                <td class="table-cell">{{ person.role || '—' }}</td>
                <td class="table-cell">{{ person.face_count }}</td>
                <td class="table-cell">{{ person.created_at | date:'mediumDate' }}</td>
              </tr>
            }
            @if (filteredPeople().length === 0) {
              <tr>
                <td colspan="4" class="table-cell text-center text-slate-500 dark:text-slate-400">
                  No people found.
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    
      <!-- Add Person Modal -->
      @if (showModal()) {
        <div class="modal-overlay" (click)="onOverlayClick($event)">
          <div class="modal">
            <h3 class="text-xl font-bold text-slate-900 dark:text-slate-100 mb-4">Add Person</h3>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Name <span class="text-red-600 dark:text-red-400">*</span>
                </label>
                <input type="text" 
                       [(ngModel)]="newPersonName" 
                       placeholder="Full name"
                       class="input-field">
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <input type="text" 
                       [(ngModel)]="newPersonDescription" 
                       placeholder="Optional description"
                       class="input-field">
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Role
                </label>
                <input type="text" 
                       [(ngModel)]="newPersonRole" 
                       placeholder="e.g. Employee, Visitor"
                       class="input-field">
              </div>
              @if (addError()) {
                <div class="inline-error">{{ addError() }}</div>
              }
              <div class="flex gap-3 justify-end pt-2">
                <button class="btn-secondary" (click)="showModal.set(false); addError.set('')">
                  Cancel
                </button>
                <button class="btn-primary" [disabled]="!newPersonName" (click)="onAddPerson()">
                  Add
                </button>
              </div>
            </div>
          </div>
        </div>
      }
    </div>
    `
})
export class PeopleListComponent {
  private faceApi = inject(FaceApiService);
  
  // Signal-based state
  people = signal<Person[]>([]);
  filteredPeople = signal<Person[]>([]);
  searchQuery = '';
  showModal = signal(false);
  newPersonName = '';
  newPersonDescription = '';
  newPersonRole = '';
  addError = signal('');

  constructor() {
    this.loadPeople();
  }

  loadPeople(): void {
    this.faceApi.getPeople().subscribe({
      next: people => {
        this.people.set(people);
        this.filteredPeople.set(people);
        this.onSearch(this.searchQuery);
      },
      error: err => console.error('Failed to load people', err)
    });
  }

  onSearch(query: string): void {
    const q = query.toLowerCase().trim();
    const currentPeople = this.people();
    this.filteredPeople.set(
      q ? currentPeople.filter(p => p.name.toLowerCase().includes(q)) : [...currentPeople]
    );
  }

  onAddPerson(): void {
    if (!this.newPersonName) return;
    this.addError.set('');

    this.faceApi.addPerson(
      this.newPersonName,
      this.newPersonDescription || undefined,
      this.newPersonRole || undefined
    ).subscribe({
      next: () => {
        this.showModal.set(false);
        this.newPersonName = '';
        this.newPersonDescription = '';
        this.newPersonRole = '';
        this.loadPeople();
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 409) {
          this.addError.set('A person with this name already exists.');
        } else {
          this.addError.set('Failed to add person. Please try again.');
        }
      }
    });
  }

  onOverlayClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.showModal.set(false);
      this.addError.set('');
    }
  }
}

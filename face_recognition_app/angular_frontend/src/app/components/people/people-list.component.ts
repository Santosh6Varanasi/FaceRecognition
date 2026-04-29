import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { FaceApiService, Person } from '../../services/face-api.service';

@Component({
  selector: 'app-people-list',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, DatePipe],
  template: `
    <div>
      <div class="page-header">
        <h1>People</h1>
        <button class="btn-primary" (click)="showModal = true; addError = ''">
          Add Person
        </button>
      </div>

      <!-- Search -->
      <div style="margin-bottom:16px;">
        <input type="search" [(ngModel)]="searchQuery"
               (input)="onSearch(searchQuery)"
               placeholder="Search by name..."
               style="max-width:300px;">
      </div>

      <!-- Table -->
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Role</th>
            <th>Face Count</th>
            <th>Registered Date</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let person of filteredPeople">
            <td>{{ person.name }}</td>
            <td>{{ person.role || '—' }}</td>
            <td>{{ person.face_count }}</td>
            <td>{{ person.created_at | date:'mediumDate' }}</td>
          </tr>
          <tr *ngIf="filteredPeople.length === 0">
            <td colspan="4" style="text-align:center;color:#6b7280;">No people found.</td>
          </tr>
        </tbody>
      </table>

      <!-- Add Person Modal -->
      <div class="modal-overlay" *ngIf="showModal" (click)="onOverlayClick($event)">
        <div class="modal">
          <h3>Add Person</h3>

          <div class="form-group">
            <label>Name <span style="color:#ef4444">*</span></label>
            <input type="text" [(ngModel)]="newPerson.name" placeholder="Full name">
          </div>

          <div class="form-group">
            <label>Description</label>
            <input type="text" [(ngModel)]="newPerson.description" placeholder="Optional description">
          </div>

          <div class="form-group">
            <label>Role</label>
            <input type="text" [(ngModel)]="newPerson.role" placeholder="e.g. Employee, Visitor">
          </div>

          <div class="inline-error" *ngIf="addError">{{ addError }}</div>

          <div class="modal-actions">
            <button class="btn-secondary" (click)="showModal = false; addError = ''">Cancel</button>
            <button class="btn-primary" [disabled]="!newPerson.name" (click)="onAddPerson()">
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class PeopleListComponent implements OnInit {
  people: Person[] = [];
  filteredPeople: Person[] = [];
  searchQuery = '';
  showModal = false;
  newPerson = { name: '', description: '', role: '' };
  addError = '';

  constructor(private faceApi: FaceApiService) {}

  ngOnInit(): void {
    this.loadPeople();
  }

  loadPeople(): void {
    this.faceApi.getPeople().subscribe({
      next: people => {
        this.people = people;
        this.filteredPeople = people;
        this.onSearch(this.searchQuery);
      },
      error: err => console.error('Failed to load people', err)
    });
  }

  onSearch(query: string): void {
    const q = query.toLowerCase().trim();
    this.filteredPeople = q
      ? this.people.filter(p => p.name.toLowerCase().includes(q))
      : [...this.people];
  }

  onAddPerson(): void {
    if (!this.newPerson.name) return;
    this.addError = '';

    this.faceApi.addPerson(
      this.newPerson.name,
      this.newPerson.description || undefined,
      this.newPerson.role || undefined
    ).subscribe({
      next: () => {
        this.showModal = false;
        this.newPerson = { name: '', description: '', role: '' };
        this.loadPeople();
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 409) {
          this.addError = 'A person with this name already exists.';
        } else {
          this.addError = 'Failed to add person. Please try again.';
        }
      }
    });
  }

  onOverlayClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.showModal = false;
      this.addError = '';
    }
  }
}

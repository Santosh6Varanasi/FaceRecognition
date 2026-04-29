import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { TrainingService, UploadImageResponse, RetrainStatusResponse } from '../../services/training.service';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

interface UploadedImage {
  id: string;
  file: File;
  preview: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  imageId?: string;
  imagePath?: string;
  faceBbox?: { x1: number; y1: number; x2: number; y2: number };
  detectionConfidence?: number;
  errorMessage?: string;
  personName?: string;
  personId?: number;
  isLabeled?: boolean;
}

interface RetrainingJob {
  jobId: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  versionNumber?: number;
  cvAccuracy?: number;
  numClasses?: number;
}

interface Person {
  id: number;
  name: string;
}

@Component({
  selector: 'app-training',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './training.component.html',
  styleUrls: ['./training.component.css']
})
export class TrainingComponent {
  uploadedImages: UploadedImage[] = [];
  retrainingJob: RetrainingJob = {
    jobId: '',
    status: 'idle',
    progress: 0,
    message: ''
  };
  people: Person[] = [];
  private pollingSubscription?: Subscription;

  constructor(
    private trainingService: TrainingService,
    private http: HttpClient
  ) {
    this.loadPeopleForAutocomplete();
  }

  onFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const files = Array.from(input.files);
    for (const file of files) {
      // Generate preview
      const reader = new FileReader();
      reader.onload = (e) => {
        const image: UploadedImage = {
          id: this.generateId(),
          file,
          preview: e.target?.result as string,
          status: 'pending'
        };
        this.uploadedImages.push(image);
        
        // Auto-upload immediately
        this.uploadImage(image);
      };
      reader.readAsDataURL(file);
    }

    // Reset input
    input.value = '';
  }

  async uploadImage(image: UploadedImage): Promise<void> {
    image.status = 'uploading';
    
    this.trainingService.uploadImage(image.file).subscribe({
      next: (result: UploadImageResponse) => {
        image.status = 'success';
        image.imageId = result.image_id;
        image.imagePath = result.image_path;
        image.faceBbox = result.face_bbox;
        image.detectionConfidence = result.detection_confidence;
        image.errorMessage = undefined;
      },
      error: (error: any) => {
        image.status = 'error';
        image.errorMessage = error.message || 'Upload failed';
      }
    });
  }

  labelImage(image: UploadedImage): void {
    if (!image.imageId || !image.personName || image.personName.trim() === '') {
      image.errorMessage = 'Please enter a person name';
      return;
    }

    this.trainingService.labelImage(image.imageId, image.personName.trim()).subscribe({
      next: (result) => {
        image.personId = result.person_id;
        image.isLabeled = true;
        image.errorMessage = undefined;
        
        // Add to people list if new
        if (!this.people.find(p => p.id === result.person_id)) {
          this.people.push({ id: result.person_id, name: result.person_name });
        }
      },
      error: (error: any) => {
        image.errorMessage = error.message || 'Labeling failed';
      }
    });
  }

  triggerRetraining(): void {
    this.retrainingJob.status = 'running';
    this.retrainingJob.progress = 0;
    this.retrainingJob.message = 'Starting retraining...';

    this.trainingService.triggerRetraining().subscribe({
      next: (result) => {
        this.retrainingJob.jobId = result.job_id;
        this.startPolling(result.job_id);
      },
      error: (error: any) => {
        this.retrainingJob.status = 'failed';
        this.retrainingJob.message = error.message || 'Retraining failed';
      }
    });
  }

  private startPolling(jobId: string): void {
    // Poll every 3 seconds
    this.pollingSubscription = interval(3000).pipe(
      switchMap(() => this.trainingService.pollRetrainingStatus(jobId)),
      takeWhile((status: RetrainStatusResponse) => 
        status.status === 'queued' || status.status === 'running', 
        true // Include the final emission
      )
    ).subscribe({
      next: (status: RetrainStatusResponse) => {
        this.retrainingJob.progress = status.progress_pct;
        this.retrainingJob.message = status.message;
        
        if (status.status === 'completed') {
          this.retrainingJob.status = 'completed';
          this.retrainingJob.versionNumber = status.version_number;
          this.retrainingJob.cvAccuracy = status.cv_accuracy;
          this.retrainingJob.numClasses = status.num_classes;
        } else if (status.status === 'failed') {
          this.retrainingJob.status = 'failed';
        }
      },
      error: (error: any) => {
        this.retrainingJob.status = 'failed';
        this.retrainingJob.message = error.message || 'Polling failed';
      }
    });
  }

  canRetrain(): boolean {
    return this.uploadedImages.some(img => img.isLabeled) && 
           this.retrainingJob.status !== 'running';
  }

  loadPeopleForAutocomplete(): void {
    const apiUrl = environment.apiBaseUrl || 'http://localhost:3000';
    this.http.get<Person[]>(`${apiUrl}/api/people`).subscribe({
      next: (people) => {
        this.people = people;
      },
      error: (error) => {
        console.error('Failed to load people:', error);
      }
    });
  }

  private generateId(): string {
    return Math.random().toString(36).substring(2, 15);
  }

  ngOnDestroy(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
    }
  }
}

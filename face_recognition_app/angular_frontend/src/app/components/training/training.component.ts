import { Component, signal, computed } from '@angular/core';
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
    imports: [CommonModule, FormsModule],
    templateUrl: './training.component.html',
    styleUrls: ['./training.component.css']
})
export class TrainingComponent {
  // Use signals for reactive state management
  uploadedImages = signal<UploadedImage[]>([]);
  retrainingJob = signal<RetrainingJob>({
    jobId: '',
    status: 'idle',
    progress: 0,
    message: ''
  });
  people = signal<Person[]>([]);
  
  // Computed signal for retrain button state
  canRetrain = computed(() => 
    this.uploadedImages().some(img => img.isLabeled) && 
    this.retrainingJob().status !== 'running'
  );
  
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
        
        // Add to signal array
        this.uploadedImages.update(images => [...images, image]);
        
        // Auto-upload immediately
        this.uploadImage(image);
      };
      reader.readAsDataURL(file);
    }

    // Reset input
    input.value = '';
  }

  uploadImage(image: UploadedImage): void {
    console.log('Starting upload for image:', image.file.name);
    
    // Update status to uploading
    this.updateImageStatus(image.id, 'uploading');
    
    this.trainingService.uploadImage(image.file).subscribe({
      next: (result: UploadImageResponse) => {
        console.log('Upload successful:', result);
        
        // Update image with result
        this.uploadedImages.update(images => 
          images.map(img => 
            img.id === image.id 
              ? {
                  ...img,
                  status: 'success' as const,
                  imageId: result.image_id,
                  imagePath: result.image_path,
                  faceBbox: result.face_bbox,
                  detectionConfidence: result.detection_confidence,
                  errorMessage: undefined
                }
              : img
          )
        );
      },
      error: (error: any) => {
        console.error('Upload failed:', error);
        
        // Update image with error
        this.uploadedImages.update(images =>
          images.map(img =>
            img.id === image.id
              ? {
                  ...img,
                  status: 'error' as const,
                  errorMessage: error.message || 'Upload failed'
                }
              : img
          )
        );
      }
    });
  }

  private updateImageStatus(imageId: string, status: UploadedImage['status']): void {
    this.uploadedImages.update(images =>
      images.map(img =>
        img.id === imageId ? { ...img, status } : img
      )
    );
  }

  labelImage(image: UploadedImage): void {
    if (!image.imageId || !image.personName || image.personName.trim() === '') {
      this.uploadedImages.update(images =>
        images.map(img =>
          img.id === image.id
            ? { ...img, errorMessage: 'Please enter a person name' }
            : img
        )
      );
      return;
    }

    this.trainingService.labelImage(image.imageId, image.personName.trim()).subscribe({
      next: (result) => {
        // Update image with label result
        this.uploadedImages.update(images =>
          images.map(img =>
            img.id === image.id
              ? {
                  ...img,
                  personId: result.person_id,
                  isLabeled: true,
                  errorMessage: undefined
                }
              : img
          )
        );
        
        // Add to people list if new
        const currentPeople = this.people();
        if (!currentPeople.find(p => p.id === result.person_id)) {
          this.people.update(people => [...people, { id: result.person_id, name: result.person_name }]);
        }
      },
      error: (error: any) => {
        this.uploadedImages.update(images =>
          images.map(img =>
            img.id === image.id
              ? { ...img, errorMessage: error.message || 'Labeling failed' }
              : img
          )
        );
      }
    });
  }

  triggerRetraining(): void {
    this.retrainingJob.set({
      jobId: '',
      status: 'running',
      progress: 0,
      message: 'Starting retraining...'
    });

    this.trainingService.triggerRetraining().subscribe({
      next: (result) => {
        this.retrainingJob.update(job => ({ ...job, jobId: result.job_id }));
        this.startPolling(result.job_id);
      },
      error: (error: any) => {
        this.retrainingJob.set({
          jobId: '',
          status: 'failed',
          progress: 0,
          message: error.message || 'Retraining failed'
        });
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
        if (status.status === 'completed') {
          this.retrainingJob.set({
            jobId: jobId,
            status: 'completed',
            progress: status.progress_pct,
            message: status.message,
            versionNumber: status.version_number,
            cvAccuracy: status.cv_accuracy,
            numClasses: status.num_classes
          });
        } else if (status.status === 'failed') {
          this.retrainingJob.set({
            jobId: jobId,
            status: 'failed',
            progress: status.progress_pct,
            message: status.message
          });
        } else {
          this.retrainingJob.update(job => ({
            ...job,
            progress: status.progress_pct,
            message: status.message
          }));
        }
      },
      error: (error: any) => {
        this.retrainingJob.update(job => ({
          ...job,
          status: 'failed',
          message: error.message || 'Polling failed'
        }));
      }
    });
  }

  loadPeopleForAutocomplete(): void {
    const apiUrl = environment.apiBaseUrl || 'http://localhost:3000';
    this.http.get<Person[]>(`${apiUrl}/api/people`).subscribe({
      next: (people) => {
        this.people.set(people);
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

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, timer } from 'rxjs';
import { catchError, retry, switchMap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface UploadImageResponse {
  image_id: string;
  image_path: string;
  face_bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
  detection_confidence: number;
  embedding?: number[];
  message: string;
}

export interface LabelImageResponse {
  person_id: number;
  person_name: string;
  success: boolean;
  message: string;
}

export interface RetrainResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface RetrainStatusResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  message: string;
  version_number?: number;
  cv_accuracy?: number;
  num_classes?: number;
}

@Injectable({ providedIn: 'root' })
export class TrainingService {
  private apiUrl = environment.apiBaseUrl || 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  /**
   * Upload image file for validation.
   * Automatically retries on network errors (max 3 attempts).
   */
  uploadImage(file: File): Observable<UploadImageResponse> {
    const formData = new FormData();
    formData.append('image', file);

    return this.http.post<UploadImageResponse>(
      `${this.apiUrl}/api/training/upload-image`,
      formData
    ).pipe(
      retry({
        count: 2,
        delay: (error: HttpErrorResponse, retryCount: number) => {
          // Only retry on network errors (status 0 or 5xx)
          if (error.status === 0 || error.status >= 500) {
            // Exponential backoff: 1s, 2s
            return timer(1000 * Math.pow(2, retryCount - 1));
          }
          // Don't retry on validation errors (4xx)
          return throwError(() => error);
        }
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Assign person name to uploaded image.
   */
  labelImage(imageId: string, personName: string): Observable<LabelImageResponse> {
    return this.http.post<LabelImageResponse>(
      `${this.apiUrl}/api/training/label-image`,
      { image_id: imageId, person_name: personName }
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Trigger model retraining.
   */
  triggerRetraining(): Observable<RetrainResponse> {
    return this.http.post<RetrainResponse>(
      `${this.apiUrl}/api/training/retrain`,
      {}
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Poll retraining job status.
   */
  pollRetrainingStatus(jobId: string): Observable<RetrainStatusResponse> {
    return this.http.get<RetrainStatusResponse>(
      `${this.apiUrl}/api/training/retrain-status/${jobId}`
    ).pipe(
      catchError(this.handleError)
    );
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An error occurred';
    
    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      if (error.error?.error) {
        errorMessage = error.error.error;
      } else if (error.status === 0) {
        errorMessage = 'Upload failed: network error';
      } else {
        errorMessage = `Server error: ${error.status}`;
      }
    }
    
    return throwError(() => ({ status: error.status, message: errorMessage }));
  }
}

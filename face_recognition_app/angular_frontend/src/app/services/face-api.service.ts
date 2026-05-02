import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DashboardStats {
  total_people: number;
  total_faces: number;
  pending_unknowns: number;
  labeled_unknowns: number;
  active_model_version: number | null;
  active_model_accuracy: number | null;
  total_detections_today: number;
}

export interface UnknownFaceItem {
  id: number;
  source_image_path: string;
  svm_prediction: string;
  svm_probability: number;
  detection_confidence: number;
  status: 'pending' | 'reviewed' | 'labeled' | 'rejected';
  created_at: string;
  thumbnail_url: string;
  source_video_id?: number | null;
  frame_timestamp?: number | null;
  frame_number?: number | null;
}

export interface UnknownFacesResponse {
  total: number;
  page: number;
  page_size: number;
  items: UnknownFaceItem[];
}

export interface BulkLabelResult {
  labeled_count: number;
  failed_ids: number[];
}

export interface BulkOperationResult {
  success_count: number;
  failure_count: number;
  message: string;
}

export interface Person {
  id: number;
  name: string;
  description?: string;
  role?: string;
  face_count: number;
  created_at: string;
}

export interface ModelVersion {
  version_number: number;
  num_classes: number;
  num_training_samples: number;
  cross_validation_accuracy: number;
  trained_at: string;
  is_active: boolean;
}

export interface RetrainingStatus {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  message: string;
  version_number?: number;
  cv_accuracy?: number;
  num_classes?: number;
}

export interface Detection {
  bbox: { x1: number; y1: number; x2: number; y2: number };
  name: string;
  confidence: number;
  detection_confidence: number;
}

export interface FrameResult {
  detections: Detection[];
  frame_id: number;
  processing_time_ms: number;
}

@Injectable({ providedIn: 'root' })
export class FaceApiService {
  private base = environment.apiBaseUrl;
  // Flask URL for direct API calls (bypasses Next.js proxy for stream operations)
  private flaskUrl = this.base.replace(':3000', ':5000');

  constructor(private http: HttpClient) {}

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.base}/api/dashboard/stats`);
  }

  getUnknownFaces(status?: string, page = 1, pageSize = 20): Observable<UnknownFacesResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<UnknownFacesResponse>(`${this.base}/api/unknown-faces`, { params });
  }

  labelFace(id: number, personName: string, labeledBy = 'operator'): Observable<any> {
    return this.http.post(`${this.base}/api/unknown-faces/${id}/label`, {
      person_name: personName,
      labeled_by: labeledBy
    });
  }

  rejectFace(id: number, rejectedBy = 'operator'): Observable<any> {
    return this.http.post(`${this.base}/api/unknown-faces/${id}/reject`, {
      rejected_by: rejectedBy
    });
  }

  bulkLabelFaces(
    labels: { id: number; person_name: string }[],
    labeledBy = 'operator'
  ): Observable<BulkLabelResult> {
    return this.http.post<BulkLabelResult>(`${this.base}/api/unknown-faces/bulk-label`, {
      labels,
      labeled_by: labeledBy
    });
  }

  bulkDeleteFaces(filterStatus: string = 'all'): Observable<BulkOperationResult> {
    return this.http.post<BulkOperationResult>(`${this.base}/api/unknown-faces/bulk-delete`, {
      filter_status: filterStatus
    });
  }

  bulkRejectFaces(filterStatus: string = 'all'): Observable<BulkOperationResult> {
    return this.http.post<BulkOperationResult>(`${this.base}/api/unknown-faces/bulk-reject`, {
      filter_status: filterStatus
    });
  }

  getAffectedCount(filterStatus: string = 'all'): Observable<{ count: number }> {
    return this.http.get<{ count: number }>(
      `${this.base}/api/unknown-faces/count?filter_status=${filterStatus}`
    );
  }

  getPeople(): Observable<Person[]> {
    return this.http.get<Person[]>(`${this.base}/api/people`);
  }

  addPerson(name: string, description?: string, role?: string): Observable<Person> {
    return this.http.post<Person>(`${this.base}/api/people`, { name, description, role });
  }

  getModelVersions(): Observable<ModelVersion[]> {
    return this.http.get<ModelVersion[]>(`${this.base}/api/model/versions`);
  }

  triggerRetrain(): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>(`${this.base}/api/model/retrain`, {});
  }

  getRetrainStatus(jobId: string): Observable<RetrainingStatus> {
    return this.http.get<RetrainingStatus>(`${this.base}/api/model/retrain/status/${jobId}`);
  }

  activateModel(versionNumber: number): Observable<any> {
    return this.http.post(`${this.base}/api/model/activate/${versionNumber}`, {});
  }

  startSession(): Observable<{ session_id: string }> {
    // Call Flask directly for stream operations
    return this.http.post<{ session_id: string }>(`${this.flaskUrl}/api/stream/session/start`, {});
  }

  endSession(sessionId: string, totalFrames: number): Observable<any> {
    // Call Flask directly for stream operations
    return this.http.post(`${this.flaskUrl}/api/stream/session/end`, {
      session_id: sessionId,
      total_frames: totalFrames
    });
  }

  processFrame(frameData: string, sessionId: string): Observable<FrameResult> {
    // Call Flask directly for stream operations
    return this.http.post<FrameResult>(`${this.flaskUrl}/api/stream/frame`, {
      frame_data: frameData,
      session_id: sessionId
    });
  }

  getThumbnailUrl(faceId: number): string {
    return `${this.base}/api/unknown-faces/${faceId}/image`;
  }
}

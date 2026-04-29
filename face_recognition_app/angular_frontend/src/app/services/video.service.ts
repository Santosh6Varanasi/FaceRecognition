import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UploadResponse {
  video_id: number;
  job_id: string;
}

export interface JobStatus {
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  frames_processed: number;
  total_frames: number;
  message: string;
  unique_unknowns: number;
  unique_known: number;
}

export interface Detection {
  bbox: { x1: number; y1: number; x2: number; y2: number };
  name: string;
  confidence: number;
  detection_confidence: number;
}

export interface FrameDetection {
  frame_timestamp_ms: number;
  frame_id: number;
  detections: Detection[];
}

export interface VideoRecord {
  id: number;
  filename: string;
  file_size_bytes: number;
  video_hash: string;
  status: string;
  uploaded_at: string;
  last_processed_at: string | null;
  unique_unknowns: number;
  unique_known: number;
  duration?: number;
  fps?: number;
  width?: number;
  height?: number;
  frame_count?: number;
  model_version?: string;
  reprocessed_at?: string | null;
}

export interface TimelineEntry {
  id: number;
  video_id: number;
  person_id: number | null;
  person_name: string;
  start_time: number;
  end_time: number;
  detection_count: number;
  avg_confidence: number;
  created_at: string;
}

export interface VideoDetection {
  id: number;
  video_id: number;
  frame_number: number;
  timestamp: number;
  person_id: number | null;
  person_name: string;
  bbox_x1: number;
  bbox_y1: number;
  bbox_x2: number;
  bbox_y2: number;
  recognition_confidence: number;
  detection_confidence: number;
  is_unknown: boolean;
}

export interface VideoListResponse {
  videos: VideoRecord[];
  total: number;
  page: number;
  page_size: number;
}

@Injectable({ providedIn: 'root' })
export class VideoService {
  private base = 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  uploadVideo(file: File): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UploadResponse>(`${this.base}/api/videos/upload`, formData, {
      reportProgress: true,
      observe: 'events'
    });
  }

  processVideo(videoId: number): Observable<{ job_id: string; message: string }> {
    return this.http.post<{ job_id: string; message: string }>(
      `${this.base}/api/videos/${videoId}/process`, {}
    );
  }

  getVideoMetadata(videoId: number): Observable<VideoRecord> {
    return this.http.get<VideoRecord>(`${this.base}/api/videos/${videoId}`);
  }

  getDetectionsAtTimestamp(videoId: number, timestamp: number, tolerance = 0.25): Observable<VideoDetection[]> {
    return this.http.get<VideoDetection[]>(
      `${this.base}/api/videos/${videoId}/detections?timestamp=${timestamp}&tolerance=${tolerance}`
    );
  }

  getTimeline(videoId: number): Observable<TimelineEntry[]> {
    return this.http.get<TimelineEntry[]>(`${this.base}/api/videos/${videoId}/timeline`);
  }

  reprocessVideo(videoId: number, modelVersion?: string): Observable<{ job_id: string; message: string }> {
    const body = modelVersion ? { model_version: modelVersion } : {};
    return this.http.post<{ job_id: string; message: string }>(
      `${this.base}/api/videos/${videoId}/reprocess`, body
    );
  }

  reprocessBatch(videoIds: number[], modelVersion?: string): Observable<{ job_id: string; message: string }> {
    const body: any = { video_ids: videoIds };
    if (modelVersion) body.model_version = modelVersion;
    return this.http.post<{ job_id: string; message: string }>(
      `${this.base}/api/videos/reprocess-batch`, body
    );
  }

  getJobStatus(jobId: string): Observable<JobStatus> {
    return this.http.get<JobStatus>(`${this.base}/api/video/job/${jobId}`);
  }

  getDetections(videoId: number): Observable<FrameDetection[]> {
    return this.http.get<FrameDetection[]>(`${this.base}/api/video/${videoId}/detections`);
  }

  listVideos(page = 1, pageSize = 20): Observable<VideoListResponse> {
    return this.http.get<VideoListResponse>(
      `${this.base}/api/video/list?page=${page}&page_size=${pageSize}`
    );
  }

  getAllProcessedVideos(): Observable<VideoRecord[]> {
    // Get all processed videos for reprocessing selection
    return this.http.get<VideoRecord[]>(`${this.base}/api/videos?status=processed`);
  }

  getVideoUrl(videoId: number): string {
    return `${this.base}/api/video/${videoId}/file`;
  }
}

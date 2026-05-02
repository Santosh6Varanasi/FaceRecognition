import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface UploadResponse {
  video_id: number;
  job_id: string;
}

export interface JobStatus {
  status: 'queued' | 'processing' | 'completed' | 'failed';
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
  private base = environment.apiBaseUrl;

  // Signal-based state management
  private videosSignal = signal<VideoRecord[]>([]);
  private loadingSignal = signal<boolean>(false);
  private errorSignal = signal<string | null>(null);
  
  // Public readonly signals
  readonly videos = this.videosSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();
  
  // Computed signals for derived state
  readonly videoCount = computed(() => this.videos().length);
  readonly hasVideos = computed(() => this.videoCount() > 0);
  readonly processedVideos = computed(() => 
    this.videos().filter(v => v.status === 'processed')
  );

  constructor(private http: HttpClient) {}

  /**
   * Load videos and update signal state
   */
  async loadVideos(page = 1, pageSize = 20): Promise<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);
    
    try {
      const response = await this.http.get<VideoListResponse>(
        `${this.base}/api/videos/list?page=${page}&page_size=${pageSize}`
      ).toPromise();
      
      if (response) {
        this.videosSignal.set(response.videos);
      }
    } catch (error: any) {
      this.errorSignal.set(error?.message || 'Failed to load videos');
      console.error('Error loading videos:', error);
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /**
   * Load all processed videos and update signal state
   */
  async loadProcessedVideos(): Promise<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);
    
    try {
      const videos = await this.http.get<VideoRecord[]>(
        `${this.base}/api/videos?status=processed`
      ).toPromise();
      
      if (videos) {
        this.videosSignal.set(videos);
      }
    } catch (error: any) {
      this.errorSignal.set(error?.message || 'Failed to load processed videos');
      console.error('Error loading processed videos:', error);
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /**
   * Add a video to the signal state
   */
  addVideo(video: VideoRecord): void {
    this.videosSignal.update(videos => [...videos, video]);
  }

  /**
   * Update a video in the signal state
   */
  updateVideo(videoId: number, updates: Partial<VideoRecord>): void {
    this.videosSignal.update(videos => 
      videos.map(v => v.id === videoId ? { ...v, ...updates } : v)
    );
  }

  /**
   * Remove a video from the signal state
   */
  removeVideo(videoId: number): void {
    this.videosSignal.update(videos => videos.filter(v => v.id !== videoId));
  }

  /**
   * Clear all videos from signal state
   */
  clearVideos(): void {
    this.videosSignal.set([]);
  }

  uploadVideo(file: File): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    
    // Call Flask directly for uploads (bypasses Next.js proxy)
    // Flask URL is constructed from environment.apiBaseUrl by replacing port 3000 with 5000
    const flaskUrl = environment.apiBaseUrl.replace(':3000', ':5000');
    
    return this.http.post<UploadResponse>(`${flaskUrl}/api/videos/upload`, formData, {
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
    return this.http.get<JobStatus>(`${this.base}/api/videos/job/${jobId}`);
  }

  /**
   * Retrieves ALL face detections for the entire video grouped by frame.
   * 
   * This method fetches all detections across all frames in the video,
   * which is needed for the video playback overlay to show bounding boxes
   * throughout the entire video.
   * 
   * @param videoId - The ID of the video
   * @returns Observable of FrameDetection array
   */
  getDetections(videoId: number): Observable<FrameDetection[]> {
    return this.http.get<FrameDetection[]>(`${this.base}/api/videos/${videoId}/all-detections`);
  }

  listVideos(page = 1, pageSize = 20): Observable<VideoListResponse> {
    return this.http.get<VideoListResponse>(
      `${this.base}/api/videos/list?page=${page}&page_size=${pageSize}`
    );
  }

  getAllProcessedVideos(): Observable<VideoRecord[]> {
    // Get all processed videos for reprocessing selection
    return this.http.get<VideoRecord[]>(`${this.base}/api/videos?status=processed`);
  }

  getVideoUrl(videoId: number): string {
    return `${this.base}/api/videos/${videoId}/file`;
  }

  deleteVideo(videoId: number): Observable<{ message: string; video_id: number; filename: string }> {
    return this.http.delete<{ message: string; video_id: number; filename: string }>(
      `${this.base}/api/videos/${videoId}`
    );
  }
}

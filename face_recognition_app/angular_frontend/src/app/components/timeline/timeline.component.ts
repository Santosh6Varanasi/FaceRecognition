import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  OnChanges,
  SimpleChanges
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { VideoService, TimelineEntry } from '../../services/video.service';

interface TimelineEntryWithStyle extends TimelineEntry {
  color: string;
  offsetPercent: number;
  widthPercent: number;
  isActive: boolean;
}

@Component({
  selector: 'app-timeline',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="timeline-container" *ngIf="timelineEntries.length > 0">
      <h4 style="margin:0 0 12px 0;color:#e5e7eb;">Timeline</h4>
      
      <!-- Timeline bar -->
      <div class="timeline-bar" style="position:relative;height:60px;background:#1f2937;border-radius:6px;margin-bottom:8px;">
        <!-- Time markers -->
        <div class="time-markers" style="position:absolute;top:0;left:0;right:0;height:20px;display:flex;justify-content:space-between;padding:0 8px;align-items:center;">
          <span *ngFor="let marker of timeMarkers" style="color:#6b7280;font-size:11px;">
            {{ marker }}
          </span>
        </div>

        <!-- Timeline entries -->
        <div class="timeline-entries" style="position:absolute;top:24px;left:0;right:0;height:32px;padding:0 4px;">
          <div *ngFor="let entry of styledEntries"
               class="timeline-entry"
               [class.active]="entry.isActive"
               [style.left.%]="entry.offsetPercent"
               [style.width.%]="entry.widthPercent"
               [style.background]="entry.color"
               [style.border]="entry.isActive ? '2px solid #ffffff' : 'none'"
               [title]="getEntryTooltip(entry)"
               (click)="onEntryClick(entry)"
               style="position:absolute;height:28px;border-radius:4px;cursor:pointer;transition:all 0.2s;">
          </div>
        </div>
      </div>

      <!-- Legend -->
      <div class="timeline-legend" style="display:flex;flex-wrap:wrap;gap:12px;margin-top:12px;">
        <div *ngFor="let person of uniquePersons" style="display:flex;align-items:center;gap:6px;">
          <div [style.background]="person.color" 
               style="width:16px;height:16px;border-radius:3px;">
          </div>
          <span style="color:#9ca3af;font-size:13px;">{{ person.name }}</span>
        </div>
      </div>
    </div>

    <div *ngIf="timelineEntries.length === 0 && !loading" style="color:#6b7280;padding:16px;">
      No timeline data available.
    </div>

    <div *ngIf="loading" style="color:#9ca3af;padding:16px;">
      Loading timeline...
    </div>

    <div *ngIf="errorMessage" style="color:#f87171;padding:16px;">
      {{ errorMessage }}
    </div>
  `,
  styles: [`
    .timeline-container {
      width: 100%;
      margin-top: 16px;
    }
    .timeline-entry:hover {
      opacity: 0.8;
      transform: scaleY(1.1);
    }
    .timeline-entry.active {
      box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
    }
  `]
})
export class TimelineComponent implements OnInit, OnChanges {
  @Input() videoId!: number;
  @Input() videoDuration: number = 0;
  @Input() currentTime: number = 0;

  @Output() timelineClick = new EventEmitter<number>();

  timelineEntries: TimelineEntry[] = [];
  styledEntries: TimelineEntryWithStyle[] = [];
  uniquePersons: { name: string; color: string }[] = [];
  timeMarkers: string[] = [];
  loading = false;
  errorMessage = '';

  private colorMap = new Map<string, string>();

  constructor(private videoService: VideoService) {}

  ngOnInit(): void {
    if (this.videoId) {
      this.loadTimeline();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['currentTime'] && !changes['currentTime'].firstChange) {
      this.updateActiveEntry();
    }
    if (changes['videoDuration'] && !changes['videoDuration'].firstChange) {
      this.generateTimeMarkers();
      this.updateStyledEntries();
    }
  }

  private loadTimeline(): void {
    this.loading = true;
    this.videoService.getTimeline(this.videoId).subscribe({
      next: (entries) => {
        this.timelineEntries = entries;
        this.assignColors();
        this.generateTimeMarkers();
        this.updateStyledEntries();
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = 'Failed to load timeline';
        this.loading = false;
        console.error('Error loading timeline:', err);
      }
    });
  }

  private assignColors(): void {
    // Get unique person names
    const uniqueNames = Array.from(new Set(this.timelineEntries.map(e => e.person_name)));
    
    // Assign distinct colors using hash function
    this.colorMap.clear();
    this.uniquePersons = [];

    uniqueNames.forEach((name, index) => {
      const color = this.generateColorFromName(name, index);
      this.colorMap.set(name, color);
      this.uniquePersons.push({ name, color });
    });
  }

  private generateColorFromName(name: string, index: number): string {
    // Use a combination of hash and index to ensure distinct colors
    const hash = this.hashString(name);
    const hue = (hash + index * 137) % 360; // Golden angle for better distribution
    const saturation = 65 + (hash % 20); // 65-85%
    const lightness = 50 + (hash % 15); // 50-65%
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }

  private generateTimeMarkers(): void {
    if (this.videoDuration <= 0) {
      this.timeMarkers = [];
      return;
    }

    const markerCount = 5;
    this.timeMarkers = [];
    
    for (let i = 0; i <= markerCount; i++) {
      const time = (this.videoDuration / markerCount) * i;
      this.timeMarkers.push(this.formatTime(time));
    }
  }

  private updateStyledEntries(): void {
    if (this.videoDuration <= 0) {
      this.styledEntries = [];
      return;
    }

    this.styledEntries = this.timelineEntries.map(entry => {
      const offsetPercent = (entry.start_time / this.videoDuration) * 100;
      const widthPercent = ((entry.end_time - entry.start_time) / this.videoDuration) * 100;
      const color = this.colorMap.get(entry.person_name) || '#6b7280';
      const isActive = this.isEntryActive(entry);

      return {
        ...entry,
        color,
        offsetPercent,
        widthPercent,
        isActive
      };
    });
  }

  private updateActiveEntry(): void {
    this.styledEntries = this.styledEntries.map(entry => ({
      ...entry,
      isActive: this.isEntryActive(entry)
    }));
  }

  private isEntryActive(entry: TimelineEntry): boolean {
    return this.currentTime >= entry.start_time && this.currentTime <= entry.end_time;
  }

  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  getEntryTooltip(entry: TimelineEntry): string {
    return `${entry.person_name}\n${this.formatTime(entry.start_time)} - ${this.formatTime(entry.end_time)}\nConfidence: ${(entry.avg_confidence * 100).toFixed(0)}%`;
  }

  onEntryClick(entry: TimelineEntry): void {
    this.timelineClick.emit(entry.start_time);
  }
}

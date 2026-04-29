import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [RouterLink, NgIf],
  template: `
    <div class="kpi-card" [class.warning]="warning">
      <div class="kpi-title">{{ title }}</div>
      <div class="kpi-value">{{ value }}</div>
      <a *ngIf="link" [routerLink]="link">View →</a>
    </div>
  `
})
export class KpiCardComponent {
  @Input() title = '';
  @Input() value: string | number = '';
  @Input() warning = false;
  @Input() link?: string;
}

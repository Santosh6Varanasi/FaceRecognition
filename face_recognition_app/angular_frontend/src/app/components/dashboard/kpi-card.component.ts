import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';


@Component({
    selector: 'app-kpi-card',
    imports: [RouterLink],
    template: `
    <div 
      class="kpi-card" 
      [class.warning]="warning"
      role="region"
      [attr.aria-label]="title + ' metric'"
    >
      <div class="kpi-title" id="kpi-title-{{sanitizeId(title)}}">{{ title }}</div>
      <div 
        class="kpi-value" 
        [attr.aria-labelledby]="'kpi-title-' + sanitizeId(title)"
        [attr.aria-live]="warning ? 'polite' : undefined"
      >
        {{ value }}
      </div>
      @if (link) {
        <a 
          [routerLink]="link" 
          class="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 text-sm font-medium mt-2 inline-block transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded"
          [attr.aria-label]="'View ' + title.toLowerCase()"
        >
          View →
        </a>
      }
    </div>
    `
})
export class KpiCardComponent {
  @Input() title = '';
  @Input() value: string | number = '';
  @Input() warning = false;
  @Input() link?: string;
  
  sanitizeId(text: string): string {
    return text.toLowerCase().replace(/\s+/g, '-');
  }
}

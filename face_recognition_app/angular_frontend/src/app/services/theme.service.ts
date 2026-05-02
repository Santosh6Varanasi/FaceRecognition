import { Injectable, signal, computed, effect } from '@angular/core';

export type Theme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'app-theme';
  private themeSignal = signal<Theme>(this.getInitialTheme());
  
  readonly currentTheme = this.themeSignal.asReadonly();
  readonly isDark = computed(() => this.currentTheme() === 'dark');
  
  constructor() {
    // Apply theme on initialization and whenever it changes
    effect(() => {
      this.applyTheme(this.currentTheme());
    });
  }
  
  /**
   * Get initial theme from localStorage or system preference
   */
  private getInitialTheme(): Theme {
    // Check localStorage first
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
    
    // Fall back to system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    
    return 'light';
  }
  
  /**
   * Toggle between light and dark themes
   */
  toggleTheme(): void {
    const newTheme = this.currentTheme() === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }
  
  /**
   * Set a specific theme
   */
  setTheme(theme: Theme): void {
    this.themeSignal.set(theme);
    localStorage.setItem(this.STORAGE_KEY, theme);
  }
  
  /**
   * Apply theme class to document element
   */
  private applyTheme(theme: Theme): void {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
  }
}

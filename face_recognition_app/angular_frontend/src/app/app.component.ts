import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ThemeToggleComponent } from './components/theme-toggle/theme-toggle.component';

@Component({
    selector: 'app-root',
    imports: [RouterOutlet, RouterLink, RouterLinkActive, ThemeToggleComponent],
    template: `
    <!-- Skip Navigation Link for Accessibility -->
    <a href="#main-content" class="skip-link">
      Skip to main content
    </a>
    
    <div class="app-layout">
      <nav class="sidebar" role="navigation" aria-label="Main navigation">
        <div class="sidebar-header">
          <h2>Face Recognition</h2>
          <app-theme-toggle />
        </div>
        <ul class="nav-links" role="list">
          <li>
            <a routerLink="/dashboard" routerLinkActive="active" aria-label="Dashboard">
              <span class="nav-icon" aria-hidden="true">📊</span> Dashboard
            </a>
          </li>
          <li>
            <a routerLink="/camera" routerLinkActive="active" aria-label="Camera Monitor">
              <span class="nav-icon" aria-hidden="true">📷</span> Camera Monitor
            </a>
          </li>
          <li>
            <a routerLink="/unknown-faces" routerLinkActive="active" aria-label="Unknown Faces">
              <span class="nav-icon" aria-hidden="true">❓</span> Unknown Faces
            </a>
          </li>
          <li>
            <a routerLink="/model" routerLinkActive="active" aria-label="Model Management">
              <span class="nav-icon" aria-hidden="true">🤖</span> Model Management
            </a>
          </li>
          <li>
            <a routerLink="/people" routerLinkActive="active" aria-label="People">
              <span class="nav-icon" aria-hidden="true">👥</span> People
            </a>
          </li>
          <li>
            <a routerLink="/video" routerLinkActive="active" aria-label="Video">
              <span class="nav-icon" aria-hidden="true">🎬</span> Video
            </a>
          </li>
          <li>
            <a routerLink="/training" routerLinkActive="active" aria-label="Train Model">
              <span class="nav-icon" aria-hidden="true">🎓</span> Train Model
            </a>
          </li>
        </ul>
      </nav>
      <main id="main-content" class="main-content" role="main" aria-label="Main content">
        <router-outlet></router-outlet>
      </main>
    </div>
  `
})
export class AppComponent {}

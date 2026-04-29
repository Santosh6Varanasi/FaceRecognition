import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-layout">
      <nav class="sidebar">
        <div class="sidebar-header">
          <h2>Face Recognition</h2>
        </div>
        <ul class="nav-links">
          <li>
            <a routerLink="/dashboard" routerLinkActive="active">
              <span class="nav-icon">📊</span> Dashboard
            </a>
          </li>
          <li>
            <a routerLink="/camera" routerLinkActive="active">
              <span class="nav-icon">📷</span> Camera Monitor
            </a>
          </li>
          <li>
            <a routerLink="/unknown-faces" routerLinkActive="active">
              <span class="nav-icon">❓</span> Unknown Faces
            </a>
          </li>
          <li>
            <a routerLink="/model" routerLinkActive="active">
              <span class="nav-icon">🤖</span> Model Management
            </a>
          </li>
          <li>
            <a routerLink="/people" routerLinkActive="active">
              <span class="nav-icon">👥</span> People
            </a>
          </li>
          <li>
            <a routerLink="/video" routerLinkActive="active">
              <span class="nav-icon">🎬</span> Video
            </a>
          </li>
          <li>
            <a routerLink="/training" routerLinkActive="active">
              <span class="nav-icon">🎓</span> Train Model
            </a>
          </li>
        </ul>
      </nav>
      <main class="main-content">
        <router-outlet></router-outlet>
      </main>
    </div>
  `
})
export class AppComponent {}

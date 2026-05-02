import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'camera',
    loadComponent: () =>
      import('./components/camera-monitor/camera-monitor.component').then(m => m.CameraMonitorComponent)
  },
  {
    path: 'unknown-faces',
    loadComponent: () =>
      import('./components/unknown-faces/unknown-faces.component').then(m => m.UnknownFacesComponent)
  },
  {
    path: 'model',
    loadComponent: () =>
      import('./components/model-management/model-management.component').then(m => m.ModelManagementComponent)
  },
  {
    path: 'people',
    loadComponent: () =>
      import('./components/people/people-list.component').then(m => m.PeopleListComponent)
  },
  {
    path: 'video',
    loadComponent: () =>
      import('./components/video/video.component').then(m => m.VideoComponent)
  },
  {
    path: 'training',
    loadComponent: () =>
      import('./components/training/training.component').then(m => m.TrainingComponent)
  }
];

import { Injectable } from '@angular/core';
import { Observable, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { FaceApiService, RetrainingStatus } from './face-api.service';

@Injectable({ providedIn: 'root' })
export class RetrainingPollerService {
  constructor(private faceApi: FaceApiService) {}

  startPolling(jobId: string): Observable<RetrainingStatus> {
    return interval(3000).pipe(
      switchMap(() => this.faceApi.getRetrainStatus(jobId)),
      takeWhile(
        s => s.status !== 'completed' && s.status !== 'failed',
        true  // inclusive: emit the terminal status too
      )
    );
  }
}

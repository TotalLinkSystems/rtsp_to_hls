// stream-ws.service.ts
import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { StreamRecord } from '../models/stream.model';

@Injectable({ providedIn: 'root' })
export class StreamWsService {
  private ws!: WebSocket;
  private recordsSubject = new Subject<StreamRecord[]>();
  public records$ = this.recordsSubject.asObservable();

  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws/streams');

    this.ws.onmessage = (event) => {
      const updatedRecords: StreamRecord[] = JSON.parse(event.data);
      this.recordsSubject.next(updatedRecords);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed, reconnecting in 3s...');
      setTimeout(() => this.connect(), 3000);
    };
  }
}

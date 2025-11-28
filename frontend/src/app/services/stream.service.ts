import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { StreamRecord } from '../models/stream.model';

@Injectable({
  providedIn: 'root'
})
export class StreamService {

  private api = 'http://192.168.55.106:8000'; // FastAPI service URL

  constructor(private http: HttpClient) {}

  getRecords(): Observable<StreamRecord[]> {
    console.log('Fetching records from API');
    return this.http.get<StreamRecord[]>(`${this.api}/records`);
  }

  startStream(id: number): Observable<any> {
    return this.http.post(`${this.api}/start_stream/${id}`, {});
  }

  stopStream(pid: number): Observable<any> {
    return this.http.post(`${this.api}/stop_stream/${pid}`, {});
  }

  restartStream(id: number): Observable<any> {
    return this.http.post(`${this.api}/restart/${id}`, {});
  }

  deleteRecord(id: number): Observable<any> {
    return this.http.delete(`${this.api}/records/${id}`);
  }
}

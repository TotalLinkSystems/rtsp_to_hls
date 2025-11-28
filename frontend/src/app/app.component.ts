import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { StreamDashboardComponent } from "./pages/stream-dashboard/stream-dashboard/stream-dashboard.component";

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, StreamDashboardComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'rtsp_to_hls';
}

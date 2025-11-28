import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { StreamService } from '../../../services/stream.service';
import { StreamRecord } from '../../../models/stream.model';
import Hls from 'hls.js';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FilterByNamePipe } from '../../../pipes/filter-by-name.pipe';
import { StreamWsService } from '../../../services/stream-ws.service';
import { Modal } from 'bootstrap';

declare var bootstrap: any;

@Component({
  selector: 'app-stream-dashboard',
  templateUrl: './stream-dashboard.component.html',
  imports: [CommonModule, FormsModule, FilterByNamePipe],
})
export class StreamDashboardComponent implements OnInit {

@ViewChild('modalVideo') modalVideo!: ElementRef<HTMLVideoElement>;
private previewHlsMap = new Map<number, Hls>();

  records: StreamRecord[] = [];
  loading = false;
  streamBaseURL = 'https://bsghelp.com/streams/';
  searchText: string = '';
  copiedId: number | null = null;

  selectedStream: StreamRecord | null = null;

  private initializedPreviews = new Set<number>();
  private hlsInstances = new Map<number, Hls>();
  private modalHls: Hls | null = null;
  private modalInstance: any = null;

  constructor(private streamService: StreamService, private wsService: StreamWsService) {}

  ngOnInit() {
    this.loadRecords();
    // setInterval(() => this.loadRecords(), 10000);
    this.wsService.connect();
    this.wsService.records$.subscribe((updates) => this.updateRecords(updates));
  }

  ngOnDestroy() {
  this.previewPlayers.forEach(hls => hls.destroy());
  this.previewPlayers.clear();
}


  updateRecords(updates: StreamRecord[]) {
    updates.forEach((rec) => {
      const idx = this.records.findIndex(r => r.id === rec.id);
      if (idx > -1) {
        this.records[idx] = { ...this.records[idx], ...rec };
      } else {
        this.records.push(rec);
      }
    });
    this.loadPreviews(); // ensure new videos are initialized
  }

  // --- Records & Previews ---
  loadRecords() {
    this.loading = true;
    this.streamService.getRecords().subscribe({
      next: data => {
        this.records = data;
        console.log('Received updates from WS:', data);
        this.loading = false;
        this.loadPreviews();
        console.log('Previews initialized');
      },
      error: err => {
        console.error(err);
        this.loading = false;
      }
    });
  }
//  --------------------  --------------------  New Preview Player Code  --------------------  --------------------
private previewPlayers = new Map<number, Hls>();

private createPreviewPlayer(rec: StreamRecord, video: HTMLVideoElement) {
  const url = this.getStreamUrl(rec);

  // Destroy old instance if exists
  if (this.previewPlayers.has(rec.id)) {
    this.previewPlayers.get(rec.id)!.destroy();
    this.previewPlayers.delete(rec.id);
  }

  if (Hls.isSupported()) {
    const hls = new Hls({
      lowLatencyMode: true,
      maxBufferLength: 5,
      backBufferLength: 0,
    });

    hls.loadSource(url);
    hls.attachMedia(video);

    // Auto-recover on errors
    hls.on(Hls.Events.ERROR, (event, data) => {
      if (data.fatal) {
        console.warn(`Fatal HLS error on preview ${rec.id}, reloading…`, data);
        this.createPreviewPlayer(rec, video);
      }
    });

    this.previewPlayers.set(rec.id, hls);

  } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = url;
  }
}
// ---------------------  --------------------  --------------------  --------------------

// loadPreviews() {
//     setTimeout(() => {
//       this.records.forEach(rec => {
//         if (this.previewHlsMap.has(rec.id)) return;

//         const video = document.getElementById('preview-' + rec.id) as HTMLVideoElement;
//         if (!video) return;

//         const url = this.getStreamUrl(rec);

//         if (Hls.isSupported()) {
//           const hls = new Hls({ lowLatencyMode: true, maxBufferLength: 5 });
//           hls.loadSource(url);
//           hls.attachMedia(video);
//           this.previewHlsMap.set(rec.id, hls);
//         } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
//           video.src = url;
//         }

//         video.pause();
//         video.addEventListener('mouseenter', () => video.play());
//         video.addEventListener('mouseleave', () => video.pause());
//       });
//     }, 50);
//   }
loadPreviews() {
  setTimeout(() => {
    this.records.forEach(rec => {
      const video = document.getElementById('preview-' + rec.id) as HTMLVideoElement;
      if (!video) return;

      this.createPreviewPlayer(rec, video);

      // hover-play logic
      video.pause();
      video.onmouseenter = () => video.play();
      video.onmouseleave = () => video.pause();
    });
  }, 50);
}
private resetPreview(id: number) {
  const hls = this.previewPlayers.get(id);
  if (hls) {
    hls.destroy();
    this.previewPlayers.delete(id);
  }
}



// Hover playback
playPreview(id: number) {
  const video = document.getElementById('preview-' + id) as HTMLVideoElement;
  video?.play();
}

pausePreview(id: number) {
  const video = document.getElementById('preview-' + id) as HTMLVideoElement;
  video?.pause();
}


  // --- Stream Controls ---
  start(record: StreamRecord) {
    this.resetPreview(record.id);
    this.streamService.startStream(record.id).subscribe(() => this.loadRecords());
  }
  stop(record: StreamRecord) {
    if (!record.pid) return;
    this.resetPreview(record.id);
    this.streamService.stopStream(record.pid).subscribe(() => this.loadRecords());
  }
  restart(record: StreamRecord) {
    this.resetPreview(record.id);
    this.streamService.restartStream(record.id).subscribe(() => this.loadRecords());
  }

  getStreamUrl(rec: StreamRecord): string {
    const encoded = rec.name.replaceAll(' ', '%20');
    return `${this.streamBaseURL}${encoded}/${encoded}.m3u8`;
  }

  // --- Clipboard ---
  copyToClipboard(url: string, id: number) {
    if (!navigator.clipboard) {
      this.fallbackCopyTextToClipboard(url, id);
      return;
    }
    navigator.clipboard.writeText(url).then(() => {
      this.copiedId = id;
      setTimeout(() => (this.copiedId = null), 1600);
    }).catch(() => this.fallbackCopyTextToClipboard(url, id));
  }
  fallbackCopyTextToClipboard(text: string, id: number) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    this.copiedId = id;
    setTimeout(() => (this.copiedId = null), 1600);
  }

openModal(rec: StreamRecord) {
  this.selectedStream = rec;

  // small timeout ensures Angular has updated selectedStream bindings if needed
  setTimeout(() => {
    const modalEl = document.getElementById('streamModal') as HTMLElement;
    const video = this.modalVideo.nativeElement as HTMLVideoElement;
    const url = this.getStreamUrl(rec);

    // destroy previous modal HLS if present
    if (this.modalHls) {
      this.modalHls.destroy();
      this.modalHls = null;
    }

    // attach HLS to modal video
    if (Hls.isSupported()) {
      const hls = new Hls({ lowLatencyMode: true, maxBufferLength: 10 });
      hls.loadSource(url);
      hls.attachMedia(video);
      this.modalHls = hls;
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = url;
    }

    // ensure clean state
    // video.pause();
    // video.currentTime = 0;


    // destroy previous Modal instance if any
    try {
      if (this.modalInstance) {
        this.modalInstance.hide();
        this.modalInstance.dispose?.();
        this.modalInstance = null;
      }
    } catch (e) {
      // ignore
    }

    // create and show a new Modal instance (using imported Modal)
    this.modalInstance = new Modal(modalEl);
    this.modalInstance.show();

    // cleanup when modal is hidden: stop video and destroy HLS
    modalEl.addEventListener('hidden.bs.modal', () => {
      try {
        video.pause();
        video.currentTime = 0;
      } catch (e) {}
      if (this.modalHls) {
        this.modalHls.destroy();
        this.modalHls = null;
      }
    }, { once: true });

    // PiP on double-click
    const dbl = async () => {
      try {
        if (document.pictureInPictureElement) {
          await document.exitPictureInPicture();
        } else {
          await video.requestPictureInPicture();
        }
      } catch (err) {
        console.warn('PiP error', err);
      }
    };

    video.removeEventListener('dblclick', dbl);
    video.addEventListener('dblclick', dbl);
  }, 50);
}

}

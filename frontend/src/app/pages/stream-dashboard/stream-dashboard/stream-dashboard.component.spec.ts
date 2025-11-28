import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StreamDashboardComponent } from './stream-dashboard.component';

describe('StreamDashboardComponent', () => {
  let component: StreamDashboardComponent;
  let fixture: ComponentFixture<StreamDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StreamDashboardComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StreamDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

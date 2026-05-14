import { Component, inject } from '@angular/core';

import { NotifyService } from '../../core/notify.service';

@Component({
  selector: 'app-toast-host',
  standalone: true,
  templateUrl: './toast-host.html',
  styleUrl: './toast-host.scss',
})
export class ToastHost {
  protected readonly notify = inject(NotifyService);
}

import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';

import { CashierIdentityService } from './core/cashier-identity.service';
import { ToastHost } from './shared-ui/toast-host/toast-host';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [TuiRoot, RouterOutlet, RouterLink, RouterLinkActive, ToastHost],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly identity = inject(CashierIdentityService);
  private readonly router = inject(Router);

  protected logout(): void {
    this.identity.clear();
    void this.router.navigate(['/login']);
  }
}

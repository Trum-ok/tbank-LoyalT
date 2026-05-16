import { Component, inject, signal } from '@angular/core';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';
import { filter } from 'rxjs';

import { AdminIdentityService } from './core/admin-identity.service';
import { AdminSwitcher } from './shared-ui/admin-switcher/admin-switcher';
import { ThemeToggle } from './shared-ui/theme-toggle/theme-toggle';
import { ToastHost } from './shared-ui/toast-host/toast-host';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    TuiRoot,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    AdminSwitcher,
    ThemeToggle,
    ToastHost,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly identity = inject(AdminIdentityService);
  private readonly router = inject(Router);

  // Хром (сайдбар + топбар) скрываем на экране входа.
  protected readonly showChrome = signal(!this.isLoginUrl(this.router.url));

  constructor() {
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => this.showChrome.set(!this.isLoginUrl(e.urlAfterRedirects)));
  }

  private isLoginUrl(url: string): boolean {
    return url.split('?')[0].replace(/\/$/, '') === '/login';
  }
}

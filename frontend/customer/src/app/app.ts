import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';
import { filter, map, startWith } from 'rxjs';

import { EnrollmentsStore } from './core/enrollments.store';
import { formatPoints } from './core/format';
import { PageActionsService } from './core/page-actions.service';
import { RoleSwitcher } from './shared-ui/role-switcher/role-switcher';
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
    RoleSwitcher,
    ThemeToggle,
    ToastHost,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly router = inject(Router);

  protected readonly enrollments = inject(EnrollmentsStore);
  protected readonly formatPoints = formatPoints;
  protected readonly pageActions = inject(PageActionsService);

  private readonly currentUrl = toSignal(
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map(e => (e as NavigationEnd).urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  protected readonly isDetail = computed(() =>
    /^\/catalog\/[^/]+/.test(this.currentUrl() ?? ''),
  );
}

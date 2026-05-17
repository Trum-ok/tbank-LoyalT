import { Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';
import { filter, map, pairwise, startWith } from 'rxjs';

import { EnrollmentsStore } from './core/enrollments.store';
import { PageActionsService } from './core/page-actions.service';
import { RoleSwitcher } from './shared-ui/role-switcher/role-switcher';
import { ThemeToggle } from './shared-ui/theme-toggle/theme-toggle';
import { ToastHost } from './shared-ui/toast-host/toast-host';

const DETAIL_URL = /^\/catalog\/[^/]+/;
const MY_PROGRAMS_URL = /^\/my-programs(\/|$|\?)/;

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
  protected readonly pageActions = inject(PageActionsService);

  private readonly currentUrl = toSignal(
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map(e => (e as NavigationEnd).urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  /** Куда ведёт кнопка «назад» со страницы программы — туда, откуда её открыли. */
  protected readonly backTarget = signal('/catalog');

  protected readonly isDetail = computed(() =>
    DETAIL_URL.test(this.currentUrl() ?? ''),
  );

  protected readonly isMyPrograms = computed(() =>
    MY_PROGRAMS_URL.test(this.currentUrl() ?? ''),
  );

  constructor() {
    this.router.events
      .pipe(
        filter(e => e instanceof NavigationEnd),
        map(e => (e as NavigationEnd).urlAfterRedirects),
        startWith(this.router.url),
        pairwise(),
        takeUntilDestroyed(),
      )
      .subscribe(([prev, curr]) => {
        // Запоминаем источник только при входе на страницу программы.
        if (DETAIL_URL.test(curr) && !DETAIL_URL.test(prev)) {
          this.backTarget.set(
            MY_PROGRAMS_URL.test(prev) ? '/my-programs' : '/catalog',
          );
        }
      });
  }
}

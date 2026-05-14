import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';

import { EnrollmentsStore } from './core/enrollments.store';
import { formatPoints } from './core/format';
import { RoleSwitcher } from './shared-ui/role-switcher/role-switcher';
import { ThemeToggle } from './shared-ui/theme-toggle/theme-toggle';

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
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly enrollments = inject(EnrollmentsStore);
  protected readonly formatPoints = formatPoints;
}

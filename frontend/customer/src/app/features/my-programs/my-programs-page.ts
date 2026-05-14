import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TuiLoader } from '@taiga-ui/core';
import { TuiAvatar } from '@taiga-ui/kit';

import { EnrollmentsStore } from '../../core/enrollments.store';
import { formatDate, formatPoints } from '../../core/format';

@Component({
  selector: 'app-my-programs-page',
  standalone: true,
  imports: [RouterLink, TuiAvatar, TuiLoader],
  templateUrl: './my-programs-page.html',
  styleUrl: './my-programs-page.scss',
})
export class MyProgramsPage {
  protected readonly store = inject(EnrollmentsStore);

  readonly formatDate = formatDate;
  readonly formatPoints = formatPoints;

  initial(name: string | null | undefined): string {
    return (name ?? 'П').trim().charAt(0).toUpperCase();
  }
}

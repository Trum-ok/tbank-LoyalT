import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TuiLoader } from '@taiga-ui/core';
import { TuiAvatar } from '@taiga-ui/kit';

import { EnrollmentRead } from '@tbank-loyalt/shared';

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

  cardName(e: EnrollmentRead): string {
    return e.display_name ?? e.partner_name ?? e.program_name ?? 'Программа';
  }

  initials(e: EnrollmentRead): string {
    return this.cardName(e)
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(s => s[0]?.toUpperCase() ?? '')
      .join('');
  }
}

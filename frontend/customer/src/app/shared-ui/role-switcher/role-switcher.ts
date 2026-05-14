import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { CustomerIdService } from '../../core/customer-id.service';

@Component({
  selector: 'app-role-switcher',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './role-switcher.html',
  styleUrl: './role-switcher.scss',
})
export class RoleSwitcher {
  private readonly service = inject(CustomerIdService);
  readonly profiles = this.service.profiles;
  readonly currentId = this.service.currentId;

  onChange(value: string): void {
    if (value === '__custom__') {
      const custom = window.prompt(
        'Введите UUID клиента (X-Customer-Id):',
        this.currentId(),
      );
      if (custom && custom.trim()) {
        this.service.setId(custom.trim());
      }
      return;
    }
    this.service.setId(value);
  }
}

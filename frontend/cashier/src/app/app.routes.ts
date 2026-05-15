import { Routes } from '@angular/router';

import { authGuard, guestGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'pos',
  },
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./features/login/login-page').then(m => m.LoginPage),
    title: 'Вход кассира',
  },
  {
    path: 'pos',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/pos/pos-page').then(m => m.PosPage),
    title: 'Касса',
  },
  {
    path: 'history',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/history/history-page').then(m => m.HistoryPage),
    title: 'История операций',
  },
  { path: '**', redirectTo: 'pos' },
];

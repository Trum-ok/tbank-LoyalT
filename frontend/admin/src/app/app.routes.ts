import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'dashboard',
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login-page').then(m => m.LoginPage),
    title: 'Вход · Т-Лояльность Админка',
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard-page').then(m => m.DashboardPage),
    title: 'Метрики платформы',
  },
  {
    path: 'moderation',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/moderation/moderation-page').then(
        m => m.ModerationPage,
      ),
    title: 'Модерация заявок',
  },
  {
    path: 'partners',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/partners/partners-page').then(m => m.PartnersPage),
    title: 'Партнёры',
  },
  {
    path: 'catalog',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/catalog/catalog-page').then(m => m.CatalogPage),
    title: 'Каталог',
  },
  { path: '**', redirectTo: 'dashboard' },
];

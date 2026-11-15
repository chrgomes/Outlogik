import { Routes } from '@angular/router';

import { Home } from './pages/home/home';
import { NotFound } from './pages/not-found/not-found';

/** Page titles follow "<page> · Outlogik"; the homepage uses the brand line. */
export const routes: Routes = [
  { path: '', component: Home, title: 'Outlogik · Digital marketing and client management for agencies' },
  { path: '**', component: NotFound, title: 'Page not found · Outlogik' },
];

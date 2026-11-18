/**
 * Build-time settings, injected with Angular's `define` option (see angular.json).
 * Production builds use the real addresses (https://outlogik.com and https://app.outlogik.com);
 * the development configuration uses localhost. Override for another deployment, e.g. staging:
 *   ng build marketing --define "OL_APP_URL='https://app.staging.outlogik.com'" --define "OL_SITE_URL='https://staging.outlogik.com'"
 */
declare const OL_APP_URL: string;
declare const OL_SITE_URL: string;
